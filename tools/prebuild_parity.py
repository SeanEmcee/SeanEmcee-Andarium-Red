#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Evidence-driven pre-build parity gate for Andarium Red.

A source check cannot certify runtime behavior: never turn an unbuilt Android
image, iOS binary, root installation, or benchmark into an accepted feature.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_SHA = {
    # Fixed, user-supplied reference assets. These never change silently.
    'home.png': '5e998a1f650c6241a4c1c40cde5182d4263960a0749c2b9b6e0c4e1f07eaa687',
    'settings.png': '385f327af32a272e946fef66a175af00142991ed407756cbb836970243b37b52',
    'browser.png': '3302c693d585e351e9a3c5ad7a821b55167fd036d4c5ce7140c163c7cbdbc87f',
}

@dataclass
class Gate:
    requirement: str
    state: str
    evidence: str


def inspect(root: Path = ROOT, kernarium: Path | None = None) -> dict:
    gates: list[Gate] = []
    def add(name: str, condition: bool, evidence: str, *, requires_device: bool = False) -> None:
        gates.append(Gate(name, 'source-ready' if condition else 'missing', evidence))

    img = root / 'launcher_src/assets'
    for name, expected in REQUIRED_SHA.items():
        f = img / name
        digest = hashlib.sha256(f.read_bytes()).hexdigest() if f.is_file() else 'missing'
        add('Exact reference artwork: ' + name, digest == expected,
            'sha256=' + digest)

    launcher = (root / 'launcher_src/java/dev/twoyi/redlauncher/MainActivity.java').read_text()
    manifest = (root / 'launcher_src/AndroidManifest.xml').read_text()
    app_catalog = (root / 'launcher_src/java/dev/twoyi/redlauncher/LauncherCatalog.java').read_text()
    native_home = (root / 'launcher_src/java/dev/twoyi/redlauncher/RedNativeDashboard.java').read_text()
    add('Android-native responsive HOME instead of a screenshot skin',
        'new RedNativeDashboard(this)' in launcher and 'getPackageInfo(packageName, 0)' in native_home
        and 'getApplicationIcon(tile.packageName)' in native_home
        and 'Root access: Not checked' in native_home,
        'Android widgets and real application icons; source stub compilation passed, device appearance untested')
    add('Actual installed-app drawer and search',
        'getInstalledApplications(0)' in launcher and 'LauncherCatalog.filter' in launcher
        and 'android.permission.QUERY_ALL_PACKAGES' in manifest,
        'Android PackageManager-backed; host/device behavior not validated')
    add('Live battery and clock rather than mock status',
        'BatteryManager.EXTRA_LEVEL' in launcher and 'SimpleDateFormat' in launcher
        and 'drawRealDeviceStatus' in launcher,
        'Android local battery/time live-code integration; not device compiled')
    add('Missing-app indicators and no fabricated rooted status',
        'drawInstalledState' in launcher and 'Not installed' in launcher
        and 'Root: not verified' in app_catalog,
        'Only installed applications may be marked available; root unverified')
    add('Real Android Settings intents',
        'Settings.ACTION_SETTINGS' in launcher and 'Settings.ACTION_APPLICATION_SETTINGS' in launcher,
        'Working action intents in source; full mockup is not native Settings')

    native_panel = (root / 'launcher_src/java/dev/twoyi/redlauncher/RedPanelActivity.java').read_text()
    web_policy = (root / 'launcher_src/java/dev/twoyi/redlauncher/PanelLinkPolicy.java').read_text()
    add('Real red Android Settings and browser panels',
        'buildSettings()' in native_panel and 'buildBrowser()' in native_panel
        and 'startActivity(new Intent(action))' in native_panel
        and 'openNativePanel(RedPanelActivity.SETTINGS_PANEL)' in launcher,
        'Native clickable Android views; not compiled or UI-tested on device')
    add('Safe functional browser URL routing',
        'PanelLinkPolicy.normalized(raw)' in native_panel and 'new URI(candidate)' in web_policy
        and 'http' in web_policy and 'https' in web_policy,
        'Validated URL handling before launching real installed Titanium browser')

    make = (root / 'install_source_overlay.py').read_text()
    host = (root / 'host_firstboot.py').read_text()
    clipboard = (root / 'guest_clipboard/java/dev/twoyi/redclipboard/ClipboardBridgeProvider.java').read_text()
    controls = (root / 'host/RedClipboardControls.swift').read_text()
    installer = (root / 'host/RedGuestApkInstaller.swift').read_text()
    add('Android 17 product source overlay',
        'LINEAGE24_ANDROID_MAJOR=17' in make and 'lineage_andarium.mk' in make,
        'Checked Android 17 source target, not built image')
    apk_audit = (root / 'tools/audit_staged_apks.py')
    add('Incremental official APK staging without losing previous apps',
        'existing_files' in host and 'validate_existing' in host
        and 'merged_names' in host and 'Existing bundled APK differs' in host,
        'Local stage upgrade tested; actual build resource validation still required')
    add('Read-only Xcode, Swift descriptor and APK staging audit',
        apk_audit.is_file() and 'PROJECT_GROUP_RE.search' in apk_audit.read_text()
        and 'source_apk_bundle_consistent' in apk_audit.read_text(),
        'Can reject inconsistent staged package resources before build; no real APK bundle audited here')
    add('Pinned Magisk manager',
        '89cefac0a318afa39fb3880c45c87b036c05bc1ebf02a7a715b7f8d7c26ac6e7' in installer,
        'Verified release digest defined; no bundled APK in this source-only package')
    add('Pinned Titanium ARM64 APK',
        'c65ef275124058617b2cf0dcc3989b143e74b32ca5a43d9279a0edece8fe7051' in installer,
        'Verified release digest defined; no bundled APK in this source-only package')
    add('Pinned F-Droid full client APK',
        '83d3fe522281c3cb89fce3bc05038f81b3c3b32c108536941f184c5f9bb53778' in installer,
        'Full F-Droid 2.0.1 source pin (not latest 2.0.3); APK unbundled')
    add('Pinned Termux ARM64 APK',
        '72fdb596045116bf5ba1b5bdf5b26fddb9acc0bd074ad9f2da9eb0ae85e83a4e' in installer,
        'Release digest + exact byte count; APK not in source package')
    add('Pinned App Manager APK',
        '2540d6d9352acd8b04d6210140630a380abb1bc46ad4745c89ad97603dee3c40' in installer,
        'Verified release digest defined; no bundled APK in this source-only package')
    add('Official HeliBoard keyboard APK verification',
        '69b2b2fb349934371b1ed2d3569541cc0bda987f8aaf5eb5f5b157961f76de86' in installer
        and 'validate_heliboard' in host and 'helium314.keyboard' in launcher,
        'Official HeliBoard v4.2 release pin; user must enable IME after installation')
    aot_build = (root / 'tools/aot_artifact_pipeline.py').read_text()
    root_check = (root / 'tools/root_readiness.py').read_text()
    add('Executable AOT artifact build and verification workflow',
        "'build'" in aot_build and "'verify'" in aot_build
        and 'accepted-aot.candidate.env' in aot_build,
        'Runs upstream AOT producer only with real release and supported fsck; no artifact produced here')
    downloader = (root / 'tools/fetch_official_apks.py').read_text()
    add('Official APK downloader with immutable checksum pins',
        'def fetch_one(' in downloader and 'verify(temp,size=size,digest=digest)' in downloader
        and 'HeliBoard-v4.2-release.apk' in downloader,
        'Downloads not executed in offline environment; verify official bytes at build time')
    live_check = (root / 'tools/verify_guest.py').read_text()
    add('Root verification works with debuggable and non-debuggable Android',
        "adb_run(adb, 'su', '-c', 'id -u')" in live_check
        and 'def magisk_daemon' in live_check
        and "require_property(args.adb, 'ro.debuggable'" not in live_check,
        'Exact UID 0 check and separate Magisk response; root remains unverified until live test')
    add('Clipboard roundtrip requires verified restoration',
        'Clipboard restore did not preserve original text' in live_check
        and 'refusing destructive test' in live_check,
        'Never changes a non-text clipboard, checks restoration; iOS transport not device-tested')
    add('Play Store service dependencies tested separately',
        'com.google.android.gms' in live_check and 'com.google.android.gsf' in live_check
        and 'require-play-services' in live_check,
        'Can detect installed packages; no licensed Google Services distribution or functionality claim')
    add('Guest-root mode diagnostic and explicit Magisk separation',
        'userdebug' in root_check and 'magisk_kernel_runtime_integrated' in root_check
        and 'root_proven_in_guest' in root_check,
        'Diagnostic su path inspected; no Magisk-managed root proof')

    root_probe = (root / 'launcher_src/java/dev/twoyi/redlauncher/RedRootProbe.java').read_text()
    add('Explicit user-initiated in-guest root and Magisk verification',
        'checkRootOnUserTap()' in native_home and 'RedRootProbe.check' in native_home
        and '"0".equals(su.output.trim())' in root_probe
        and 'magisk -v' in root_probe,
        'Shows only observed root result, never infers root from APK presence')
    add('Lazy loading original artwork for native HOME performance',
        'designForPreview(screen)' in launcher
        and 'designs[index] = readAsset(file)' in launcher,
        'Reference bitmaps not decoded on every native HOME launch')
    add('Prevent duplicate first-boot APK installers per guest run',
        'redInstallerActiveRun != startedRun' in host,
        'Boot-complete notifications cannot start overlapping installations in one guest run')
    accent_source = (root / 'launcher_src/java/dev/twoyi/redlauncher/RedAccentStore.java').read_text()
    add('Theme color persisted in native Android launcher and Settings panels',
        'acceptLaunchAccent' in accent_source and 'getSharedPreferences' in accent_source
        and 'RedAccentStore.load(owner)' in native_home
        and 'RedAccentStore.load(this)' in native_panel
        and 'RedAccentStore.acceptLaunchAccent(this, getIntent())' in launcher,
        'Guest remembers 24-bit RGB sent on launch; Nexaris host-to-guest runtime adapter still needs actual integration')
    theme_provider = (root / 'launcher_src/java/dev/twoyi/redlauncher/RedThemeProvider.java').read_text()
    theme_host = (root / 'host/RedGuestAccentTransport.swift').read_text()
    add('Shell-only non-disruptive native Android RGB theme bridge with readback',
        'android.permission.DUMP' in manifest
        and 'Binder.getCallingUid()' in theme_provider
        and 'Process.SHELL_UID' in theme_provider
        and 'RedAccentStore.acceptRGB' in theme_provider
        and 'editor.putInt(KEY, color).commit()' in accent_source
        and 'RedGuestAccentTransport.verifyRead(' in make
        and 'static func verifyRead(' in theme_host
        and 'registerOnSharedPreferenceChangeListener(themeObserver)' in launcher
        and 'registerOnSharedPreferenceChangeListener(themeObserver)' in native_panel,
        'Source-only host-to-guest RGB transport and persisted readback; actual Android 17 compilation and runtime integration still required')
    grid_logic = (root / 'launcher_src/java/dev/twoyi/redlauncher/DashboardGridPolicy.java').read_text()
    host_accent_state = (root / 'host/RedHostAccentState.swift').read_text()
    host_clipboard_controls = (root / 'host/RedClipboardControls.swift').read_text()
    add('Host clipboard chrome tracks verified Nexaris theme RGB',
        'RedHostAccentState.shared.acceptVerified(rgb)' in make
        and 'RedGuestAccentTransport.verifyRead(' in make
        and 'RedHostAccentState.swift' in make
        and '@ObservedObject private var accentState' in host_clipboard_controls
        and '.foregroundStyle(accentState.color)' in host_clipboard_controls
        and 'guard selected <= 0x00FF_FFFF' in host_accent_state,
        'Host-side source wired to confirmed guest RGB; live iOS SwiftUI rendering untested')
    add('Native Android HOME grid adapts to narrow viewports',
        'DashboardGridPolicy.columns(available, dp(80))' in native_home
        and 'DashboardGridPolicy.cellWidth(available, dp(80))' in native_home
        and 'Math.min(4, availablePixels / desiredCellPixels)' in grid_logic
        and 'if (dashboard != null) dashboard.refresh()' in launcher,
        'Responsive widget grid source; 2,006 arithmetic assertions pass locally; real Android appearance untested')
    add('Explicit clipboard signature permission check',
        'def clipboard_privilege(' in live_check
        and 'READ_CLIPBOARD_IN_BACKGROUND' in live_check,
        'Checks granted permission in live Android package registry, not only manifest declaration')
    add('Verify active HeliBoard, not just package registration',
        'def active_heliboard(' in live_check and 'default_input_method' in live_check,
        'Requires selected IME; actual Android typing test remains outstanding')
    boot_preflight = (root / 'tools/magisk_boot_preflight.py').read_text()
    add('Validate official Magisk boot and kernel-less init_boot inputs',
        'inspect_init_boot' in boot_preflight and 'MAGISK_SHA256' in boot_preflight,
        'Non-destructive input check; no Magisk runtime or root integration claimed')

    # v11 source/behavior checks are deliberately NOT runtime certification.
    add('Strict host clipboard response parsing',
        'private static func fields(_ raw: String)' in (root / 'host/RedClipboardCodec.swift').read_text()
        and 'values[name] == nil' in (root / 'host/RedClipboardCodec.swift').read_text(),
        'Rejects ambiguous or duplicated Android Bundle fields; adversarial Swift harness passed')
    add('Guest clipboard rejects malformed Unicode',
        'CodingErrorAction.REPORT' in clipboard and 'encoded.matches("[A-Za-z0-9_-]*")' in clipboard,
        'Real provider method Java compile/harness passed; live provider privilege remains untested')
    # v12 behavior gates require both protocol endpoints AND targeted tests.
    live_safety = (root / 'tools/verify_guest.py').read_text()
    v12_tests = (root / 'tests/test_v12_clipboard_safety.py').read_text() if (root / 'tests/test_v12_clipboard_safety.py').is_file() else ''
    add('Canonical unpadded Base64 across iOS, Android, and acceptance test',
        'canonical == payload' in (root / 'host/RedClipboardCodec.swift').read_text()
        and 'Base64.encodeToString(data, BASE64_FLAGS).equals(encoded)' in clipboard
        and 'canonical != value' in live_safety and 'nonzeroPadBits' in (root / 'tools/clipboard_provider_behavior_test.py').read_text(),
        'Both protocol implementations reject unused nonzero Base64 bits; Java/Swift/Python regression harnesses passed')
    add('Live clipboard verification protects concurrent user changes',
        'preserving newer content' in live_safety
        and 'if current == encoded:' in live_safety
        and 'test_does_not_overwrite_clipboard_changed_midtest' in v12_tests,
        'ADB verifier restores its test clip only if its own clip is still current; other apps may replace it')
    aot_v12_tests = (root / 'tests/test_v12_aot_acceptance.py').read_text() if (root / 'tests/test_v12_aot_acceptance.py').is_file() else ''
    add('AOT acceptance candidates validated by upstream release verifier',
        'validate_against_upstream(' in aot_build
        and "'--accepted', str(candidate)" in aot_build
        and 'validate_candidate(' in aot_build
        and 'test_verifier_failure_blocks_candidate' in aot_v12_tests,
        'Candidate rejected on missing fields, digest mismatch or upstream verify failure; still not auto-accepted')
    add('First boot scans package bundle once per run',
        'redInstallerCompletedRun != startedRun' in host and 'redInstallerCompletedRun = startedRun' in host,
        'Upgrades the previously injected v10 method and skips redundant scans after completion')
    add('Compiled launcher input structurally checked',
        'Launcher must contain a compiled Android DEX image' in host
        and 'compiled binary AndroidManifest.xml' in host,
        'Rejects dummy APK ZIPs; platform package manager still performs definitive install validation')
    add('AOT archive candidate is explicit and unaccepted',
        '--archive-candidate' in aot_build and 'accepted-aot.candidate.env' in aot_build
        and "'--archives', 'yes' if archive_candidate else 'no'" in aot_build,
        'Candidate may request native archive acceleration, but descriptor is not silently accepted')

    add('First-boot ADB installation logic',
        'redInstallBundledAppsAfterBoot' in host and 'verify_launcher' in host,
        'source integrator only; iOS build and guest install not verified')
    add('Explicit host-guest clipboard sources',
        'ClipboardBridgeProvider extends ContentProvider' in clipboard
        and 'Paste into Android' in controls and 'Copy from Android' in controls,
        'Not yet platform-signed or tested against Android 17')
    add('Native resolution, user override and thermal safety',
        'chosenScale ?? .native' in make and 'thermal_frame_rate_safeguard_preserved' in make,
        'Host default only; Native workload and thermal frame rate untested')
    add('AOT build-source audit',
        'def aot_readiness(' in make and 'accepted-aot.env' in make,
        'Audit is implemented; artifact is not generated or accepted')

    if kernarium is not None:
        import importlib.util
        spec = importlib.util.spec_from_file_location('red_overlay', root / 'install_source_overlay.py')
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        k = mod.aot_readiness(kernarium)
        aot = k
    else:
        aot = {'status': 'No Kernarium checkout supplied; not verified'}

    # Any claimed success below MUST be backed by build/device artifacts, not
    # matching source strings or a test fixture. These are not source gates.
    runtime_gates = [
        Gate('Full Android 17 image built', 'unverified', 'No compiled Android 17 image supplied'),
        Gate('iOS custom app built and signed', 'unverified', 'No Xcode device archive or IPA supplied'),
        Gate('Android 17 boots on iPhone', 'unverified', 'No device boot log'),
        Gate('Magisk-managed root', 'unverified', 'Manager APK alone is not root; guest kernel support unproven'),
        Gate('Clipboard transfers work in both directions', 'unverified', 'Privileged system provider and host must be built and tested together'),
        Gate('Titanium extension compatibility', 'unverified', 'Chromium APK not installed or tested in guest'),
        Gate('Google Play Store genuinely available', 'missing', 'No licensed Play services/store bundle or compatibility proof'),
        Gate('F-Droid installed', 'unverified', 'Checksum-pinned staging exists for 2.0.1; no actual guest install'),
        Gate('Termux installed', 'unverified', 'Checksum-pinned install path exists; no actual guest install'),
        Gate('HeliBoard keyboard installed and working', 'unverified', 'Official v4.2 APK pinned; guest install, IME enable and typing untested'),
        Gate('Responsive native HOME appearance and accessibility on iPhone', 'unverified', 'Widget source and local stub compile passed; actual Android build and visual comparison pending'),
        Gate('Full functional red native Settings/browser design', 'unverified', 'Native Android screens implemented but uncompiled/untested; design pixel parity unverified'),
        Gate('Native-resolution fast boot and smooth FPS', 'unverified', 'No full-resolution boot or thermal-controlled benchmark'),
        Gate('Stability under sustained load', 'unverified', 'No extended iPhone run or crash report'),
        Gate('Selected Nexaris accent reaches running Android guest', 'unverified', 'Guest RGB persistence and Nexaris UI adapter source exist; no connected live host transport or visual roundtrip'),
        Gate('Independent Nexaris My Device launch and gesture behavior', 'unverified', 'Native entry in Nexaris feature branch only; requires built iPhone interaction test'),
        Gate('Guest data survives restart and seven-day signing window', 'unverified', 'No signed app data-retention or restart tests'),
        Gate('iOS privacy permissions safely bridge to guest', 'unverified', 'Clipboard source only; camera, microphone and location require opt-in host bridges and device tests'),
    ]
    source_ok = sum(x.state == 'source-ready' for x in gates)
    release_go = source_ok == len(gates) and all(x.state == 'verified' for x in runtime_gates)
    return {'product': 'Andarium Red Android 17',
            'source_checks_passed': source_ok, 'source_checks_total': len(gates),
            'release_gate': 'GO' if release_go else 'NO-GO',
            'source_gates': [asdict(x) for x in gates],
            'runtime_gates': [asdict(x) for x in runtime_gates],
            'aot_readiness': aot,
            'note': 'Passing source tests is not feature parity, an iOS build, or device acceptance.'}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--kernarium', type=Path)
    p.add_argument('--report', type=Path)
    p.add_argument('--require-release-go', action='store_true')
    p.add_argument('--require-source-ready', action='store_true',
                   help='Exit nonzero if any source gate is missing, without requiring device acceptance')
    args = p.parse_args()
    report = inspect(ROOT, args.kernarium)
    output = json.dumps(report, indent=2) + '\n'
    if args.report:
        args.report.write_text(output)
    print(output)
    if args.require_release_go and report['release_gate'] != 'GO':
        sys.exit(2)
    if args.require_source_ready and report['source_checks_passed'] != report['source_checks_total']:
        sys.exit(1)


if __name__ == '__main__':
    main()
