// SPDX-License-Identifier: Apache-2.0
package dev.twoyi.redlauncher;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.TimeUnit;

/** Only run after a user explicitly taps Check root. No root claim is inferred
 * from a manager app's presence. Every command is a fixed argv array. */
final class RedRootProbe {
    interface Runner { CommandResult run(String... argv) throws Exception; }
    static final class CommandResult {
        final int exit; final String output;
        CommandResult(int exit, String output) { this.exit = exit; this.output = output; }
    }
    static final class Result {
        final boolean root; final boolean magisk; final String magiskVersion;
        Result(boolean root, boolean magisk, String magiskVersion) {
            this.root = root; this.magisk = magisk; this.magiskVersion = magiskVersion;
        }
        String label() {
            if (!root) return "Root access: Not granted / unavailable";
            return magisk ? "Root: UID 0 · Magisk " + magiskVersion : "Root: UID 0 · Magisk not verified";
        }
    }

    private static final int OUTPUT_LIMIT = 1024;

    /** Drain the pipe concurrently. Waiting for a child before consuming its
     * output can deadlock when the child fills the OS stdout/stderr pipe. */
    private static final class BoundedOutput implements Runnable {
        private final InputStream input;
        private final ByteArrayOutputStream data = new ByteArrayOutputStream();
        private volatile boolean overLimit;
        private volatile boolean failed;

        BoundedOutput(InputStream input) { this.input = input; }

        @Override public void run() {
            try (InputStream stream = input) {
                byte[] buffer = new byte[256];
                int read;
                while ((read = stream.read(buffer)) != -1) {
                    int available = OUTPUT_LIMIT - data.size();
                    if (read > available) overLimit = true;
                    if (available > 0) data.write(buffer, 0, Math.min(read, available));
                }
            } catch (IOException e) {
                failed = true;
            }
        }

        String text() { return new String(data.toByteArray(), StandardCharsets.UTF_8); }
    }

    static final Runner PROCESS_RUNNER = argv -> {
        Process process = new ProcessBuilder(argv).redirectErrorStream(true).start();
        BoundedOutput captured = new BoundedOutput(process.getInputStream());
        Thread reader = new Thread(captured, "andarium-root-probe-output");
        reader.setDaemon(true);
        reader.start();
        try {
            if (!process.waitFor(15, TimeUnit.SECONDS)) {
                process.destroyForcibly();
                reader.join(1000);
                return new CommandResult(-1, "timeout");
            }
            reader.join(1000);
            if (reader.isAlive() || captured.failed || captured.overLimit) {
                return new CommandResult(-2, "invalid or incomplete command output");
            }
            return new CommandResult(process.exitValue(), captured.text());
        } finally {
            if (process.isAlive()) process.destroyForcibly();
        }
    };

    static Result check(Runner runner) {
        final CommandResult su;
        try { su = runner.run("su", "-c", "id -u"); }
        catch (Exception failed) { return new Result(false, false, ""); }
        // No heuristic string matching: the command must exit zero and return precisely UID 0.
        if (su.exit != 0 || !"0".equals(su.output.trim())) return new Result(false, false, "");
        try {
            CommandResult m = runner.run("su", "-c", "magisk -v");
            String version = m.output.trim();
            if (m.exit == 0 && version.length() > 0 && version.length() <= 96
                    && version.matches("[A-Za-z0-9._+() -]+")) {
                return new Result(true, true, version);
            }
        } catch (Exception ignored) { /* su can work without Magisk. */ }
        return new Result(true, false, "");
    }

    private RedRootProbe() {}
}
