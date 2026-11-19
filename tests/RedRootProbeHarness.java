package dev.twoyi.redlauncher;

public final class RedRootProbeHarness {
    private static void check(boolean ok, String message) {
        if (!ok) throw new AssertionError(message);
    }
    public static void main(String[] ignored) {
        RedRootProbe.Result missing = RedRootProbe.check(argv -> { throw new java.io.IOException("missing su"); });
        check(!missing.root && !missing.magisk, "missing su cannot imply root");
        RedRootProbe.Result denied = RedRootProbe.check(argv -> new RedRootProbe.CommandResult(1, "0"));
        check(!denied.root, "nonzero exit fails even with UID 0 in output");
        RedRootProbe.Result shell = RedRootProbe.check(argv -> new RedRootProbe.CommandResult(0, "2000\n"));
        check(!shell.root, "shell UID cannot pass");
        RedRootProbe.Result weak = RedRootProbe.check(argv -> new RedRootProbe.CommandResult(0, "0 extra"));
        check(!weak.root, "UID must be exact");
        RedRootProbe.Result rooted = RedRootProbe.check(argv -> {
            if (argv.length == 3 && argv[2].equals("id -u")) return new RedRootProbe.CommandResult(0, "0\n");
            return new RedRootProbe.CommandResult(127, "not found");
        });
        check(rooted.root && !rooted.magisk, "su alone is not Magisk-managed root");
        RedRootProbe.Result magisk = RedRootProbe.check(argv -> {
            if (argv.length == 3 && argv[2].equals("id -u")) return new RedRootProbe.CommandResult(0, "0\n");
            if (argv.length == 3 && argv[2].equals("magisk -v")) return new RedRootProbe.CommandResult(0, "31.1\n");
            throw new AssertionError("Unexpected command arguments");
        });
        check(magisk.root && magisk.magisk && magisk.label().contains("31.1"), "real su + magisk proof");
        RedRootProbe.Result malicious = RedRootProbe.check(argv -> {
            if (argv[2].equals("id -u")) return new RedRootProbe.CommandResult(0, "0");
            return new RedRootProbe.CommandResult(0, "31.1;evil");
        });
        check(malicious.root && !malicious.magisk, "reject unexpected output");
        System.out.println("RED_ROOT_PROBE_7_PASS");
    }
}
