#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""One checked source-integration command for Kernarium's Android 17 product.

Runs both *read-only* preflights before touching the checkout. Source changes
are NOT an Android release, an Xcode archive, a Magisk root install or an FPS
benchmark. Keep this separate from the upstream accepted-release pipeline.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import install_source_overlay as guest
import host_firstboot as firstboot

REVIEWED_UPSTREAM = '538de0dddaa0af5779bfbf7bb8e12e0938c3389a'


def verified_upstream_revision(root: Path) -> str | None:
    """Return an actual git revision, never treat presence of source anchors
    as proof of a particular commit. Works with a checked-out real repository;
    synthetic test fixtures remain correctly unverified.
    """
    if not (root / '.git').exists():
        return None
    try:
        cp = subprocess.run(['git', '-C', str(root), 'rev-parse', '--verify', 'HEAD'],
                            capture_output=True, text=True, timeout=10)
        value = cp.stdout.strip()
        return value if cp.returncode == 0 and len(value) == 40 else None
    except (OSError, subprocess.TimeoutExpired):
        return None



def integrate(
    kernarium: Path, source: Path, *,
    magisk: Path | None = None,
    titanium: Path | None = None,
    appmanager: Path | None = None,
    termux: Path | None = None,
    fdroid: Path | None = None,
    heliboard: Path | None = None,
    launcher_apk: Path | None = None,
    diagnostic_userdebug: bool = False,
    dry_run: bool = False,
) -> dict:
    kernarium = kernarium.resolve()
    source = source.resolve()
    variant = "userdebug" if diagnostic_userdebug else "keep"
    inputs = (magisk, titanium, appmanager, termux, fdroid, heliboard, launcher_apk)
    kwargs = {
        'magisk': magisk.resolve() if magisk else None,
        'titanium': titanium.resolve() if titanium else None,
        'appmanager': appmanager.resolve() if appmanager else None,
        'termux': termux.resolve() if termux else None,
        'fdroid': fdroid.resolve() if fdroid else None,
        'heliboard': heliboard.resolve() if heliboard else None,
        'launcher': launcher_apk.resolve() if launcher_apk else None,
    }

    # BOTH stages must validate without changing any source first. A bad
    # official APK or an unknown upstream host interface fails before edits.
    guest_preflight = guest.apply(kernarium, source / 'launcher_src',
                                  None, True, variant, None, True)
    host_preflight = None
    if any(inputs):
        host_preflight = firstboot.stage(kernarium, source, kwargs['magisk'],
                                          kwargs['titanium'], dry_run=True,
                                          launcher=kwargs['launcher'],
                                          appmanager=kwargs['appmanager'],
                                          termux=kwargs['termux'], fdroid=kwargs['fdroid'],
                                          heliboard=kwargs['heliboard'])

    checkout_sha = verified_upstream_revision(kernarium)
    report = {
        'android_version': 17,
        'upstream_checkout_commit': checkout_sha,
        'source_revision_checked': checkout_sha == REVIEWED_UPSTREAM,
        'source_api_anchors_checked': True,
        'dry_run': dry_run,
        'guest_overlay': guest_preflight,
        'firstboot': host_preflight,
        'source_patches_applied': False,
        'ios_archive_built': False,
        'iphone_tested': False,
        'magisk_root_verified': False,
        'clipboard_end_to_end_verified': False,
        'aot_on_iphone_verified': False,
    }
    if dry_run:
        return report

    # The actual guest overlay is needed for a native-system clipboard provider
    # and platform-compiled launcher. The ordinary APK installer is optional.
    overlay_result = guest.apply(kernarium, source / 'launcher_src',
                                 None, False, variant, None, True)
    host_result = None
    if any(inputs):
        host_result = firstboot.stage(kernarium, source, kwargs['magisk'],
                                       kwargs['titanium'], dry_run=False,
                                       launcher=kwargs['launcher'],
                                       appmanager=kwargs['appmanager'],
                                          termux=kwargs['termux'], fdroid=kwargs['fdroid'],
                                          heliboard=kwargs['heliboard'])
    report['guest_overlay'] = overlay_result
    report['firstboot'] = host_result
    report['source_patches_applied'] = True
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--kernarium', type=Path, required=True)
    ap.add_argument('--source', type=Path, default=Path(__file__).resolve().parent)
    ap.add_argument('--magisk-apk', type=Path)
    ap.add_argument('--titanium-apk', type=Path)
    ap.add_argument('--appmanager-apk', type=Path)
    ap.add_argument('--termux-apk', type=Path)
    ap.add_argument('--fdroid-apk', type=Path)
    ap.add_argument('--heliboard-apk', type=Path)
    ap.add_argument('--launcher-apk', type=Path)
    ap.add_argument('--diagnostic-userdebug', action='store_true',
                    help='Diagnostic guest with su; NOT a signed release and NOT Magisk-managed root')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    result = integrate(args.kernarium, args.source,
                       magisk=args.magisk_apk, titanium=args.titanium_apk,
                       appmanager=args.appmanager_apk, termux=args.termux_apk,
                       fdroid=args.fdroid_apk, heliboard=args.heliboard_apk,
                       launcher_apk=args.launcher_apk,
                       diagnostic_userdebug=args.diagnostic_userdebug,
                       dry_run=args.dry_run)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
