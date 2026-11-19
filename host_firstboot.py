#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Stage verified ordinary APKs inside Andarium's iOS host for ADB first-boot installation.

This is an optional FAST PATH for Magisk manager and Titanium browser that
avoids rebuilding the Android 17 ROM. It DOES NOT make the guest rootable.
The clipboard provider needs platform signing and thus still needs a rebuilt guest.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import shutil
import zipfile
import re
from pathlib import Path
from install_source_overlay import validate_apk, validate_titanium

LIVE_MARKER = '    // MARK: Android operations'
BOOT_MARKER = '            partialSweep?.guestBooted()'
METHOD_SIGNATURE = '    private func redInstallBundledAppsAfterBoot() async {'
APPMANAGER_RELEASE_URL = 'https://github.com/MuntashirAkon/AppManager/releases/download/v4.1.1/AppManager_v4.1.1.apk'
APPMANAGER_RELEASE_SIZE = 28270163
APPMANAGER_RELEASE_SHA256 = '2540d6d9352acd8b04d6210140630a380abb1bc46ad4745c89ad97603dee3c40'
TERMUX_RELEASE_URL = 'https://github.com/termux/termux-app/releases/download/v0.118.3/termux-app_v0.118.3%2Bgithub-debug_arm64-v8a.apk'
TERMUX_RELEASE_SIZE = 35106607
TERMUX_RELEASE_SHA256 = '72fdb596045116bf5ba1b5bdf5b26fddb9acc0bd074ad9f2da9eb0ae85e83a4e'
# F-Droid 2.0.1 (full client) is not the latest v2.0.3, but has a
# known file fingerprint from the signed publisher build. Never swap a newer
# APK into this filename without updating BOTH pins.
FDROID_RELEASE_URL = 'https://f-droid.org/repo/org.fdroid.fdroid_2000051.apk'
FDROID_RELEASE_SIZE = 12537183
FDROID_RELEASE_SHA256 = '83d3fe522281c3cb89fce3bc05038f81b3c3b32c108536941f184c5f9bb53778'


def validate_fdroid(path: Path) -> dict:
    if not path.is_file() or path.stat().st_size != FDROID_RELEASE_SIZE:
        raise ValueError('F-Droid APK size does not match pinned signed release')
    h = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            h.update(chunk)
    if h.hexdigest() != FDROID_RELEASE_SHA256:
        raise ValueError('F-Droid APK SHA-256 does not match pinned signed release')
    with zipfile.ZipFile(path) as z:
        if 'AndroidManifest.xml' not in z.namelist() or z.testzip() is not None:
            raise ValueError('Invalid F-Droid APK archive')
    return {'file': path.name, 'bytes': path.stat().st_size, 'sha256': h.hexdigest(),
            'release': FDROID_RELEASE_URL, 'note': 'Pin is for 2.0.1, not the latest 2.0.3'}



def validate_termux(path: Path) -> dict:
    if not path.is_file() or path.stat().st_size != TERMUX_RELEASE_SIZE:
        raise ValueError('Termux APK size does not match pinned release')
    h = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            h.update(chunk)
    if h.hexdigest() != TERMUX_RELEASE_SHA256:
        raise ValueError('Termux APK SHA-256 does not match verified release checksum')
    with zipfile.ZipFile(path) as z:
        if 'AndroidManifest.xml' not in z.namelist() or z.testzip() is not None:
            raise ValueError('Invalid Termux APK archive')
    return {'file': path.name, 'bytes': path.stat().st_size, 'sha256': h.hexdigest(),
            'release': TERMUX_RELEASE_URL}



def validate_appmanager(path: Path) -> dict:
    if not path.is_file() or path.stat().st_size != APPMANAGER_RELEASE_SIZE:
        raise ValueError('App Manager APK size does not match the verified official release')
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    if digest.hexdigest() != APPMANAGER_RELEASE_SHA256:
        raise ValueError('App Manager APK SHA-256 does not match the verified official release')
    with zipfile.ZipFile(path) as archive:
        if 'AndroidManifest.xml' not in archive.namelist() or archive.testzip() is not None:
            raise ValueError('Invalid App Manager APK')
    return {'file': path.name, 'bytes': path.stat().st_size,
            'sha256': digest.hexdigest(), 'release': APPMANAGER_RELEASE_URL}


