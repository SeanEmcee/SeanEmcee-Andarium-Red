#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Stage the Twoyi Red launcher source in a checked-out Kernarium Android 17 guest tree.

This intentionally does NOT replace the iOS NEO executable or claim that the
result has been booted. Kernarium's own accepted-artifact workflows must run
before an IPA can carry the modified guest.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

APP_MODULE = 'TwoyiRedLauncher'
MAGISK_MODULE = 'TwoyiRedMagiskManager'
CLIPBOARD_MODULE = 'TwoyiRedClipboard'
TITANIUM_MODULE = 'TwoyiRedTitaniumBrowser'
TITANIUM_RELEASE_URL = 'https://github.com/jqssun/android-titanium-browser/releases/download/v157.0.8103.78/157.0.8103.78-1794501360-arm64-v8a.apk'
TITANIUM_RELEASE_SIZE = 335631810
TITANIUM_RELEASE_SHA256 = 'c65ef275124058617b2cf0dcc3989b143e74b32ca5a43d9279a0edece8fe7051'
# Official Magisk v31.1 release asset digest from GitHub's releases API.
MAGISK_RELEASE_URL = 'https://github.com/topjohnwu/Magisk/releases/download/v31.1/Magisk-v31.1.apk'
MAGISK_RELEASE_SIZE = 10679283
MAGISK_RELEASE_SHA256 = '89cefac0a318afa39fb3880c45c87b036c05bc1ebf02a7a715b7f8d7c26ac6e7'


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def required_tree(root: Path) -> tuple[Path, Path]:
    cfg = root / 'android/lineage-24/overlay/lineage_andarium.mk'
    lineage = root / 'android/lineage-24/metadata/lineage.env'
    app = root / 'Andarium/Andarium/Shared/AndariumApp.swift'
    if not cfg.is_file() or not lineage.is_file() or not app.is_file():
        raise ValueError('Not a Kernarium checkout with LineageOS 24 and Andarium source')
    source = lineage.read_text()
    if "LINEAGE24_ANDROID_MAJOR=17" not in source:
        raise ValueError('Guest is not pinned to Android 17')
    return cfg, root / 'android/lineage-24/overlay/twoyi-red'


def patch_makefile(text: str, modules: list[str]) -> str:
    mark = '# Twoyi Red optional guest applications (source-controlled overlay).'
    for mod in modules:
        if re.search(r'^PRODUCT_PACKAGES\s*\+=\s*' + re.escape(mod) + r'\s*$', text, re.M):
            continue
        item = f'{mark}\nPRODUCT_PACKAGES += {mod}\n'
        anchor = 'PRODUCT_NAME := lineage_andarium'
        if anchor not in text:
            raise ValueError(f'Cannot locate {anchor} for a safe product patch')
        text = text.replace(anchor, item + '\n' + anchor, 1)
    return text


def launcher_manifest(source: bytes) -> bytes:
    source_text = source.decode('utf-8')
    if 'package="dev.twoyi.redlauncher"' not in source_text:
        source_text = source_text.replace('<manifest xmlns:android=',
            '<manifest package="dev.twoyi.redlauncher" xmlns:android=', 1)
    if 'package="dev.twoyi.redlauncher"' not in source_text:
        raise ValueError('Could not set Android manifest package')
    return source_text.encode('utf-8')


LAUNCHER_BP = '''// SPDX-License-Identifier: Apache-2.0
// Android 17 guest HOME app; not the iOS host app.
android_app {
    name: "TwoyiRedLauncher",
    srcs: ["java/**/*.java"],
    asset_dirs: ["assets"],
    manifest: "AndroidManifest.xml",
    sdk_version: "current",
    min_sdk_version: "33",
    certificate: "platform",
    product_specific: true,
    optimize: { enabled: false },
}
'''

