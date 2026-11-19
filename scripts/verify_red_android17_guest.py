#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Fail-closed acceptance gate for an Andarium Red Android 17 proof image.

This does NOT synthesize Android from a manifest. It verifies the separately
compiled Red guest release, then (optionally) the exact image copied into an
iPhoneOS .app. Provenance and actual boot are separate release gates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

NEEDED = (
    "release-manifest.json",
    "boot/kernel-command-line.txt",
    "guest/partition-layout.json",
    "guest/system.img",
)


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{path}: expected JSON object")
    return value


def inspect(folder: Path) -> dict:
    require(folder.is_dir() and not folder.is_symlink(), "Red guest release folder missing")
    for name in NEEDED:
        file = folder / name
        require(file.is_file() and not file.is_symlink(),
                f"Missing real Android guest file: {file}")
    manifest = read_json(folder / NEEDED[0])
    layout = read_json(folder / NEEDED[2])
    require(manifest.get("acceptance") == "unsigned-proof",
            "Only a separately compiled, verifiable Red Android proof is accepted")
    rid = manifest.get("release_id", "")
    require(isinstance(rid, str) and rid.startswith("unsigned-proof-red-"),
            f"Not a Red developer proof: {rid!r}")
    android = manifest.get("android")
    require(isinstance(android, dict) and android.get("major") == 17
            and android.get("signed") is False,
            "Guest must be unsigned Android 17 from the Red image producer")
    require(manifest.get("product_family") == "lineage-andarium",
            "Wrong guest product family")
    producer = manifest.get("producer")
    require(isinstance(producer, dict)
            and bool(re.fullmatch(r"[0-9a-f]{64}", str(producer.get("target_files_sha256", ""))))
            and bool(re.fullmatch(r"[0-9a-f]{64}", str(producer.get("system_disk_sha256", "")))),
            "Missing compiled Android target-files/system-disk provenance")
    system = layout.get("system_disk")
    require(isinstance(system, dict) and layout.get("schema_version") == 2,
            "Invalid Andarium Android partition layout")
    actual_disk = folder / "guest/system.img"
    require(system.get("size") == actual_disk.stat().st_size,
            "Android system image byte count differs from partition manifest")
    checksum = digest(actual_disk)
    require(checksum == system.get("sha256")
            and checksum == producer["system_disk_sha256"],
            "Android system disk failed SHA-256 integrity checks")
    for name in NEEDED[1:]:
        require((folder / name).stat().st_size > 0,
                f"Empty Android guest file: {name}")
    return {"release_id": rid, "system_disk_sha256": checksum, "major": 17}


def inspect_modified_host(checkout: Path) -> None:
    for name, marker in (
        ("Andarium/Andarium/Shared/RedDisplayChoice.swift", "RedResolutionSetting"),
        ("Andarium/Andarium/Shared/RedMemoryChoices.swift", "RedMemory"),
        ("Andarium/Andarium/Shared/Model.swift", "redNativePixelSize"),
    ):
        p = checkout / name
        require(p.is_file() and marker in p.read_text(encoding="utf-8"),
                f"Modified Andarium Red host source missing: {name}")
    # Actual Android launcher is built into target-files separately. Its
    # existence in source is not proof it reached the guest image.
    require((checkout / "android/lineage-24/overlay/twoyi-red/launcher/Android.bp").is_file(),
            "Modified Red Android HOME module is missing from source")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--proof", type=Path)
    ap.add_argument("--app", type=Path)
    ap.add_argument("--kernarium", type=Path, required=True)
    args = ap.parse_args()
    require((args.proof is None) != (args.app is None),
            "Provide exactly one of --proof or --app")
    inspect_modified_host(args.kernarium)
    folder = args.proof if args.proof else args.app / "andarium-system"
    record = inspect(folder)
    print(f"ANDARIUM_RED_ANDROID17_PROOF_VERIFIED: {record['release_id']}")
    print(f"SYSTEM_DISK_SHA256: {record['system_disk_sha256']}")
    if args.app:
        require((args.app / "Andarium").is_file(),
                "Full native Andarium executable missing from iOS app")


if __name__ == "__main__":
    main()