# HeliBoard normal release APK (not a debug APK); official GitHub asset digest.
HELIBOARD_RELEASE_URL = 'https://github.com/HeliBorg/HeliBoard/releases/download/v4.2/HeliBoard_4.2-release.apk'
HELIBOARD_RELEASE_SIZE = 22431797
HELIBOARD_RELEASE_SHA256 = '69b2b2fb349934371b1ed2d3569541cc0bda987f8aaf5eb5f5b157961f76de86'


def validate_heliboard(path: Path) -> dict:
    if not path.is_file() or path.stat().st_size != HELIBOARD_RELEASE_SIZE:
        raise ValueError('HeliBoard APK size does not match official v4.2 release')
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    if digest.hexdigest() != HELIBOARD_RELEASE_SHA256:
        raise ValueError('HeliBoard APK SHA-256 does not match official v4.2 release')
    with zipfile.ZipFile(path) as archive:
        if 'AndroidManifest.xml' not in archive.namelist() or archive.testzip() is not None:
            raise ValueError('Invalid HeliBoard APK archive')
    return {'file': path.name, 'bytes': path.stat().st_size,
            'sha256': digest.hexdigest(), 'release': HELIBOARD_RELEASE_URL}


PROJECT_ANCHOR = '    { "path": "../.build/andarium-system", "target-membership": [ "Andarium/resources" ] },'

# This body runs on LiveRuntime's main actor. Each install is done on Andarium's
# existing authenticated ADB transport, with memory-efficient APK streaming.
INSTALL_METHOD = '''    /// First-boot import of ordinary Android applications bundled with this iOS app.
    /// No global root or platform certificate is required to install regular APKs.
    /// Guest data may have been erased, so query Android rather than remembering a host flag.
    private var redInstallerActiveRun: GuestRunMark?
    private var redInstallerCompletedRun: GuestRunMark?

    private func redInstallBundledAppsAfterBoot() async {
        guard normalRun else { return }
        let startedRun = runMark
        // Console boot-complete can be observed more than once. Never run two
        // installers against one guest's package manager concurrently.
        guard redInstallerActiveRun != startedRun, redInstallerCompletedRun != startedRun else { return }
        redInstallerActiveRun = startedRun
        defer {
            if redInstallerActiveRun == startedRun { redInstallerActiveRun = nil }
        }
        // Android's data storage may take longer than sys.boot_completed to mount.
        var isReady = false
        for _ in 0..<50 {
            guard !Task.isCancelled, normalRun, runMark == startedRun else { return }
            if await operations.storageReady() == true { isReady = true; break }
            try? await Task.sleep(for: .seconds(2))
        }
        guard isReady, !Task.isCancelled, normalRun, runMark == startedRun else { return }
        for package in RedGuestApkInstaller.packages {
            guard !Task.isCancelled, normalRun, runMark == startedRun else { return }
            do {
                let existing = try await operations.shell("pm path " + package.androidPackage, limit: .seconds(10))
                if existing.exitCode == 0 && existing.text.hasPrefix("package:") { continue }
                // Missing official APKs are optional. A bad APK is never installed.
                guard RedGuestApkInstaller.bundledURL(for: package) != nil else {
                    print("Andarium Red: optional APK absent from bundle: " + package.filename)
                    continue
                }
                let url = try RedGuestApkInstaller.verifiedURL(for: package)
                _ = try await operations.installApk(at: url, update: { _ in })
                // Never mark a failed install successful. Inspect Android's actual package database.
                let installed = try await operations.shell("pm path " + package.androidPackage, limit: .seconds(10))
                if installed.exitCode != 0 || !installed.text.hasPrefix("package:") {
                    print("Andarium Red: guest rejected first-boot package " + package.androidPackage)
                }
            } catch {
                print("Andarium Red: optional first-boot package unavailable: " + error.localizedDescription)
            }
        }
        // The launcher is not in the stock system. After its first successful
        // guest installation, select it once; a later user choice is never reset.
        if !Task.isCancelled && normalRun && runMark == startedRun {
            do {
                let installed = try await operations.shell("pm path dev.twoyi.redlauncher", limit: .seconds(10))
                let flag = try await operations.shell(
                    "settings get secure dev.twoyi.redlauncher.home_provisioned", limit: .seconds(10))
                if installed.exitCode == 0 && installed.text.hasPrefix("package:") &&
                    flag.text.trimmingCharacters(in: .whitespacesAndNewlines) != "1" {
                    let selected = try await operations.shell(
                        "cmd package set-home-activity dev.twoyi.redlauncher/.MainActivity", limit: .seconds(15))
                    if selected.exitCode == 0 {
                        _ = try? await operations.shell(
                            "settings put secure dev.twoyi.redlauncher.home_provisioned 1", limit: .seconds(10))
                    }
                }
            } catch { print("Andarium Red: launcher selection unavailable: " + error.localizedDescription) }
        }
        // Boot has completed its one-time scan. A later guest restart or new
        // run gets a new run mark and can provision again after data reset.
        // Optional APKs absent from this immutable app bundle cannot appear
        // during the same run; avoid repeated filesystem/hash work.
        if normalRun && runMark == startedRun && !Task.isCancelled {
            redInstallerCompletedRun = startedRun
        }
    }

'''


