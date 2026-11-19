#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Fail-closed static root readiness audit of an Android 17 Kernarium guest tree.

Magisk manager is not an elevated guest runtime. A userdebug `su` is not Magisk.
A real Magisk root implementation requires boot artifact and device verification.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path


def inspect(root: Path) -> dict:
    config=root/'android/lineage-24/metadata/lineage.env'
    make=root/'android/lineage-24/overlay/lineage_andarium.mk'
    if not config.is_file() or not make.is_file():
        raise ValueError('Kernarium Android 17 source tree not present')
    source=config.read_text()
    makefile=make.read_text()
    if 'LINEAGE24_ANDROID_MAJOR=17' not in source or 'TARGET_NO_KERNEL_OVERRIDE := true' not in makefile:
        raise ValueError('Not the reviewed Android 17 UML guest configuration')
    userdebug="LINEAGE24_BUILD_VARIANT='userdebug'" in source
    su_config='WITH_SU := true' in makefile
    return {
        'android_version':17,
        'guest_variant':'userdebug' if userdebug else 'user',
        'su_configuration_present':su_config,
        'diagnostic_su_possible':userdebug and su_config,
        'magisk_manager_pinned_in_host':False,
        'magisk_kernel_runtime_integrated':False,
        'root_proven_in_guest':False,
        'requires':'Boot a real image and test exact root path; do not conflate userdebug su with Magisk.',
        'release_ready':False,
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--kernarium',required=True,type=Path)
    args=p.parse_args()
    print(json.dumps(inspect(args.kernarium.resolve()),indent=2))

if __name__=='__main__':main()
