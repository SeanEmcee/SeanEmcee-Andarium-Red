> **v17 extension:** The Android HOME→native Nexaris five-app shortcut source and crossfade logic are now committed in **both** private repositories. Java route wire **45/45**, Swift route wire **25/25** and Android-shaped provider behavior **17/17** checked against exact GitHub blobs. The actual Nexaris Andarium runtime adapter, Android 17 image, Xcode build and physical iPhone fade remain **unverified**. See [v17 handoff](ANDROID_HOST_HANDOFF_v17.md). The v15 checks below remain historical baseline, not an updated release certification.

# Andarium Red v15 — pre-build readiness ledger

**Prepared branch:** feature/andd-memory-tuning
**Base source:** imxieyi/Kernarium at fbe12ee72d195f0241c4fc24090a98b259026604
**Status:** SOURCE HANDOFF EXTENDED; actual first Xcode compile has NOT run.

## v15.1 — expanded implementation and configuration audit

**Source progress:** memory mode and reference-style UI are now configurable and persistent. **Release remains NO-GO** until an Android17 image, Xcode build and physical iPhone test pass.

Completed configuration code:
- Reference-matched red Android home is default on first run; Android Settings and browser reference hit areas now use real guest actions. A saved menu choice switches between the reference art and adaptive native Swift/Android widgets. Reference artwork is fixed-red (not dynamically recolored) and has not been screenshot-compared.
- New guest RAM profile selection persists among Max quality, Graphics priority, High RAM, and Device limit. Changing the default does not silently reconfigure an existing guest. Risks are reported when exceeding safe RAM/graphics headroom.
- ANDD/custom resolution portable Swift state now rejects malformed persisted ratio values and overflow; **22 policy assertions** passed in a Linux Swift compiler harness, plus **12** memory preference assertions. These local tests do **not** typecheck the full SwiftUI host.
- A real user-triggered Java root check is exposed by the reference home. It does not perform Magisk installation or imply an initialized Magisk daemon. Userdebug `su` is not Magisk-managed root.
- Nexaris's native Andarium management page now correctly names the existing private repository. Actual `NexarisAndariumGuestRuntime` registration still needs a compiled/embedded runtime.
- First-build script can fetch/pin-verify six official Android APKs and stage a separately supplied Android17 unsigned proof. It does not synthesize or sign a new ROM image itself.
- The source gate checks for retained upstream camera, microphone, location and persistent guest-instance implementations, and requires Java behavior compiles (six harnesses), Python regression suite and Swift state checks on the checkout.

**New first-build options:**

```sh
bash scripts/first_build.sh /path/to/Kernarium --with-apps
bash scripts/first_build.sh /path/to/Kernarium --preview
bash scripts/first_build.sh /path/to/Kernarium --build --with-apps --guest-proof /path/to/android17/unsigned-release
```

**Unfinished work is not erased by configuration:** an actual Magisk-integrated Android image, matching/validated Android launcher pixels, the live clipboard transport, approved Google components, Nexaris compiled engine adapter, signed IPA, iPhone boot, >7-day persistence proof, heat/120Hz benchmarks and device crash fixes remain to be completed and verified. The Xcode preview/full compile and full new-branch tests have not been executed in the checked-out GitHub repository.

---

## Verified in development

- The live public Kernarium revision was independently retrieved, and the new overlay's exact Swift source anchor strings were checked against that commit. Result: **24 of 24** checked anchors matched across 13 files (GuestDisplayScale, GuestDisplay, Model, Resolution, Home, GuestLayer, AppEntry, PreferenceKeeper, AndariumApp, Ruler, Sheets, LiveRuntime, SessionView). Matching anchors do not prove typecheck or runtime behavior.
- Existing Android 17 launch/source integration was inspected. A genuine Kernarium checkout is pinned to the verified revision. An incomplete host tree now fails closed; minimal legacy synthetic fixtures remain permitted for preexisting Python tests.
- Kernarium's GPU EDID maximum with density is 4095 pixels/side (maximumEdidDimension). Custom widths/heights are now validated against that limit, not the separate 8192-pixel graphics protocol ceiling. ANDD rejects impossible native dimensions and warns in the picker.
- The portable Swift policy was manually reproduced from repository source and compiler-tested with **22 assertions**, including corrupted settings and linked-ratio protection. Memory preference state was also compiled/tested with **12 assertions**. These are focused source checks, **not** Xcode/SwiftUI or device verification.
- Compilable standalone portable Swift value-test harness and automated Python unit coverage added to repo for the build machine.
- Source staging is integrated into the existing installer, plus an explicit read-only first-build gate checks the exact copied files, EDID/backend consistency, host source anchors, Python regressions, Swift value behavior, entitlement declarations and staged runtime/image inputs.
- No GitHub Actions, signing, or privileged device operation run.

## What cannot yet be marked PASS

- All existing Python/Java/Swift tests **as run from the newly staged repository**: not executed end-to-end in the current runtime because the private repository checkout and a full Kernarium working tree are not mounted here.
- Xcode 27 target compilation (AndariumPreview and Andarium): no macOS/Xcode device build environment attached.
- A rebuilt native Android 17 guest (Magisk, clipboard, launcher, apps) and accepted proof image: not produced.
- Accepted runtime XCFramework, staged release image, Apple provisioning/codesign, IPA and device FPS/memory thermal stability: not verified.

## Commands for the real first build

```bash
# In your private Andarium Red repo clone:
bash scripts/first_build.sh /absolute/path/to/Kernarium
bash scripts/first_build.sh /absolute/path/to/Kernarium --preview

# Only after accepted Android image and matching iOS runtime dependencies exist:
bash scripts/first_build.sh /absolute/path/to/Kernarium --build
```

The first command runs preflight, integrates source and tests. The second attempts an unsigned **UI preview compile without Android**. The last packages the accepted runtime and attempts an unsigned full host iOS compile. None signs an IPA, bypasses iOS entitlements, or certifies Android guest behavior.

**Decision:** The source is staged for the first build attempt and equipped to fail with useful diagnostics. **Do not merge to a released/100%-verified branch until Xcode and physical-device acceptance results exist.**