# Exact v10 body, reconstructed from this version's template. A previously
# installed v10 patch must be safely upgraded rather than skipped. Any local
# edits by the repository owner fail closed instead of being overwritten.
def legacy_v10_install_method() -> str:
    previous = INSTALL_METHOD.replace(
        '    private var redInstallerActiveRun: GuestRunMark?\n    private var redInstallerCompletedRun: GuestRunMark?',
        '    private var redInstallerActiveRun: GuestRunMark?')
    previous = previous.replace(
        'guard redInstallerActiveRun != startedRun, redInstallerCompletedRun != startedRun else { return }',
        'guard redInstallerActiveRun != startedRun else { return }')
    extra = '''        // Boot has completed its one-time scan. A later guest restart or new
        // run gets a new run mark and can provision again after data reset.
        // Optional APKs absent from this immutable app bundle cannot appear
        // during the same run; avoid repeated filesystem/hash work.
        if normalRun && runMark == startedRun && !Task.isCancelled {
            redInstallerCompletedRun = startedRun
        }
'''
    return previous.replace(extra, '')


def patch_live_runtime(content: str) -> str:
    if METHOD_SIGNATURE in content:
        if 'private var redInstallerCompletedRun: GuestRunMark?' in content:
            return content
        marker = '    /// First-boot import of ordinary Android applications bundled with this iOS app.'
        if marker not in content or '    private var operations: AdbGuestOperations' not in content:
            raise ValueError('Existing Red installer source does not match reviewed host integration')
        start = content.index(marker)
        end = content.index('    private var operations: AdbGuestOperations', start)
        if content[start:end] != legacy_v10_install_method():
            raise ValueError('Existing Red installer has local changes; refusing an unsafe overwrite')
        return content[:start] + INSTALL_METHOD + content[end:]
    if LIVE_MARKER not in content or BOOT_MARKER not in content or 'private var operations: AdbGuestOperations' not in content:
        raise ValueError('LiveRuntime.swift does not match the reviewed Andarium v1 interface')
    content = content.replace(LIVE_MARKER, LIVE_MARKER + '\n\n' + INSTALL_METHOD, 1)
    hook = '            Task { [weak self] in await self?.redInstallBundledAppsAfterBoot() }'
    # The older ROM overlay selects HOME at boot-complete, which races an APK
    # installed only afterwards. Replace that hook with the install-then-select
    # sequence so there is exactly one owner of launcher provisioning.
    legacy_hook = '            Task { [weak self] in await self?.redProvisionHomeOnce() }'
    content = content.replace(legacy_hook, '', 1)
    content = content.replace(BOOT_MARKER, BOOT_MARKER + '\n' + hook, 1)
    return content


# The user's bundled APK set may grow between source updates. Keep names
# fixed and revalidate every existing APK; never silently trust old bytes.
BUNDLE_ORDER = (
    'TwoyiRedLauncher.apk', 'Magisk-v31.1.apk', 'Titanium-v157.apk',
    'AppManager-v4.1.1.apk', 'Termux-v0.118.3-arm64.apk',
    'FDroid-v2.0.1.apk', 'HeliBoard-v4.2-release.apk',
)


