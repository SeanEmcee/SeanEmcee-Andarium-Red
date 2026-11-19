# Andarium Red v17 — pre-build hardening and acceptance tooling

**Release still NO-GO:** Source-level improvements are committed and selective Java/Swift harnesses were exercised locally. No full Android image, iOS IPA, device boot, genuine Magisk root, native AOT benchmark, or 7-day persistence run exists yet.

## v17 source improvements

- **Responsive Android HOME:** Changed the launcher from a forced four-column app grid to a width-aware one-to-four-column layout. The isolated grid logic compiled and passed **2,006 local Java assertions**, including edge widths.
- **Screen continuity:** The Android Settings/browser view now preserves an in-progress browser URL when the Nexaris-selected accent changes. Restricted package-manager lookups fail gracefully rather than crashing.
- **Verified host control colors:** The iOS host clipboard overlay is no longer hardcoded red. It adopts the RGB that Android confirmed through an authenticated ADB write/readback, with source-only tests. This is not yet compiled into a Nexaris IPA.
- **Pre-build source gate:** `--require-source-ready` makes a missing source requirement exit nonzero. The offline validator invokes it and explicitly labels `--only` filtered runs as incomplete coverage.
- **Guest persistence testing:** Added opt-in create/verify token commands for checking the guest data disk across actual restarts, app updates, and elapsed time. The marker is never treated as runtime evidence until verified in a real Android guest.
- **Nexaris status colors:** Native Nexaris Andarium development screen now shows source-implemented areas in green and keeps the engine/Android boot unverified until real driver evidence exists.

Run the offline source checks (not an IPA or Android image build):

```sh
python3 tools/prebuild_validate_v16.py --report prebuild-source-v17.json
```

After a real Android guest is running, the two-stage persistence acceptance can be done explicitly:

```sh
python3 tools/verify_guest.py --create-persistence-marker
# Save the 32-character token from the check result, restart/update the actual guest
python3 tools/verify_guest.py --check-persistence-marker <saved-32-character-token>
```

Do not run the second step until a guest restart/update has actually occurred; retest again after seven days for long-term persistence. Neither the above tooling nor a green source report is a substitute for functional device parity.

---

# Andarium Red v16 — non-disruptive Android theme handoff and offline pre-build gate

**Release: NO-GO.** The private source branch now contains a local, shell-authorized Android theme provider with a Swift write-and-readback transport. This does not boot Android 17, connect the real Nexaris runtime adapter, establish Magisk root, or prove visual parity. No GitHub Actions, Android image build, or signed IPA build has been run.

## Source improvements in v16

- The native Android launcher includes an exported `RedThemeProvider` protected by Android's `DUMP` permission and a shell/root UID check. Only an authorized guest ADB command can call it; no network service or external listener is introduced.
- Theme updates validate 24-bit RGB, commit the preference before acknowledging success, and provide an exact readback field. The iOS host now sends `content call` set/get commands instead of forcing the Android launcher into the foreground.
- Native HOME and Settings/browser screens register change listeners while visible, update their color when the preference changes, and unregister on stop to avoid retaining dead screens.
- The Swift protocol checker was compiled and exercised locally with **17 assertions**. An isolated Java provider implementation was stub-compiled and exercised locally; the complete repository's 15-assertion Java provider harness still requires running from a synced checkout.
- `tools/prebuild_validate_v16.py` runs source tests, Java harnesses and source gates locally and writes a JSON report, while always leaving runtime release status **NO-GO**. It does not call GitHub Actions, Xcode or Gradle.
- Nexaris's separate integration pull request serializes theme requests, coalesces fast changes, queues colors while Android is stopped, and replays them after a real guest boot. The actual runtime adapter remains unimplemented.

```sh
python3 tools/prebuild_validate_v16.py --report prebuild-v16-local.json
```

For a real, authenticated Android guest later, use the explicit, opt-in checks:

```sh
python3 tools/verify_guest.py --check-theme-provider
python3 tools/verify_guest.py --check-theme-write
```

The read-only check does not change the guest. The write check snapshots the old color, changes one RGB bit, verifies provider persistence and restores the original only if the test color is still present. Android offers no atomic theme compare-and-swap, so a concurrent user's change is preserved on a best-effort basis. Neither command should be run before Android 17 has actually been built and booted.

**Evidence caveat:** The bundled `PREBUILD_PARITY.json` and `RELEASE_STATUS.json` capture the previous **v14** baseline. Do not reuse their 139 Python passing-test count or 44/44 source-check number as a verified v16 full-suite result. A full Android 17 compilation, authenticated ADB integration, ROM boot, and iPhone acceptance remain required for actual functional parity.

---

# Andarium Red v15 — incremental source hardening (development branch)

