#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Inspect a cached/published iPhoneOS Android runtime framework set.

A verified framework set is not an Android guest, a built iOS app, or a
LiveContainer test. Upstream package-ios-frameworks.sh still performs the
complete publisher gate on fresh builds. This guard additionally validates
restored cross-run framework payloads before they are consumed by Xcode.
"""
from __future__ import annotations

import argparse
import plistlib
import subprocess
from pathlib import Path

FRAMEWORKS = (
    "KRuntime_Android_6_18_4K",
    "MesaEGL",
    "MesaGallium",
    "KosmicKrisp",
    "GPTFDisk",
    "LibZstd",
)
ARCHIVES = ("HostBattery", "HostVideoEncoder")
REQUIRED = (*FRAMEWORKS, *ARCHIVES)


def require(test: bool, reason: str) -> None:
    if not test:
        raise SystemExit(f"ERROR: iPhoneOS Android runtime cache invalid: {reason}")


def plist(file: Path) -> dict:
    require(file.is_file() and not file.is_symlink(), f"missing plist {file}")
    with file.open("rb") as handle:
        value = plistlib.load(handle)
    require(isinstance(value, dict), f"malformed plist {file}")
    return value


def valid_file(path: Path) -> None:
    require(path.is_file() and not path.is_symlink() and path.stat().st_size > 0,
            f"missing, symlinked or empty binary: {path}")


def check_bundle(root: Path, name: str, framework: bool) -> None:
    bundle = root / (name + ".xcframework")
    require(bundle.is_dir() and not bundle.is_symlink(), f"missing bundle {name}")
    manifest = plist(bundle / "Info.plist")
    libraries = manifest.get("AvailableLibraries")
    require(isinstance(libraries, list) and len(libraries) >= 1,
            f"{name}: empty AvailableLibraries")
    matches = [
        row for row in libraries
        if isinstance(row, dict) and row.get("LibraryIdentifier") == "ios-arm64"
        and str(row.get("SupportedPlatform", "")).lower() == "ios"
        and not row.get("SupportedPlatformVariant")
        and "arm64" in row.get("SupportedArchitectures", [])
    ]
    require(len(matches) == 1, f"{name}: no unique iPhoneOS arm64 library")
    row = matches[0]
    lib = row.get("LibraryPath")
    require(isinstance(lib, str) and lib and "/" not in lib and "\\" not in lib,
            f"{name}: unsafe or absent LibraryPath")
    slice_dir = bundle / "ios-arm64"
    require(slice_dir.is_dir() and not slice_dir.is_symlink(),
            f"{name}: missing iPhoneOS device slice")
    if framework:
        require(lib == name + ".framework", f"{name}: unexpected framework path")
        frame = slice_dir / lib
        require(frame.is_dir() and not frame.is_symlink(),
                f"{name}: missing framework directory")
        valid_file(frame / name)
        privacy = frame / "PrivacyInfo.xcprivacy"
        if name not in ("GPTFDisk", "LibZstd"):
            require(privacy.is_file() and not privacy.is_symlink(),
                    f"{name}: missing privacy manifest")
    else:
        require(lib.endswith(".a"), f"{name}: expected static archive")
        valid_file(slice_dir / lib)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", required=True, type=Path)
    p.add_argument("--kernarium", required=True, type=Path)
    args = p.parse_args()
    root = args.root.resolve(strict=True)
    kernarium = args.kernarium.resolve(strict=True)
    require(root == kernarium / ".build/kernarium-xcframeworks",
            "framework output is not the pinned Kernarium publication path")
    require(root.is_dir(), "framework root absent")
    actual = {part.name for part in root.iterdir() if part.name.endswith(".xcframework")}
    require(set(REQUIRED).issubset(actual),
            f"published bundle set missing {sorted(set(REQUIRED) - actual)}")
    for name in FRAMEWORKS:
        check_bundle(root, name, True)
    for name in ARCHIVES:
        check_bundle(root, name, False)
    common = kernarium / "kernel/common"
    descriptor = kernarium / "kernel/mainline-6.18/artifacts/accepted-android-4k.env"
    artifact_dir = (
        kernarium / ".build/kernel/artifacts"
        / "android-6.18-arm64-4k-20261119-6.18.60-ca1"
    )
    subprocess.run([
        "python3", "-B", str(common / "artifacts/verify-kernel-artifact.py"),
        "--artifact", str(artifact_dir),
        "--common-root", str(common),
        "--abi-metadata", str(common / "abi/identity.env"),
        "--compatible", "--expected-family", "android-6.18",
        "--expected-slice", "arm64", "--expected-release-series", "6.18",
        "--descriptor", str(descriptor),
    ], check=True)
    print(f"VERIFIED_IOS_RUNTIME_CACHE: {len(REQUIRED)} iPhoneOS ARM64 XCFrameworks")
    print("VERIFIED_KERNEL_INTEGRITY: original pinned Kernarium descriptor and ABI29")
    print("GUEST_IMAGE_STATUS: not part of the runtime cache")


if __name__ == "__main__":
    main()