def validate_existing(name: str, path: Path) -> dict:
    validators = {
        'TwoyiRedLauncher.apk': verify_launcher,
        'Magisk-v31.1.apk': validate_apk,
        'Titanium-v157.apk': validate_titanium,
        'AppManager-v4.1.1.apk': validate_appmanager,
        'Termux-v0.118.3-arm64.apk': validate_termux,
        'FDroid-v2.0.1.apk': validate_fdroid,
        'HeliBoard-v4.2-release.apk': validate_heliboard,
    }
    if name not in validators:
        raise ValueError(f'Unknown existing APK resource: {name}')
    if not path.is_file() or path.is_symlink():
        raise ValueError(f'Existing APK resource is missing or is a symlink: {name}')
    return validators[name](path)


PROJECT_GROUP_RE = re.compile(
    r'    \{ "kind": "group", "name": "Red Bundled APKs", '
    r'"path": "Andarium/RedBundledAPKs", "children": \[\n'
    r'(?P<children>.*?)\n    \] \},', re.S,
)
PROJECT_PATH_RE = re.compile(r'\{ "path": "([^"\n]+)", "target-membership": '
                             r'\[ "Andarium/resources" \] \}')



CUSTOM_LAUNCHER_MARKER = '        // RED_CUSTOM_PACKAGES'
CUSTOM_LAUNCHER_ENTRY = re.compile(
    r'^[ \t]*Package\(filename:\s*"TwoyiRedLauncher\.apk",\s*'
    r'androidPackage:\s*"dev\.twoyi\.redlauncher",\s*'
    r'expectedBytes:\s*[0-9_]+,\s*expectedSHA256:\s*"[0-9a-f]{64}"\),?[ \t]*
    if PROJECT_ANCHOR not in original:
        raise ValueError('Andarium Xcode JSON project resource anchor changed')
    if len(packages) != len(set(packages)) or any(name not in BUNDLE_ORDER for name in packages):
        raise ValueError('Duplicate or unknown bundled APK resource requested')
    packages = [name for name in BUNDLE_ORDER if name in packages]
    children = ',\n'.join(
        f'      {{ "path": "{name}", "target-membership": [ "Andarium/resources" ] }}'
        for name in packages)
    group = ('    { "kind": "group", "name": "Red Bundled APKs", '
             '"path": "Andarium/RedBundledAPKs", "children": [\n'
             + children + '\n    ] },')
    existing = PROJECT_GROUP_RE.search(original)
    if existing:
        raw_children = existing.group('children')
        entries = PROJECT_PATH_RE.findall(raw_children)
        # Refuse unrecognized JSON5 elements or a duplicate resource entry.
        residue = PROJECT_PATH_RE.sub('', raw_children).replace(',', '').strip()
        if residue or len(entries) != len(set(entries)) or any(x not in BUNDLE_ORDER for x in entries):
            raise ValueError('Existing Red APK group has unexpected or duplicate resources')
        if not set(entries).issubset(packages):
            raise ValueError('Existing Red APK group contains resources missing from staged bundle')
        return original[:existing.start()] + group + original[existing.end():]
    if '"name": "Red Bundled APKs"' in original:
        raise ValueError('Existing Red APK resource group has an unexpected structure')
    return original.replace(PROJECT_ANCHOR, PROJECT_ANCHOR + '\n' + group, 1)


def verify_launcher(apk: Path) -> dict:
    if not apk.is_file():
        raise ValueError(f'Launcher APK missing: {apk}')
    with zipfile.ZipFile(apk) as z:
        names = z.namelist()
        if 'AndroidManifest.xml' not in names or 'classes.dex' not in names:
            raise ValueError('Launcher must be a compiled APK with a manifest and DEX classes')
        if z.testzip() is not None:
            raise ValueError('Launcher APK ZIP integrity check failed')
    # A ZIP with dummy entries is not a compiled Android app. Validate the
    # minimum structure of AAPT's binary manifest and a real DEX header;
    # signing and package identity are checked by Android at install time.
    with zipfile.ZipFile(apk) as z:
        manifest = z.read('AndroidManifest.xml')
        dex = z.read('classes.dex')
    if not manifest.startswith(b'\x03\x00\x08\x00') or len(manifest) < 8:
        raise ValueError('Launcher must contain a compiled binary AndroidManifest.xml')
    if (len(dex) < 112 or dex[:4] != b'dex\n' or dex[4:7] not in
            (b'035', b'037', b'038', b'039', b'040', b'041') or dex[7] != 0 or
            int.from_bytes(dex[32:36], 'little') != len(dex) or
            int.from_bytes(dex[36:40], 'little') != 112 or
            int.from_bytes(dex[40:44], 'little') != 0x12345678):
        raise ValueError('Launcher must contain a compiled Android DEX image')
    hasher = hashlib.sha256()
    with apk.open('rb') as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b''):
            hasher.update(chunk)
    digest = hasher.hexdigest()
    return {'file': apk.name, 'bytes': apk.stat().st_size, 'sha256': digest,
            'note': 'Launcher must be built from our checked Android 17 source; APK package identity needs device verification'}


