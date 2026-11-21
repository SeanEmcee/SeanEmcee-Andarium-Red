# Andarium Red: fail-fast guest Java preflight and compressed swap

Both Android guest Java source modules passed independent SDK 37.2
compilation in [run 44870957057](https://github.com/SeanEmcee/SeanEmcee-Andarium-Red/actions/runs/44870957057),
after replacing nonexistent Settings.ACTION_NOTIFICATION_SETTINGS
with supported Settings.ACTION_ALL_APPS_NOTIFICATION_SETTINGS.

The free hosted builder now executes this same exact Java-source check
immediately after checkout, BEFORE removing its preinstalled Android SDK
and BEFORE the expensive 1200+ project Repo sync. This catches future
missing Java SDK symbols without wasting hours or modifying pinned AOSP.

ZRAM feasibility was tested in [run 44870828794](https://github.com/SeanEmcee/SeanEmcee-Andarium-Red/actions/runs/44870828794).
A separate [6 GiB test 44871016354](https://github.com/SeanEmcee/SeanEmcee-Andarium-Red/actions/runs/44871016354)
successfully activated an additional high-priority ZRAM device on the
free Ubuntu runner. It uses memory compression, not preallocated disk
capacity; effective gain depends on compressibility and memory load,
so it cannot guarantee full Soong completion. Existing Ubuntu ZRAM and
checked disk swap remain available. Memory snapshots include ZRAM
compressed storage statistics for diagnosis.

All original Kernarium pinned source integrity checks, kernel cache,
accessibility checkout and 3.06 GiB Git object seed keys are retained.
The previously launched full run 44860535715 is tied to old commit
1ce856b693f6654e94aa6c3f92bb971e968f911f and cannot be hot-edited;
only a new run can incorporate these corrections.