MAGISK_BP = '''// SPDX-License-Identifier: Apache-2.0
// Installs the unmodified, separately verified manager APK only.
// Does NOT provide an su binary or root privilege.
android_app_import {
    name: "TwoyiRedMagiskManager",
    apk: "Magisk.apk",
    presigned: true,
    preprocessed: true,
    product_specific: true,
    dex_preopt: { enabled: false },
}
'''


def validate_apk(path: Path) -> dict:
    if not path.is_file():
        raise ValueError(f'APK not found: {path}')
    data = path.read_bytes()
    digest = sha256(data)
    if len(data) != MAGISK_RELEASE_SIZE or digest != MAGISK_RELEASE_SHA256:
        raise ValueError('Magisk APK fails official v31.1 size/SHA-256 verification')
    with zipfile.ZipFile(path) as z:
        if z.testzip() is not None:
            raise ValueError('Invalid APK ZIP entry')
        if 'AndroidManifest.xml' not in z.namelist():
            raise ValueError('Missing AndroidManifest.xml')
    return {'file': path.name, 'bytes': len(data), 'sha256': digest,
            'release': MAGISK_RELEASE_URL,
            'note': 'Exact official v31.1 release asset verified; Android guest rootability NOT verified'}


def configure_build_variant(lineage_text: str, variant: str) -> str:
    """Select an explicit diagnostic variant; do not silently change release policy."""
    if variant not in ('keep', 'userdebug'):
        raise ValueError('Only keep or userdebug are valid; diagnostic build is not a release')
    if variant == 'keep':
        return lineage_text
    marker = "LINEAGE24_BUILD_VARIANT='user'"
    if marker not in lineage_text and "LINEAGE24_BUILD_VARIANT='userdebug'" not in lineage_text:
        raise ValueError('Cannot locate the pinned LineageOS build variant')
    return lineage_text.replace(marker, "LINEAGE24_BUILD_VARIANT='userdebug'")


TITANIUM_BP = '''// SPDX-License-Identifier: Apache-2.0
android_app_import {
    name: "TwoyiRedTitaniumBrowser",
    apk: "Titanium.apk",
    presigned: true,
    preprocessed: true,
    product_specific: true,
    dex_preopt: { enabled: false },
}
'''


def validate_titanium(path: Path) -> dict:
    if not path.is_file() or path.stat().st_size != TITANIUM_RELEASE_SIZE:
        raise ValueError('Titanium APK size does not match verified release')
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    if h.hexdigest() != TITANIUM_RELEASE_SHA256:
        raise ValueError('Titanium APK SHA-256 does not match verified official release')
    with zipfile.ZipFile(path) as z:
        if 'AndroidManifest.xml' not in z.namelist():
            raise ValueError('Titanium APK is missing its manifest')
    return {'file': path.name, 'bytes': path.stat().st_size, 'sha256': h.hexdigest(),
            'release': TITANIUM_RELEASE_URL}


