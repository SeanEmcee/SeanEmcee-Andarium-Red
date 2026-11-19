# Andarium Red v15 — native display and device-budget memory

**Branch:** feature/andd-memory-tuning in private SeanEmcee/SeanEmcee-Andarium-Red.
**Status:** SOURCE IMPLEMENTATION. Not an iOS build, performance benchmark, rooted Android image or device-certified release.

## Automatic Native Device Display (ANDD)

- **New installation default:** Automatic Native Device Display (ANDD). Physical pixel size is read at runtime from UIWindowScene.screen.nativeBounds; hw.machine hardware identifier is informational only, not a resolution lookup table. Dimensions track screen orientation. On the iPhone 14 Pro Max (iPhone15,3), expected full portrait dimensions are **1290 × 2796**.
- **Custom:** width/height numeric fields, linked chain (aspect locked to the ratio at the moment the chain is enabled), unlinked independent editing. Blank, invalid, below-256 or above-4095 side, or a framebuffer over 16,777,216 pixels cannot be saved. Android receives exact chosen dimensions rather than approximating to a scale preset.
- **Scaled:** Existing resolution factor choices remain accessible. An explicit saved pre-v15 selection is migrated into this mode and preserved. A noninteractive harness launch's explicit scale still takes priority for that run only.
- **Rendering path:** Same resolution reaches Home's expected guest pixel layout, GuestDisplayView Metal drawable size, Android's reported display geometry/dpi, and guest touchscreen coordinate mapping. Resolutions take effect on next guest start. An unusual custom aspect ratio may appear letterboxed depending on host window, rather than warped.

## Memory and performance

Kernarium runtime currently has a per-device budget that incorporates available process memory under jetsam, iOS native kernel virtual address window, vCPU count, translation cache, engine overhead, graphics memory, and camera memory reserves. Andarium Red uses this **existing authoritative budget** rather than a fictional unlock-all-RAM switch.

- **Max quality** picks largest guest RAM at/below both conservative no-closing-risk bound and graphics headroom line for active vCPU count. Also the default RAM for a new Andarium Red guest created from New VM screen.
- **High RAM** picks runtime safe guest RAM bound; it may leave fewer graphics resources.
- **Device limit** picks highest value current runtime admits; explicit warning notes iOS can terminate the app and graphics may run out of memory. This is NOT default.
- Original CPU and 64 MiB step RAM controls, estimated VRAM and safety warnings remain.
- Respect Apple process limits. Do not claim Extended Virtual Addressing, Increased Memory Limit entitlement, persistent overcommit, AOT compilation, 120 Hz, or high benchmark scores merely from source changes. RAM totals and GPU budget depend on actual device, iOS signing and run conditions.

No universal RAM number simultaneously maximizes game framerate and fidelity. More guest RAM above graphics limit can cause worse performance. Full native pixels demand more GPU work than reduced render resolution. ANDD is sharpest sensible default; scaled mode remains fallback for performance.

## Apply to Kernarium checkout

The overlay validates all host source anchors before writing any; changed upstream interfaces fail closed. integrate_andarium.py applies overlay during ordinary full integration.

    python3 integrate_andarium.py --kernarium /path/to/Kernarium --source . --dry-run
    python3 integrate_andarium.py --kernarium /path/to/Kernarium --source .

For host-only change:

    python3 red_runtime_overlay.py --kernarium /path/to/Kernarium --source . --dry-run
    python3 red_runtime_overlay.py --kernarium /path/to/Kernarium --source .

Regressions (when checked out):

    python3 -m unittest discover -s tests -q

**Source coverage:** tests/test_red_runtime_overlay.py checks preflight, fail-closed behavior, idempotence, drawable propagation, preserving existing resolutions, and presence of memory/chain safeguards. Source evidence only.

## Remaining release blockers

No signed Andarium Red iOS archive or Android 17 image built in this branch. An iOS Xcode build is required to catch platform-specific Swift/Metal integration errors. Then actual iPhone must show ANDD correct dimensions portrait/landscape, custom sizes, chain behavior, touch alignment, memory under pressure, launch duration, sustained FPS and thermals. Recorded benchmarks, not invented 1–100 scores, needed before calling performance or quality maximized.

Original five project acceptance targets (Magisk root, pixel-matched red UI, clipboard, AOT/boot/FPS, apps/keyboard/Play) are **not** upgraded to PASS by this display/memory source change.
