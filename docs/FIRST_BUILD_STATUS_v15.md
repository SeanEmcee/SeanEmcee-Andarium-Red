# Andarium Red v15 — pre-build readiness ledger

**Prepared branch:** feature/andd-memory-tuning
**Base source:** imxieyi/Kernarium at fbe12ee72d195f0241c4fc24090a98b259026604
**Status:** SOURCE HANDOFF PREPARED; actual first Xcode compile has NOT run.

## Verified in development

- The live public Kernarium revision was independently retrieved, and the new overlay's exact Swift source anchor strings were checked against that commit. Result: **24 of 24** checked anchors matched across 13 files (GuestDisplayScale, GuestDisplay, Model, Resolution, Home, GuestLayer, AppEntry, PreferenceKeeper, AndariumApp, Ruler, Sheets, LiveRuntime, SessionView). Matching anchors do not prove typecheck or runtime behavior.
- Existing Android 17 launch/source integration was inspected. A genuine Kernarium checkout is pinned to the verified revision. An incomplete host tree now fails closed; minimal legacy synthetic fixtures remain permitted for preexisting Python tests.
- Kernarium's GPU EDID maximum with density is 4095 pixels/side (maximumEdidDimension). Custom widths/heights are now validated against that limit, not the separate 8192-pixel graphics protocol ceiling. ANDD rejects impossible native dimensions and warns in the picker.
- A local Swift **reconstructed policy** probe successfully ran **12 checks** (native pixels, 4095 boundary, custom linked/unlinked dimensions, finite-number protection, save/restore). This is NOT a byte-identical compile or device verification of the GitHub source.
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
