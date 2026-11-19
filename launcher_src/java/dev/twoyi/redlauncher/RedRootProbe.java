// SPDX-License-Identifier: Apache-2.0
package dev.twoyi.redlauncher;

import java.io.ByteArrayOutputStream;
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
    static final Runner PROCESS_RUNNER = argv -> {
        Process process = new ProcessBuilder(argv).redirectErrorStream(true).start();
        try {
            if (!process.waitFor(15, TimeUnit.SECONDS)) {
                process.destroyForcibly();
                return new CommandResult(-1, "timeout");
            }
            try (InputStream stream = process.getInputStream(); ByteArrayOutputStream out = new ByteArrayOutputStream()) {
                byte[] block = new byte[256];
                int n;
                while ((n = stream.read(block)) != -1 && out.size() <= OUTPUT_LIMIT) {
                    out.write(block, 0, n);
                }
                return new CommandResult(process.exitValue(), out.toString(StandardCharsets.UTF_8.name()));
            }
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