def patch_host_runtime(original: str) -> str:
    marker = '    // MARK: Android operations'
    signature = '    func redClipboardShell(_ command: String) async throws -> String {'
    if signature in original:
        return original
    if marker not in original or 'private var operations: AdbGuestOperations' not in original:
        raise ValueError('Upstream LiveRuntime.swift Android operations interface changed')
    addition = '''    /// Explicit, user-triggered clipboard transfer over existing authenticated guest ADB.
    func redClipboardShell(_ command: String) async throws -> String {
        let output = try await operations.shell(command, limit: .seconds(15))
        guard output.exitCode == 0 else {
            throw RedClipboardCodec.BridgeError.guestRejected("guest shell returned an error")
        }
        return output.text
    }

'''
    patched = original.replace(marker, marker + '\n\n' + addition, 1)
    # The first completed Android boot provisions the new HOME activity once;
    # the user may change HOME afterwards without us overriding that choice.
    provision_marker = '            partialSweep?.guestBooted()'
    if provision_marker not in patched:
        raise ValueError('Upstream Android boot completion hook changed')
    patched = patched.replace(provision_marker,
        provision_marker + '\n            Task { [weak self] in await self?.redProvisionHomeOnce() }', 1)
    provision_method = '''    /// Select the installed Twoyi Red launcher only once per guest data disk.
    /// Preserve the user's subsequent default-HOME choice across restarts.
    private func redProvisionHomeOnce() async {
        guard normalRun else { return }
        do {
            let flag = try await operations.shell(
                "settings get secure dev.twoyi.redlauncher.home_provisioned", limit: .seconds(10))
            if flag.text.trimmingCharacters(in: .whitespacesAndNewlines) == "1" { return }
            let response = try await operations.shell(
                "cmd package set-home-activity dev.twoyi.redlauncher/.MainActivity", limit: .seconds(15))
            guard response.exitCode == 0 else { return }
            _ = try? await operations.shell(
                "settings put secure dev.twoyi.redlauncher.home_provisioned 1", limit: .seconds(10))
            // Choose Titanium only if no browser is already the default.
            let browser = try? await operations.shell("pm path io.github.jqssun.helium", limit: .seconds(10))
            if browser?.text.contains("package:") == true {
                let existing = try? await operations.shell(
                    "cmd role get-role-holders --user 0 android.app.role.BROWSER", limit: .seconds(10))
                let holders = existing?.text.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
                if holders.isEmpty || holders == "[]" {
                    _ = try? await operations.shell(
                        "cmd role add-role-holder --user 0 android.app.role.BROWSER io.github.jqssun.helium",
                        limit: .seconds(15))
                }
            }
        } catch {
            // Do not block Android's boot on optional launcher customization.
        }
    }

'''
    return patched.replace(marker, marker + '\n\n' + provision_method, 1)


def patch_native_resolution_default(original: str) -> str:
    """Use the host screen's actual native scale for a fresh guest only.

    A user's explicit saved selection remains higher priority, including
    deliberate lower-resolution settings for performance/thermal headroom.
    """
    old = 'model.chosenScale = DisplayOptionsStore.load().chosenScale'
    new = 'model.chosenScale = DisplayOptionsStore.load().chosenScale ?? .native'
    if new in original:
        return original
    if old not in original:
        raise ValueError('Upstream AppEntry.swift resolution initializer changed')
    return original.replace(old, new, 1)


def aot_readiness(root: Path) -> dict:
    """Audit—not activate—the accepted AOT pipeline and its archived outputs.

    An AOT framework is never marked active based solely on a source checkout.
    Activation is confirmed only by archive and device runtime inspection.
    """
    aot_dir = root / 'tools/aot'
    required = [aot_dir / 'rewrite.py', aot_dir / 'release_artifact.py',
                aot_dir / 'libraries.txt', root / 'darwin/cpu/arm64/aot/CMakeLists.txt']
    missing = [str(path.relative_to(root)) for path in required if not path.is_file()]
    acceptance = root / 'android/lineage-24/metadata/accepted-aot.env'
    has_acceptance = acceptance.is_file()
    accepted_for_archives = False
    if has_acceptance:
        import re
        accepted_for_archives = bool(re.search(
            r"(?m)^LINEAGE24_ACCEPTED_AOT_ARCHIVES=['\"]?yes['\"]?\s*$",
            acceptance.read_text()))
    return {'toolchain_sources_present': not missing,
            'missing_sources': missing,
            'acceptance_descriptor_present': has_acceptance,
            'archives_approved_in_descriptor': accepted_for_archives,
            'compiled_native_aot_verified': False,
            'active_on_device_verified': False,
            'status': ('Needs AOT artifact acceptance and signed-device benchmark'
                       if not accepted_for_archives else
                       'Descriptor allows archives; verify compiled artifact and device runtime')}


def patch_session_view(original: str) -> str:
    signature = 'RedClipboardControls(runtime: runtime)'
    if signature in original:
        return original
    anchor = '''        content
            // The text message bar, over Android and above the keyboard.'''
    if anchor not in original:
        raise ValueError('Upstream SessionView.swift layout anchor changed')
    patch = '''        content
            .overlay(alignment: .topTrailing) {
                if mode == .normal { RedClipboardControls(runtime: runtime) }
            }
            // The text message bar, over Android and above the keyboard.'''
    return original.replace(anchor, patch, 1)