def stage(root: Path, source_dir: Path, magisk: Path | None, titanium: Path | None,
          dry_run: bool = False, launcher: Path | None = None,
          appmanager: Path | None = None, termux: Path | None = None,
          fdroid: Path | None = None, heliboard: Path | None = None) -> dict:
    live = root / 'Andarium/Andarium/Live/LiveRuntime.swift'
    project = root / 'Andarium/Andarium.xcodeproj/project.xcproj'
    if not live.is_file() or not project.is_file():
        raise ValueError('Not a matching Andarium iOS source checkout')
    swift_path = source_dir / 'host/RedGuestApkInstaller.swift'
    if not swift_path.is_file():
        raise ValueError('Missing streaming hash implementation')
    inputs = []
    if launcher:
        meta = verify_launcher(launcher)
        inputs.append(('TwoyiRedLauncher.apk', launcher, meta))
    if magisk:
        meta = validate_apk(magisk)
        inputs.append(('Magisk-v31.1.apk', magisk, meta))
    if titanium:
        meta = validate_titanium(titanium)
        inputs.append(('Titanium-v157.apk', titanium, meta))
    if appmanager:
        meta = validate_appmanager(appmanager)
        inputs.append(('AppManager-v4.1.1.apk', appmanager, meta))
    if termux:
        meta = validate_termux(termux)
        inputs.append(('Termux-v0.118.3-arm64.apk', termux, meta))
    if fdroid:
        meta = validate_fdroid(fdroid)
        inputs.append(('FDroid-v2.0.1.apk', fdroid, meta))
    if heliboard:
        meta = validate_heliboard(heliboard)
        inputs.append(('HeliBoard-v4.2-release.apk', heliboard, meta))
    target = root / 'Andarium/RedBundledAPKs'
    input_by_name = {name: (path, meta) for name, path, meta in inputs}
    existing_files: dict[str, Path] = {}
    if target.exists():
        if target.is_symlink() or not target.is_dir():
            raise ValueError('Existing Red APK bundle is not a real directory')
        for path in target.iterdir():
            if path.name not in BUNDLE_ORDER:
                raise ValueError('Existing Red APK bundle contains unknown resource: ' + path.name)
            validate_existing(path.name, path)
            existing_files[path.name] = path
    if not inputs and not existing_files:
        raise ValueError('Supply at least one officially verified APK; do not include placeholders')
    # An add-on update keeps all existing pinned assets; conflicting input is
    # rejected even when its checksum was valid for a different version.
    for name, (input_path, _) in input_by_name.items():
        if name in existing_files:
            def digest(path: Path) -> str:
                h = hashlib.sha256()
                with path.open('rb') as stream:
                    for chunk in iter(lambda: stream.read(1 << 20), b''):
                        h.update(chunk)
                return h.hexdigest()
            if digest(input_path) != digest(existing_files[name]):
                raise ValueError('Existing bundled APK differs from requested file: ' + name)
    merged_names = [name for name in BUNDLE_ORDER if name in input_by_name or name in existing_files]
    runtime_patched = patch_live_runtime(live.read_text())
    project_patched = patch_project(project.read_text(), merged_names)
    swift_text = swift_path.read_text()
    # Preserve the installed custom HOME package across incremental updates.
    launcher_source = input_by_name.get('TwoyiRedLauncher.apk', (None,))[0] or existing_files.get('TwoyiRedLauncher.apk')
    if launcher_source:
        meta = verify_launcher(launcher_source)
        swift_text = pin_launcher_in_swift(swift_text, meta)
    report = {'changes_applied': not dry_run, 'host_firstboot': True,
              'guest_android': 17, 'guest_root_enabled': False,
              'image_rebuild_needed_for_regular_apks': False,
              'image_rebuild_needed_for_clipboard_privilege': True,
              'input_apks': {name: meta for name, _, meta in inputs},
              'preserved_existing_apks': sorted(set(existing_files) - set(input_by_name)),
              'bundled_apks_after_update': merged_names}
    if dry_run:
        return report
    target.mkdir(parents=True, exist_ok=True)
    for name, source, _ in inputs:
        dest = target / name
        if dest.resolve() != source.resolve() and name not in existing_files:
            shutil.copy2(source, dest)
    (live.parent / swift_path.name).write_text(swift_text)
    live.write_text(runtime_patched)
    project.write_text(project_patched)
    return report


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--kernarium', required=True, type=Path)
    p.add_argument('--magisk-apk', type=Path)
    p.add_argument('--titanium-apk', type=Path)
    p.add_argument('--launcher-apk', type=Path, help='A real, compiled Android red launcher APK')
    p.add_argument('--appmanager-apk', type=Path, help='Verified official App Manager v4.1.1 APK')
    p.add_argument('--termux-apk', type=Path, help='Checksum-pinned Termux v0.118.3 ARM64 APK')
    p.add_argument('--fdroid-apk', type=Path, help='Checksum-pinned full F-Droid v2.0.1 APK')
    p.add_argument('--heliboard-apk', type=Path, help='Official HeliBoard v4.2 release APK')
    p.add_argument('--dry-run', action='store_true')
    a = p.parse_args()
    print(json.dumps(stage(a.kernarium.resolve(), Path(__file__).resolve().parent,
                           a.magisk_apk.resolve() if a.magisk_apk else None,
                           a.titanium_apk.resolve() if a.titanium_apk else None,
                           a.dry_run,
                           a.launcher_apk.resolve() if a.launcher_apk else None,
                           a.appmanager_apk.resolve() if a.appmanager_apk else None,
                           a.termux_apk.resolve() if a.termux_apk else None,
                           a.fdroid_apk.resolve() if a.fdroid_apk else None,
                           a.heliboard_apk.resolve() if a.heliboard_apk else None), indent=2))


