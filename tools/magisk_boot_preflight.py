#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Non-destructive audit of the real Magisk boot integration inputs.

This does not patch an image, change verified release metadata, or claim that
Andarium's UML boot path is compatible. A working guest requires Android's own
build/release verification and an actual boot before Magisk can be certified.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
import zipfile
from pathlib import Path

MAGISK_SHA256 = '89cefac0a318afa39fb3880c45c87b036c05bc1ebf02a7a715b7f8d7c26ac6e7'
MAGISK_BYTES = 10679283
ESSENTIAL = {
    'assets/boot_patch.sh': 'Magisk official boot patch logic',
    'assets/util_functions.sh': 'Magisk patch helpers',
    'lib/arm64-v8a/libmagiskinit.so': 'arm64 boot-time init binary',
    'lib/arm64-v8a/libmagiskboot.so': 'arm64 boot image packing binary',
}


def digest_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def inspect_magisk(apk: Path) -> dict:
    if not apk.is_file() or apk.stat().st_size != MAGISK_BYTES or digest_file(apk) != MAGISK_SHA256:
        raise ValueError('Official Magisk v31.1 APK checksum/length mismatch')
    with zipfile.ZipFile(apk) as jar:
        files = set(jar.namelist())
        missing = sorted(set(ESSENTIAL) - files)
        # Never assume an APK package layout is identical across Magisk releases.
        extras = sorted(x for x in files if x.startswith('lib/arm64-v8a/') and 'magisk' in x.lower())
        return {'verified_release_sha256': MAGISK_SHA256,
                'essential_parts_present': not missing, 'missing': missing,
                'arm64_magisk_binaries': extras,
                'can_stage_boot_patcher': not missing}


def inspect_init_boot(path: Path) -> dict:
    if not path.is_file():
        raise ValueError('init_boot image not found')
    with path.open('rb') as f:
        header = f.read(48)
    if len(header) < 44 or header[:8] != b'ANDROID!':
        raise ValueError('Not a standard Android init_boot image (missing ANDROID! header)')
    # Android boot image header v3/v4 layout, from AOSP bootimg.h.
    kernel_size, ramdisk_size, _os_version, header_size = struct.unpack_from('<4I', header, 8)
    version = struct.unpack_from('<I', header, 40)[0]
    if version not in (3, 4) or header_size < 1580 or ramdisk_size < 1:
        raise ValueError('Unexpected init_boot header version, size, or missing ramdisk')
    if kernel_size != 0:
        raise ValueError('init_boot should carry no kernel; got nonzero kernel size')
    return {'boot_header_version': version, 'kernel_bytes': kernel_size,
            'ramdisk_bytes': ramdisk_size, 'image_sha256': digest_file(path),
            'boot_structure_validated': True,
            'magisk_boot_interception_compatible': 'UNVERIFIED: Kernarium UML boot packaging differs from a physical phone'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--magisk-apk', type=Path, required=True)
    p.add_argument('--init-boot', type=Path, required=True)
    p.add_argument('--report', type=Path)
    args = p.parse_args()
    a = inspect_magisk(args.magisk_apk)
    b = inspect_init_boot(args.init_boot)
    report = {'magisk': a, 'init_boot': b,
              'prepared_for_boot_patch_trial': bool(a['can_stage_boot_patcher']),
              'magisk_root_working': False, 'guest_17_boot_verified': False,
              'notes': ['Never replace a boot image in an accepted release in place.',
                        'Requires original upstream Magisk patcher on a compatible guest, new release signing and boot tests.',
                        'Kernel-less UML boot and Magisk init interception still require integration validation.']}
    result = json.dumps(report, indent=2) + '\n'
    if args.report: args.report.write_text(result)
    print(result)

if __name__ == '__main__':
    main()
