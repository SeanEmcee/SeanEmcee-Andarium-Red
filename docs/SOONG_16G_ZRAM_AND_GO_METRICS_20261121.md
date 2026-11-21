# Android 17 Soong Go memory strategy — 2026-11-21

On run 44871368198, the 4.5 GiB / GOGC=8 policy plus 6 GiB ZRAM
produced no verified Android image, with prolonged Soong graph generation
and a missing final GitHub log. Last reported ZRAM compression was strong
(~5.2 GiB swapped logically inside ~1.1 GiB physical bytes).
This does not prove that the Go collector or OOM killer caused the failure.

A disposable **16 GiB** ZRAM device was independently activated in
[probe 44882095931](https://github.com/SeanEmcee/SeanEmcee-Andarium-Red/actions/runs/44882095931),
with no preallocated 16 GiB physical RAM or disk. The next hosted build
will use that, while allowing the Soong Go graph builder a **6 GiB**
runtime soft heap target and GOGC=20 instead of 4.5 GiB/GOGC=8.
The goal is to avoid excessive collection and short virtual-memory capacity,
not to claim additional physical RAM. A longer actual Soong run remains
necessary to validate correctness and performance.

A 60-second in-process memory metrics ticker records:
HeapAlloc, HeapSys, Sys, TotalAlloc, GC cycles, and goroutine count, into
the compiler stderr. It is best-effort diagnostic instrumentation of the
host build executable only; the original pinned source is restored exactly
before upstream post-build verification. The code is covered by the
small Go compilation fixture test.

There are still structural limits: the 16 GiB physical RAM and constrained
Btrfs/host disk in free GitHub Actions, and a full uncached Android
compilation after Soong bootstrap. No "all errors fixed" claim is justified
until the actual image and IPA are built and independently validated.