if __name__ == '__main__':
    main()
,
    re.MULTILINE,
)


def pin_launcher_in_swift(original: str, metadata: dict) -> str:
    """Repeatable byte/hash pin update without deleting the marker.

    An older already-patched source may have lost the marker; accept only one
    exact known launcher entry in that case and restore the marker. Unknown or
    duplicated entries fail closed rather than installing a guessed package.
    """
    custom = (
        '        Package(filename: "TwoyiRedLauncher.apk", '
        'androidPackage: "dev.twoyi.redlauncher",\n'
        f'                expectedBytes: {metadata["bytes"]}, '
        f'expectedSHA256: "{metadata["sha256"]}"),'
    )
    entries = list(CUSTOM_LAUNCHER_ENTRY.finditer(original))
    if len(entries) > 1 or original.count(CUSTOM_LAUNCHER_MARKER) > 1:
        raise ValueError('Duplicate launcher pin or custom package marker')
    if entries:
        match = entries[0]
        original = original[:match.start()] + custom + original[match.end():]
        if CUSTOM_LAUNCHER_MARKER not in original:
            original = original.replace(custom, custom + '\n' + CUSTOM_LAUNCHER_MARKER, 1)
        return original
    if CUSTOM_LAUNCHER_MARKER not in original:
        raise ValueError('Cannot pin launcher: no known entry or custom package marker')
    return original.replace(
        CUSTOM_LAUNCHER_MARKER,
        custom + '\n' + CUSTOM_LAUNCHER_MARKER,
        1,
    )


def patch_project(original: str, packages: list[str]) -> str:
    if PROJECT_ANCHOR not in original:
        raise ValueError('Andarium Xcode JSON project resource anchor changed')
    if len(packages) != len(set(packages)) or any(name not in BUNDLE_ORDER for name in packages):
        raise ValueError('Duplicate or unknown bundled APK resource requested')
    packages = [name for name in BUNDLE_ORDER if name in packages]
    children = ',\n'.join(
        f'      {{ "path": "{name}", "target-membership": [ "Andarium/resources" ] }}'
        for name in packages)
    group = ('    { "kind": "group", "name": "Red Bundled APKs", '
             '"path": "Andarium/RedBundledAPKs", "children": [\n'
             + children + '\n    ] },')
    existing = PROJECT_GROUP_RE.search(original)
    if existing:
        raw_children = existing.group('children')
        entries = PROJECT_PATH_RE.findall(raw_children)
        # Refuse unrecognized JSON5 elements or a duplicate resource entry.
        residue = PROJECT_PATH_RE.sub('', raw_children).replace(',', '').strip()
        if residue or len(entries) != len(set(entries)) or any(x not in BUNDLE_ORDER for x in entries):
            raise ValueError('Existing Red APK group has unexpected or duplicate resources')
        if not set(entries).issubset(packages):
            raise ValueError('Existing Red APK group contains resources missing from staged bundle')
        return original[:existing.start()] + group + original[existing.end():]
    if '"name": "Red Bundled APKs"' in original:
        raise ValueError('Existing Red APK resource group has an unexpected structure')
    return original.replace(PROJECT_ANCHOR, PROJECT_ANCHOR + '\n' + group, 1)