def plan_host(root: Path) -> dict:
    live = root / 'Andarium/Andarium/Live'
    runtime = live / 'LiveRuntime.swift'
    session = live / 'SessionView.swift'
    if not runtime.is_file() or not session.is_file():
        raise ValueError('Andarium host runtime source unavailable')
    return {runtime: patch_host_runtime(runtime.read_text()),
            session: patch_session_view(session.read_text())}


def apply(root: Path, source: Path, magisk_apk: Path | None, dry_run: bool,
          variant: str = 'keep', titanium_apk: Path | None = None,
          host_clipboard: bool = True) -> dict:
    cfg, dest = required_tree(root)
    lineage_path = root / 'android/lineage-24/metadata/lineage.env'
    lineage_original = lineage_path.read_text()
    lineage_modified = configure_build_variant(lineage_original, variant)
    if not source.is_dir():
        raise ValueError(f'Missing launcher source: {source}')
    manifest = source / 'AndroidManifest.xml'
    if not manifest.is_file():
        raise ValueError('Launcher manifest missing')
    for name in ('home.png','settings.png','browser.png'):
        if not (source / 'assets' / name).is_file():
            raise ValueError(f'Missing exact visual reference asset {name}')
    java = list((source / 'java').rglob('*.java'))
    if not java:
        raise ValueError('Launcher Java source missing')
    mods = [APP_MODULE]
    host_patch = plan_host(root) if host_clipboard else {}
    app_entry = root / 'Andarium/Andarium/Live/AppEntry.swift'
    if not app_entry.is_file():
        raise ValueError('Andarium AppEntry.swift is required for native resolution defaults')
    native_app_entry = patch_native_resolution_default(app_entry.read_text())
    aot_report = aot_readiness(root)
    if host_clipboard and not (Path(__file__).resolve().parent / 'guest_clipboard' / 'Android.bp').is_file():
        raise ValueError('Guest clipboard source is missing')
    if host_clipboard:
        mods.append(CLIPBOARD_MODULE)
    before = cfg.read_text()
    # Re-running a source-only update must not silently misreport or drop
    # an existing Magisk module in the checked-out guest device tree.
    existing_apk = dest / 'magisk' / 'Magisk.apk'
    if magisk_apk is None and MAGISK_MODULE in before:
        if not existing_apk.is_file():
            raise ValueError('Magisk is listed in product but its APK is missing')
        magisk_apk = existing_apk
    mreport = None
    if magisk_apk is not None:
        mreport = validate_apk(magisk_apk)
        mods.append(MAGISK_MODULE)
    t_report = None
    old_titanium = dest / 'titanium' / 'Titanium.apk'
    if titanium_apk is None and TITANIUM_MODULE in before:
        if not old_titanium.is_file():
            raise ValueError('Titanium is listed in product but its APK is missing')
        titanium_apk = old_titanium
    if titanium_apk is not None:
        t_report = validate_titanium(titanium_apk)
        mods.append(TITANIUM_MODULE)
    after = patch_makefile(before, mods)
    result = {'checked_root':str(root),'android':17,'changes_applied':not dry_run,
              'guest_modules':mods,'home_default_configured':False,
              'home_auto_provisioning_source_added':host_clipboard,
              'host_runtime_changed':False,'guest_root_enabled':False,
              'clipboard_bridge_source_staged':host_clipboard,
              'host_runtime_source_patched':host_clipboard,
              'clipboard_bridge_connected':False,
              'source_image_sha256': {name:sha256((source/'assets'/name).read_bytes())
                  for name in ('home.png','settings.png','browser.png')},
              'magisk_apk':mreport,
              'titanium_apk':t_report,
              'native_resolution_default': True,
              'existing_resolution_selection_preserved': True,
              'thermal_frame_rate_safeguard_preserved': True,
              'aot_readiness': aot_report,
              'build_variant': ('userdebug' if "LINEAGE24_BUILD_VARIANT='userdebug'" in lineage_modified else 'user'),
              'diagnostic_build_not_releasable': variant == 'userdebug',
              'notes':['HOME is automatically selected once after Android boot when the host integration is included; Android boot is not verified.',
                       'This is a new Android 17 guest build input; the accepted user image is unchanged until rebuilt, signed and restaged.',
                       'Magisk manager app alone does not grant root. Stock user build explicitly has no su.']}
    if dry_run:
        return result
    app_entry.write_text(native_app_entry)
    dest.mkdir(parents=True, exist_ok=True)
    ldir = dest / 'launcher'
    if ldir.exists():
        shutil.rmtree(ldir)
    shutil.copytree(source, ldir)
    (ldir/'AndroidManifest.xml').write_bytes(launcher_manifest(manifest.read_bytes()))
    (ldir/'Android.bp').write_text(LAUNCHER_BP)
    if mreport:
        mdir=dest/'magisk'
        mdir.mkdir(parents=True,exist_ok=True)
        if magisk_apk.resolve() != (mdir/'Magisk.apk').resolve():
            shutil.copy2(magisk_apk, mdir/'Magisk.apk')
        (mdir/'Android.bp').write_text(MAGISK_BP)
        (mdir/'source.json').write_text(json.dumps(mreport,indent=2)+'\n')
    if host_clipboard:
        clip_src = Path(__file__).resolve().parent / 'guest_clipboard'
        if not (clip_src / 'Android.bp').is_file():
            raise ValueError('Missing Android 17 guest clipboard implementation')
        clip_dest = dest / 'clipboard'
        if clip_dest.exists():
            shutil.rmtree(clip_dest)
        shutil.copytree(clip_src, clip_dest)
        for target, content in host_patch.items():
            target.write_text(content)
        host_dest = root / 'Andarium/Andarium/Live'
        for fname in ('RedClipboardCodec.swift', 'RedClipboardControls.swift'):
            shutil.copy2(Path(__file__).resolve().parent / 'host' / fname, host_dest / fname)
    if t_report:
        tdir = dest / 'titanium'
        tdir.mkdir(parents=True, exist_ok=True)
        if titanium_apk.resolve() != (tdir / 'Titanium.apk').resolve():
            shutil.copy2(titanium_apk, tdir / 'Titanium.apk')
        (tdir / 'Android.bp').write_text(TITANIUM_BP)
        (tdir / 'source.json').write_text(json.dumps(t_report, indent=2) + '\n')
    cfg.write_text(after)
    if lineage_modified != lineage_original:
        lineage_path.write_text(lineage_modified)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--kernarium',type=Path,required=True,help='Kernarium checkout root')
    p.add_argument('--launcher-src',type=Path,default=Path(__file__).resolve().parent/'launcher_src')
    p.add_argument('--magisk-apk',type=Path,help='Official Magisk v31.1 APK; must match pinned release SHA-256')
    p.add_argument('--dry-run',action='store_true')
    p.add_argument('--titanium-apk',type=Path,help='Official Titanium v157 ARM64 APK (335 MB), with pinned SHA-256')
    p.add_argument('--no-host-clipboard',action='store_true',help='Omit guest and host clipboard bridge source')
    p.add_argument('--diagnostic-userdebug',action='store_true',
        help='Opt-in Android 17 userdebug build with su; NOT an accepted/releasable image')
    args=p.parse_args()
    print(json.dumps(apply(args.kernarium.resolve(),args.launcher_src.resolve(),
          args.magisk_apk.resolve() if args.magisk_apk else None,args.dry_run,
          'userdebug' if args.diagnostic_userdebug else 'keep',
          args.titanium_apk.resolve() if args.titanium_apk else None,
          not args.no_host_clipboard),indent=2))


if __name__=='__main__':
    main()
