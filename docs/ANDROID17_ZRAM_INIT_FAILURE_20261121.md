# Android 17 build #44882421582 — ZRAM module initialization order

The last full hosted run [44882421582](https://github.com/SeanEmcee/SeanEmcee-Andarium-Red/actions/runs/44882421582)
passed complete 167-test preflight, verified all four source/kernel/accessibility
cache restores and completed the pinned Android17 source sync with patch
verification. Compilation NEVER started. The fatal step was:

```
ERROR: runner kernel does not support separate ZRAM devices
```

The ZRAM bootstrap inspected `/sys/class/zram-control/hot_add` *before*
executing `sudo modprobe zram`. That check was premature: the sysfs
interface may only appear when the module is loaded. The failure alone does
not establish an unsupported kernel, and it is not a Soong compilation error.

The corrected script loads the module **first**, verifies the device
interface, activates 16 GiB high-priority compressed virtual swap, and logs
the active devices. The exact ZRAM initialization now runs immediately
after the complete source/Java/Swift preflight, **before** disk cleanup and
the expensive 1200-project Android17 Repo sync. Unsupported host runners
fail quickly with diagnostics, not after an expensive 40-minute checkout.

ZRAM provides compression, not 16 GiB extra physical RAM; the subsequent
full Soong runtime still needs actual validation. Original pinned cache
keys, Repo retry, low-memory Soong instrumentation, complete source
verification and build-graph checks remain unchanged. No synthetic ROM,
signed IPA, or device-boot verification is claimed.