def verify_launcher(apk: Path) -> dict:
    if not apk.is_file():
        raise ValueError(f'Launcher APK missing: {apk}')
    with zipfile.ZipFile(apk) as z:
        names = z.namelist()
        if 'AndroidManifest.xml' not in names or 'classes.dex' not in names:
            raise ValueError('Launcher must be a compiled APK with a manifest and DEX classes')
        if z.testzip() is not None:
            raise ValueError('Launcher APK ZIP integrity check failed')
    # A ZIP with dummy entries is not a compiled Android app. Validate the
    # minimum structure of AAPT's binary manifest and a real DEX header;
    # signing and package identity are checked by Android at install time.
    with zipfile.ZipFile(apk) as z:
        manifest = z.read('AndroidManifest.xml')
        dex = z.read('classes.dex')
    if not manifest.startswith(b'\x03\x00\x08\x00') or len(manifest) < 8:
        raise ValueError('Launcher must contain a compiled binary AndroidManifest.xml')
    if (len(dex) < 112 or dex[:4] != b'dex\n' or dex[4:7] not in
            (b'035', b'037', b'038', b'039', b'040', b'041') or dex[7] != 0 or
            int.from_bytes(dex[32:36], 'little') != len(dex) or
            int.from_bytes(dex[36:40], 'little') != 112 or
            int.from_bytes(dex[40:44], 'little') != 0x12345678):
        raise ValueError('Launcher must contain a compiled Android DEX image')
    hasher = hashlib.sha256()
    with apk.open('rb') as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b''):
            hasher.update(chunk)
    digest = hasher.hexdigest()
    return {'file': apk.name, 'bytes': apk.stat().st_size, 'sha256': digest,
            'note': 'Launcher must be built from our checked Android 17 source; APK package identity needs device verification'}


