# Andarium Red free-runner build — systematic preflight and memory

The full source audit runs on the disposable GitHub-hosted runner
before deleting the preinstalled Android SDK and before downloading
the ~1200-repository Android checkout. It checks Bash syntax, all local
Python source, Android XML, product Android.bp rules, launcher/clipboard
Java compilation, reversible Soong host Go memory patch, vendor preflight,
pinned Repo retry driver, source checkpoint and the entire 167+ Python/Swift
regression suite. Failure stops the expensive build early; unsupported
toolchains or iPhone runtime behavior are not silently marked as passed.

GitHub's independent run
[44882095931](https://github.com/SeanEmcee/SeanEmcee-Andarium-Red/actions/runs/44882095931)
demonstrated the free runner can activate an additional **16 GiB of
compressed ZRAM swap**. That is not physical memory and does not
guarantee build success. The ZRAM is higher priority than existing disk
swap; 6 GiB disk swap remains as fallback if sufficient host storage
exists. The original Kernarium, kernel, accessibility and source-object
cache keys remain unmodified.

The host-only Soong Go instrumentation uses a **6 GiB soft memory limit
and GOGC=20**, and periodically logs heap allocated, GC count and
goroutine count. The original pinned Soong entry point is restored
before the upstream's final source integrity verification.
A smoke-test pass is not a bootable Android image. Any iPhone unsigned
IPA still requires an actual iOS packaging/compile job and independent
device verification.
