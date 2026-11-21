# Functional parity acceptance — v16 source continuation

Do **not** interpret a green source check as 100% functional parity. Each target passes only when its guest image, host app, and device behavior have been built and independently exercised. The supplied concept artwork is a visual reference, not functioning UI.

## The original five targets

| # | Requested target | Required acceptance evidence | State on 2026-11-19 |
|---|---|---|---|
| 1 | Rooted Android 17 with Magisk-managed superuser | Boot a compatible guest and prove `id -u` gives 0 **through consented Magisk** (not a diagnostic `userdebug su`) | NOT VERIFIED |
| 2 | Pixel-matched AMOLED / adaptive launcher, Settings, Titanium browser | Actual Android 17 build, functional interactions and side-by-side pixel comparisons against three reference PNGs | NOT VERIFIED |
| 3 | Android 17 + bidirectional iOS clipboard | Correct guest Android version and platform signatures; explicit host↔guest Unicode transfer roundtrip | NOT VERIFIED |
| 4 | Native resolution + genuine AOT + fast boot | Accepted AOT artifact matches the signed runtime, measured cold/warm boots, FPS/heat under sustained use on iPhone | NOT VERIFIED |
| 5 | Real apps, HeliBoard and Play compatibility | Package installs, HeliBoard selected and typed successfully, real browser rendering, separately licensed/compatible Google services | NOT VERIFIED |

## Additional requirements carried forward

| # | Requirement | Acceptance evidence | State |
|---|---|---|---|
| 6 | Independent Andarium Red area in Nexaris My Device, directly below Manage ROMs; no vertical open/close gestures; inherit Nexaris selected accent | Nexaris native navigation plus real runtime driver and same-color Android display verified on iPhone | UI source exists, live runtime unconnected |
| 7 | No unexpected native host crashes, sustained Settings and App Manager use, bounded memory/thread growth | Instrumented iPhone soak tests and native thread/memory crash statistics | NOT VERIFIED |
| 8 | Authorized iOS permission bridge (clipboard, microphone, camera, location as supported) | User prompts, explicit handoff, sandbox checks and device tests per permission | Clipboard source only |
| 9 | Persistent Android guest and one-tap access; survive relaunch and more than seven days | Reboot, app update, container and signing-expiry tests with preserved guest app data | NOT VERIFIED |
| 10 | Authorized signed IPA, LiveContainer compatibility and device testing | Signed iOS archive and iPhone 14 Pro Max on iOS 27.3 running guest with real diagnostics | NOT VERIFIED |

## What v17 changes (source only)

- A responsive Android-native HOME grid now adapts from one to four columns; the layout arithmetic compiled and passed 2,006 local assertions. Full Android UI pixel matching remains unverified.
- The Android browser panel retains a partially entered URL during accent changes.
- The iOS clipboard icon/border follow an accent confirmed by Android rather than staying permanently crimson.
- The pre-build gate now returns a failing exit status for any missing source requirement, even while the release gate correctly remains NO-GO.
- An opt-in two-stage guest persistence marker supports post-boot and post-update verification but has not yet been run against a device.
- Nexaris marks **source-implemented** interface areas green, while missing runtime integration and unbooted Android remain visibly unverified.

**No completion claim** is made for any of the original five or five added functional targets until independent Android/iPhone acceptance passes.

## What v16 changes (source only)

- The Android launcher now has a package-local, shell-authorized RGB ContentProvider, requiring the `DUMP` permission and checking the calling UID; 24-bit colors are durably saved before responding.
- The iOS-side guest ADB bridge writes the value and reads it back, validating exact `Bundle` replies. Unlike a launcher `am start` action, this transport does not forcibly foreground Android HOME.
- Native launcher and Settings/browser components observe RGB updates while visible.
- The live verifier has opt-in `--check-theme-provider` (read-only) and `--check-theme-write` (restored when unchanged) probes.
- Local Swift source protocol harness passed 17 cases, and an isolated Java provider compile/smoke check passed. The full native Android 17 build and full repository test suite remain unverified.
- The v16 single-command source validator cannot override a missing runtime acceptance gate, even when all source checks pass.

**Target 6 remains INCOMPLETE**: Nexaris has a runtime protocol and queued/coalesced theme calls but no compiled, connected engine adapter. Theme readback is not equivalent to verified Android pixels on the iPhone.

## What v14 changes

- Implements persistent 24-bit RGB guest color input via `dev.twoyi.redlauncher.NEXARIS_ACCENT_RGB` launch extra, honoring the selected accent in the native home and native panel UIs. It does not automatically provide a transport between iOS and Android.
- New Java behavior tests check defaults, accepted colors, persistence, invalid and corrupt values. Existing checks are preserved.
- The native Nexaris side has its own SwiftUI screen and `applyAccentRGB` adapter API on `SeanEmcee/Nexaris`, `feature/nexaris-unified-app`. This source package does not embed or modify that repository.

**Release gate: NO-GO** until runtime acceptance exists for all targets. Pixel perfection cannot be certified from Java stub compilation or a screenshot preview. No Android 17 image or iOS app has been compiled in this package.