**Release: NO-GO.** This branch continues the v14 source handoff; it does **not** contain a completed Android image, Magisk-booted guest, working Nexaris Android runtime adapter, AOT acceptance measurement, or signed iOS app. Source changes are not a declaration of 100% functional parity. GitHub Actions and app builds have not been run.

## v15 changes

- **Root-check reliability:** The Java `ProcessBuilder` runner drains child stdout/stderr while the process is alive, rather than waiting first and risking a full-pipe deadlock. Output is strictly bounded to 1 KiB, overflow is rejected, and the 15-second process timeout is preserved. An executable Java harness now covers 10 checks, including a 200 KiB child-output flood that passes locally.
- **Crash containment:** Native Android HOME, dashboard, Settings, and browser paths handle Android security-denied app launches and settings intents with user-visible fallback messages. They do not falsely claim an unavailable app is working.
- **Theme parity:** The guest launcher fallback color now equals Nexaris's native Crimson preset (`0xF22B43`). A separate Nexaris parity branch preserves the most recent selected RGB while no driver exists and replays the value when a genuine engine registers.
- **Regression coverage added:** `tests/test_v15_root_process.py` and `tests/test_v15_android_intent_safety.py` exercise the Java root harness and native Android stub compilation. Full repository/Android 17/device verification has not been run from this environment.

### Source verification commands (no GitHub Actions)

```sh
python3 -m unittest discover -s tests -q
python3 tools/root_probe_java_test.py
python3 tools/accent_store_behavior_test.py
python3 tools/native_home_stub_compile.py
python3 tools/android_panel_stub_compile.py
```

The original five functional acceptance targets and five additional Nexaris/stability/privacy/persistence/distribution targets remain **unverified on device**. Refer to [acceptance targets](docs/ACCEPTANCE_TARGETS.md) and the v14 baseline [release status](RELEASE_STATUS.json). The previous v14 count of 139 Python tests must not be reused as a v15 full-suite result.

---

# Andarium Red v14 — source continuation and Nexaris accent handoff

**Release: NO-GO.** This is a complete source handoff built from the prior v13 package, not an Android image or installable IPA. No GitHub Actions, signing or iPhone build was used. [Original and expanded parity targets](docs/ACCEPTANCE_TARGETS.md) • [Private GitHub repository guidance](docs/REPOSITORY_AND_BUILD.md).

## v14 source changes (local-only verification)

1. Native Android launcher and the native Settings/browser panels now load a persisted **24-bit accent RGB**. The host can supply it on a guest Activity launch under `dev.twoyi.redlauncher.NEXARIS_ACCENT_RGB`; invalid values are ignored. The guest does not claim that Nexaris host/runtime theme transport already works.
2. Added `RedAccentStore.java` and a Java behavior harness with **13 assertions** for defaults, valid/invalid colors, persistence and corruption fallback.
3. Existing **137** Python regressions remain passing; v14 adds **2** tests. Java stub compiles pass. Source gate records the new code; runtime acceptance remains blocked.
4. Verified the existing Nexaris `feature/nexaris-unified-app` branch includes `NexarisAndariumRedView.swift` and a `My Device` section below Manage ROMs, with no swipe gestures and a selected-accent hook; it is not a working Android adapter yet.

---

# Andarium Red v13 — incremental package staging and pre-build integrity audit

**Status: NO-GO for final functional parity.** This package is development source only. Target 6 (signed iOS IPA and live iPhone validation) remains deferred. No compiled Android system image, native AOT framework, Magisk-rooted guest, or iOS IPA was produced in this turn.

## Completed and locally verified in v13

- **Incremental verified APK staging:** Previously, adding HeliBoard or another APK after any initial APK bundle caused an unconditional 'different assets' failure. `host_firstboot.stage` now verifies every existing asset against its official publisher pin, preserves it, adds only requested new verified APKs, and updates the Xcode project resource group. No files are overwritten on a conflicting input.
- **Preserves custom launcher identity:** Adding optional apps later keeps the existing launcher APK’s actual size and SHA-256 pinned in `RedGuestApkInstaller.swift`.
- **Tampering and source-state checks:** Rejects unexpected files, directory symlinks, unknown project resources, duplicate Xcode entries and conflicts between the requested and already-staged official APK. Dry-run integration is unchanged.
- **New read-only build audit:** `tools/audit_staged_apks.py` checks a *real Kernarium checkout's* staged APKs against Xcode resource entries and Swift installer descriptors (size and digest) before committing build time. The audit fails if any file is absent, unrecognized or inconsistent. The local test uses synthetic fixtures; no real official APK was downloaded in this environment.
- **Regression checks:** 137/137 Python tests pass. Java clipboard behavior and Java stub compile checks and compiled Swift clipboard protocol tests also pass. Source-presence checks: 43/43. Source presence is not runtime completion.

