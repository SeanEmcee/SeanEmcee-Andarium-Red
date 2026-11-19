#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Audit an actual modified Kernarium checkout's bundled Android APK resources.

This does NOT prove installation or guest operation. It ensures the Xcode
resource group, host installer descriptor, and on-disk APKs agree before a
resource-heavy iOS/Android build starts. Read-only and fails closed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import host_firstboot as host

PACKAGE_RE = re.compile(
    r'Package\(filename: "(?P<name>[^"\n]+)", androidPackage: "(?P<id>[^"\n]+)",\s*'
    r'expectedBytes: (?P<bytes>[0-9_]+),\s*expectedSHA256: "(?P<sha>[0-9a-f]{64})"\)',
    re.M,
)


def audit(kernarium: Path) -> dict:
    base = kernarium / 'Andarium'
    folder = base / 'RedBundledAPKs'
    project = base / 'Andarium.xcodeproj/project.xcproj'
    swift = base / 'Andarium/Live/RedGuestApkInstaller.swift'
    if not folder.is_dir() or folder.is_symlink() or not project.is_file() or not swift.is_file():
        raise ValueError('Kernarium checkout is missing a real APK directory, Xcode project or installer source')
    names = sorted(x.name for x in folder.iterdir())
    if not names:
        raise ValueError('No staged APKs to audit')
    if len(set(names)) != len(names) or any(name not in host.BUNDLE_ORDER for name in names):
        raise ValueError('Unrecognized staged APK filenames')
    match = host.PROJECT_GROUP_RE.search(project.read_text())
    if not match:
        raise ValueError('Xcode project is missing the Red Bundled APK resources group')
    entries = host.PROJECT_PATH_RE.findall(match.group('children'))
    residue = host.PROJECT_PATH_RE.sub('', match.group('children')).replace(',', '').strip()
    if residue or len(entries) != len(set(entries)) or set(entries) != set(names):
        raise ValueError('Xcode project resources differ from staged APK files')
    descriptors = {}
    for found in PACKAGE_RE.finditer(swift.read_text()):
        key = found.group('name')
        if key in descriptors:
            raise ValueError(f'Duplicate host installer descriptor for {key}')
        descriptors[key] = {'android_package': found.group('id'),
                            'bytes': int(found.group('bytes').replace('_', '')),
                            'sha256': found.group('sha')}
    if not descriptors:
        raise ValueError('Host installer has no APK descriptors')
    verified = []
    for name in names:
        path = folder / name
        # The official release identity must match the hard-coded pin from
        # host_firstboot; do not trust a same-name file with different bytes.
        host.validate_existing(name, path)
        expected = descriptors.get(name)
        if expected is None:
            raise ValueError(f'No host installer descriptor for {name}')
        hasher = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1 << 20), b''):
                hasher.update(block)
        actual = hasher.hexdigest()
        if path.stat().st_size != expected['bytes'] or actual != expected['sha256']:
            raise ValueError(f'Swift APK installer digest or size differs from {name}')
        verified.append({'filename': name, 'android_package': expected['android_package'],
                         'bytes': expected['bytes'], 'sha256': actual})
    return {'product': 'Andarium Red Android 17', 'source_apk_bundle_consistent': True,
            'build_executed': False, 'guest_install_verified': False,
            'staged_apks': verified}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kernarium', required=True, type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    try:
        report = audit(args.kernarium.resolve())
    except (OSError, ValueError) as error:
        print(f'APK_STAGE_NO_GO: {error}', file=sys.stderr)
        return 2
    result = json.dumps(report, indent=2) + '\n'
    if args.out:
        args.out.write_text(result)
    print(result, end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