def stage(root: Path, source_dir: Path, magisk: Path | None, titanium: Path | None,
          dry_run: bool = False, launcher: Path | None = None,
          appmanager: Path | None = None, termux: Path | None = None,
          fdroid: Path | None = None, heliboard: Path | None = None) -> dict:
    live = root / 'Andarium/Andarium/Live/LiveRuntime.swift'
    project = root / 'Andarium/Andarium.xcodeproj/project.xcproj'
    if not live.is_file() or not project.is_file():
        raise ValueError('Not a matching Andarium iOS source checkout')
    swift_path = source_dir / 'host/RedGuestApkInstaller.swift'
    if not swift_path.is_file():
        raise ValueError('Missing streaming hash implementation')
    inputs = []
    if launcher:
        meta = verify_launcher(launcher)
        inputs.append(('TwoyiRedLauncher.apk', launcher, meta))
    if magisk:
        meta = validate_apk(magisk)
        inputs.append(('Magisk-v31.1.apk', magisk, meta))
    if titanium:
        meta = validate_titanium(titanium)
        inputs.append(('Titanium-v157.apk', titanium, meta))
    if appmanager:
        meta = validate_appmanager(appmanager)
        inputs.append(('AppManager-v4.1.1.apk', appmanager, meta))
    if termux:
        meta = validate_termux(termux)
        inputs.append(('Termux-v0.118.3-arm64.apk', termux, meta))
    if fdroid:
        meta = validate_fdroid(fdroid)
        inputs.append(('FDroid-v2.0.1.apk', fdroid, meta))
    if heliboard:
        meta = validate_heliboard(heliboard)
        inputs.append(('HeliBoard-v4.2-release.apk', heliboard, meta))
    target = root / 'Andarium/RedBundledAPKs'
    input_by_name = {name: (path, meta) for name, path, meta in inputs}
    existing_files: dict[str, Path] = {}
    if target.exists():
        if target.is_symlink() or not target.is_dir():
            raise ValueError('Existing Red APK bundle is not a real directory')
        for path in target.iterdir():
            if path.name not in BUNDLE_ORDER:
                raise ValueError('Existing Red APK bundle contains unknown resource: ' + path.name)
            validate_existing(path.name, path)
            existing_files[path.name] = path
    if not inputs and not existing_files:
        raise ValueError('Supply at least one officially verified APK; do not include placeholders')
    # An add-on update keeps all existing pinned assets; conflicting input is
    # rejected even when its checksum was valid for a different version.
    for name, (input_path, _) in input_by_name.items():
        if name in existing_files:
            def digest(path: Path) -> str:
                h = hashlib.sha256()
                with path.open('rb') as stream:
                    for chunk in iter(lambda: stream.read(1 << 20), b''):
                        h.update(chunk)
                return h.hexdigest()
            if digest(input_path) != digest(existing_files[name]):
                raise ValueError('Existing bundled APK differs from requested file: ' + name)
    merged_names = [name for name in BUNDLE_ORDER if name in input_by_name or name in existing_files]
    runtime_patched = patch_live_runtime(live.read_text())
    project_patched = patch_project(project.read_text(), merged_names)
    swift_text = swift_path.read_text()
    # Preserve the installed custom HOME package across incremental updates.
    launcher_source = input_by_name.get('TwoyiRedLauncher.apk', (None,))[0] or existing_files.get('TwoyiRedLauncher.apk')
    if launcher_source:
        meta = verify_launcher(launcher_source)
        marker = '        // RED_CUSTOM_PACKAGES'
        if marker not in swift_text:
            raise ValueError('Cannot pin launcher in host Swift installer: marker absent')
        custom = (f'        Package(filename: "TwoyiRedLauncher.apk", androidPackage: "dev.twoyi.redlauncher",\n'
                  f'                expectedBytes: {meta["bytes"]}, expectedSHA256: "{meta["sha256"]}"),')
        swift_text = swift_text.replace(marker, custom, 1)
    report = {'changes_applied': not dry_run, 'host_firstboot': True,
              'guest_android': 17, 'guest_root_enabled': False,
              'image_rebuild_needed_for_regular_apks': False,
              'image_rebuild_needed_for_clipboard_privilege': True,
              'input_apks': {name: meta for name, _, meta in inputs},
              'preserved_existing_apks': sorted(set(existing_files) - set(input_by_name)),
              'bundled_apks_after_update': merged_names}
    if dry_run:
        return report
    target.mkdir(parents=True, exist_ok=True)
    for name, source, _ in inputs:
        dest = target / name
        if dest.resolve() != source.resolve() and name not in existing_files:
            shutil.copy2(source, dest)
    (live.parent / swift_path.name).write_text(swift_text)
    live.write_text(runtime_patched)
    project.write_text(project_patched)
    return report


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--kernarium', required=True, type=Path)
    p.add_argument('--magisk-apk', type=Path)
    p.add_argument('--titanium-apk', type=Path)
    p.add_argument('--launcher-apk', type=Path, help='A real, compiled Android red launcher APK')
    p.add_argument('--appmanager-apk', type=Path, help='Verified official App Manager v4.1.1 APK')
    p.add_argument('--termux-apk', type=Path, help='Checksum-pinned Termux v0.118.3 ARM64 APK')
    p.add_argument('--fdroid-apk', type=Path, help='Checksum-pinned full F-Droid v2.0.1 APK')
    p.add_argument('--heliboard-apk', type=Path, help='Official HeliBoard v4.2 release APK')
    p.add_argument('--dry-run', action='store_true')
    a = p.parse_args()
    print(json.dumps(stage(a.kernarium.resolve(), Path(__file__).resolve().parent,
                           a.magisk_apk.resolve() if a.magisk_apk else None,
                           a.titanium_apk.resolve() if a.titanium_apk else None,
                           a.dry_run,
                           a.launcher_apk.resolve() if a.launcher_apk else None,
                           a.appmanager_apk.resolve() if a.appmanager_apk else None,
                           a.termux_apk.resolve() if a.termux_apk else None,
                           a.fdroid_apk.resolve() if a.fdroid_apk else None,
                           a.heliboard_apk.resolve() if a.heliboard_apk else None), indent=2))


if __name__ == '__main__':
    main()