### Run on a configured source checkout

```sh
python3 integrate_andarium.py --kernarium /path/to/Kernarium --source . --dry-run
# Apply once reviewed and the inputs are available:
# python3 integrate_andarium.py --kernarium /path/to/Kernarium --source . --magisk-apk /path/to/Magisk.apk
# On subsequent runs, provide only the additional officially verified APK(s):
# python3 host_firstboot.py --kernarium /path/to/Kernarium --heliboard-apk /path/to/HeliBoard.apk
python3 tools/audit_staged_apks.py --kernarium /path/to/Kernarium
```

The final audit requires already-staged authentic official APKs. It will not pass on this source-only ZIP, since it intentionally contains no binaries.

### Five target states

| Target | Status |
| --- | --- |
| 1. Magisk root | **NOT COMPLETE:** manager staging and diagnostic checks only; no patched, boot-tested guest |
| 2. Native red UI | **NOT COMPLETE:** launcher/Settings/browser source, not compiled under Android 17 or visually tested |
| 3. Clipboard | **NOT COMPLETE:** source and protocol tests; no platform-signed image/real ADB roundtrip |
| 4. AOT/native display | **NOT COMPLETE:** source and artifact checker only; no native artifact or frame-rate improvement proven |
| 5. Apps/keyboard/Play | **IMPROVED:** safe incremental APK staging and exact bundle audit; no live apps/keyboard verification or licensed Play Store integration |

**Known dependency:** The official Android 17 guest must be built and exercised to establish the remaining runtime behavior. No Android build, Xcode archive, or iPhone run happened in this pass.

---

## Earlier work inherited from v12

# Andarium Red v12 — Canonical clipboard, concurrent-edit safety, verified AOT candidates

**Release state: NO-GO.** This is a source package for the existing Andarium Red/Kernarium Android 17 project, not a signed IPA, tested Android image, working Magisk boot or FPS benchmark. **User target 6 has been deliberately deferred.** No Android 17 system image or iPhone device build was made.

## New in v12 (locally verified)

1. **Canonical clipboard encoding in all three runtimes:** Android's provider now checks decoded URL-safe Base64 by encoding it again, rejecting non-zero unused bits. Swift's host decoder makes the same canonical comparison, and the live Python ADB verifier no longer searches substring matches inside untrusted shell output. Exact single-field Bundle parsing rejects duplicate, injected or malformed replies. No clipboard data is logged.
2. **Concurrent clipboard protection:** The explicitly opt-in guest test snapshots the original text, verifies it is unchanged just before writing, and restores it only if the test's own value is still there. If an app/user replaces the clipboard mid-test, the verifier preserves that newer content. Android has no atomic compare-and-swap clipboard API, so this is a best-effort protection, not a zero-race guarantee.
3. **AOT release-candidate validation:** The AOT pipeline verifies required descriptor fields, exact release ID syntax, full SHA-256 digests and the requested archive policy. It then invokes Kernarium's own `release_artifact.py verify --accepted ... --release ...` and deletes an invalid generated candidate. It never copies candidate settings into the accepted release metadata or claims compiled acceleration.
4. **New regression tests:** 126/126 Python tests pass, including ten new clipboard safety cases and seven AOT candidate validation cases. Real Java provider behavior harness passes 10 assertions; Swift clipboard behavior harness, Swift source syntax and Android Java *stub* compiles pass.

**Still not complete:** The five overall targets require a real Android 17 guest image for Magisk init/daemon root, platform-signed clipboard, native UI and installed app/keyboard verification. AOT artifact production and FPS measurements remain outstanding. We have not started item 6.

## Prior v11 changes still included

1. **Android↔iOS clipboard format integrity:** `host/RedClipboardCodec.swift` now requires an exact `content call` Bundle response, refuses ambiguous/duplicate keys and malformed base64, and bounds the encoded payload before allocation. The Java `ClipboardBridgeProvider` refuses malformed UTF-8 and noncanonical base64 before changing clipboard content. Explicit user actions and 32 KiB limit remain.
2. **No repeat package scan after completed first boot:** `host_firstboot.py` now records the completed guest run mark. Duplicate console boot-complete notifications cannot restart a package scan after the first completed pass. A new boot/run can still scan again.
3. **Safe v10 in-place upgrade:** An existing v10 `LiveRuntime.swift` first-boot method is replaced only when its original body matches the reviewed v10 template. Owner-customized versions fail closed; an already-upgraded method is unchanged. The installation hook is not duplicated.
4. **Reject fake launchers:** launcher staging now requires an Android binary manifest and a well-formed DEX *header*, in addition to ZIP integrity and exact runtime SHA-256 pinning. This is a structural guard only; it does **not** replace Android package signature and identity verification at install time.
5. **AOT archive acceptance candidate:** `tools/aot_artifact_pipeline.py --archive-candidate` now asks upstream's descriptor generator for `--archives yes` after building and verifying a real matching AOT artifact. The default remains `--archives no`. The command writes only a *candidate* descriptor and never edits upstream's `accepted-aot.env` or enables it without validation. No AOT artifact was built here.

## Current upstream situation

Public `imxieyi/Kernarium` main was observed at `fbe12ee72d195f0241c4fc24090a98b259026604` on 19 Nov 2026. That commit merges default selection of an AOT component **when a matching accepted artifact exists**; it does not by itself mean App Store archives contain AOT. This retrofit was originally developed against `538de0dddaa0af5779bfbf7bb8e12e0938c3389a`. Compatibility with newer revisions needs actual checkout and compile checks; code anchor presence is not enough to certify compatibility.

## Local verification

Commands run in this source directory:

```sh
python3 -m unittest discover -s tests -q
python3 tools/java_compile_smoke.py
python3 tools/clipboard_provider_behavior_test.py
python3 tools/root_probe_java_test.py
python3 tools/native_home_stub_compile.py
python3 tools/android_panel_stub_compile.py
swiftc -frontend -parse host/*.swift tests/SwiftClipboardHarness.swift
swiftc host/RedClipboardCodec.swift tests/SwiftClipboardHarness.swift -o /tmp/red-clipboard-test
/tmp/red-clipboard-test
python3 tools/prebuild_parity.py --report PREBUILD_PARITY.json
```

**Prior v11 results:** 109/109 Python tests passed, Java native-screen **stub** compilation passed, real clipboard provider Java method tests passed (9 assertions), Java root probe (7 assertions) passed, Swift syntax parsing and compiled Swift clipboard behavior harness passed, and 38/38 source checks passed. `NO-GO` remains correct: none of those is an Android Soong build, Xcode build or iPhone proof.

## Targets 1–5: reality check

| Target | Source changes available | Missing before functional completion |
|---|---|---|
| **1. Magisk-managed root** | Verified Magisk manager APK pin, `init_boot` auditor, diagnostic `userdebug`/`su`, real UID0/Magisk test | Magisk init/daemon-compatible boot artifacts, rebuilt guest and guest-side `su` proof. |
| **2. Red native UI** | Android native HOME, functional Settings/browser panels and APK drawer | Real Android 17 compilation, UI testing and pixel/interaction parity. |
| **3. Clipboard** | Privileged provider and iOS buttons, now strict Unicode and response handling | System image inclusion, real platform grant and iOS↔guest roundtrip. |
| **4. Fast AOT/native display** | Native resolution default, one-time first-boot APK scans, accepted AOT candidate workflow | Native artifact built/accepted and FPS, thermal and boot profiling on iPhone. |
| **5. Apps/keyboard/Play** | Six pinned official APK entries, safe import, APK validation; HeliBoard activation check | Actual package installation, keyboard typing, browser rendering, and properly licensed Play Services integration. |

**Green source checks are not 100% functional parity.** The complete five-target release gate is intentionally blocked. `RELEASE_STATUS.json` is the machine-readable status, and `PREBUILD_PARITY.json` records source gates and runtime gates separately.

### Source integration

```sh
python3 integrate_andarium.py --kernarium /path/to/Kernarium --source . --dry-run
```

For real source application, omit `--dry-run` after preflight. Source changes modify the Kernarium checkout and require its own Android image producer/release workflows. `--diagnostic-userdebug` is for development only, not a Magisk-rooted release. Do not try to bypass accepted artifact or iOS entitlement checks.

### AOT candidate workflow

```sh
python3 tools/aot_artifact_pipeline.py --kernarium /path/to/Kernarium --release /path/to/installed/android17/release --fsck-erofs /path/to/fsck.erofs --out /path/to/aot-artifact --archive-candidate
```

This prints a read-only build plan by default. Add `--run` only in a build environment with the real release and `fsck.erofs` with zstd support. Review and accept the output through Kernarium's official release process before any runtime packaging; a generated candidate is not automatically a release.

## v12 validation

```sh
python3 -m unittest discover -s tests -q
python3 tools/clipboard_provider_behavior_test.py
python3 tools/java_compile_smoke.py
python3 tools/native_home_stub_compile.py
python3 tools/android_panel_stub_compile.py
swiftc -frontend -parse host/*.swift tests/SwiftClipboardHarness.swift
python3 tools/prebuild_parity.py --report PREBUILD_PARITY.json
```

The source gate is **41/41**, but the overall release gate remains **NO-GO**. The integrated Android source and iOS app have not been compiled or booted on device.
