#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Package a REAL, already-compiled Android 17 unsigned proof for Andarium Red.

Reads the actual target-files ZIP and verified assembled GPT disk. It does NOT
compile Android, patch Magisk, sign a release or fabricate an Android boot test.
Output is accepted only as an unsigned proof by Andarium's developer builds.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

MODULES = ("TwoyiRedLauncher", "TwoyiRedClipboard")
RELEASE_RE = re.compile(r"[a-z0-9][a-z0-9._-]{0,48}")
PROPERTY_CANDIDATES = (
    "SYSTEM/build.prop", "SYSTEM/system/build.prop",
    "SYSTEM/etc/build.prop",
)


def regular(path: Path, name: str) -> Path:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"{name} is missing, unsafe or not a regular file: {path}")
    return path


def digest(path: Path) -> str:
    hash_ = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            hash_.update(part)
    return hash_.hexdigest()


def assignments(path: Path) -> dict[str, str]:
    result = {}
    for raw in regular(path, "Kernarium metadata").read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key in result:
            raise ValueError(f"Duplicate Kernarium metadata: {key}")
        result[key] = val
    return result


def target_metadata(archive: zipfile.ZipFile) -> tuple[dict[str, str], dict[str, str]]:
    paths = set(archive.namelist())
    found = [name for name in PROPERTY_CANDIDATES if name in paths]
    if not found:
        raise ValueError("Target files lack SYSTEM build.prop metadata")
    properties = {}
    for line in archive.read(found[0]).decode("utf-8", errors="strict").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key in properties and properties[key] != value:
            raise ValueError("Conflicting values for Android property " + key)
        properties[key] = value
    def first(*names: str) -> str:
        return next((properties[n] for n in names if properties.get(n)), "")
    android = {
        "fingerprint": first("ro.build.fingerprint", "ro.system.build.fingerprint"),
        "build_number": first("ro.build.version.incremental", "ro.system.build.version.incremental"),
        "security_patch": first("ro.build.version.security_patch", "ro.system.build.version.security_patch"),
        "release": first("ro.build.version.release", "ro.system.build.version.release"),
    }
    if android["release"] != "17":
        raise ValueError(f"Target files are not Android 17: {android['release']!r}")
    if not android["fingerprint"] or not re.fullmatch(r"[0-9]{1,10}", android["build_number"]):
        raise ValueError("Unsigned Android 17 target files lack fingerprint or numeric build number")
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", android["security_patch"]):
        raise ValueError("Android 17 target files have invalid security patch date")
    located = {}
    for module in MODULES:
        matched = [name for name in paths
                   if name.lower().endswith(".apk") and module.lower() in name.lower()]
        if not matched:
            raise ValueError(f"Target files do not include Android module {module}")
        located[module] = sorted(matched)[0]
    return android, located


def manifest(*, release_name: str, product_family: str, properties: dict[str, str],
             disk_sha: str, target_sha: str) -> dict:
    if not RELEASE_RE.fullmatch(release_name):
        raise ValueError("Proof release name must use 1–49 lowercase letters, digits, dot, hyphen or underscore")
    if not product_family.startswith("lineage-"):
        raise ValueError("The checkout is not a verified LineageOS product family")
    return {
        "acceptance": "unsigned-proof",
        "release_id": "unsigned-proof-" + release_name,
        "product_family": product_family,
        "producer": {
            "proof_for_release_id": release_name,
            "system_disk_sha256": disk_sha,
            "target_files_sha256": target_sha,
            "purpose": "Andarium Red developer-only unsigned proof",
        },
        "android": {
            "major": 17,
            "fingerprint": properties["fingerprint"],
            "build_number": int(properties["build_number"]),
            "security_patch": properties["security_patch"],
            "signed": False,
        },
        "kernel": {"page_size": 4096},
        "inventory": [],
        "source": {},
    }


def create(*, kernarium: Path, target_files: Path, disk_dir: Path, cmdline: Path,
           output: Path, release_name: str) -> dict:
    if output.exists() or output.is_symlink():
        raise ValueError("Refusing to overwrite existing proof output")
    metadata = assignments(kernarium / "android/lineage-24/metadata/lineage.env")
    acceptance = assignments(kernarium / "android/lineage-24/metadata/accepted-release.env")
    if metadata.get("LINEAGE24_ANDROID_MAJOR") != "17":
        raise ValueError("Kernarium checkout is not Android 17")
    product = acceptance.get("LINEAGE24_ACCEPTED_PRODUCT_FAMILY", "")
    disk = regular(disk_dir / "system.img", "Android GPT system disk")
    layout = regular(disk_dir / "partition-layout.json", "partition layout")
    command = regular(cmdline, "kernel command line")
    if not command.read_text(encoding="utf-8").split():
        raise ValueError("Guest kernel command line cannot be empty")
    layout_data = json.loads(layout.read_text(encoding="utf-8"))
    if layout_data.get("schema_version") != 2:
        raise ValueError("Android GPT partition layout must be schema 2")
    disk_metadata = layout_data.get("system_disk", {})
    if disk_metadata.get("size_bytes") != disk.stat().st_size:
        raise ValueError("Assembled disk length disagrees with partition layout")
    actual_sha = digest(disk)
    if disk_metadata.get("sha256") != actual_sha:
        raise ValueError("Assembled disk SHA256 disagrees with partition layout")

    with zipfile.ZipFile(regular(target_files, "target-files ZIP")) as archive:
        if archive.testzip() is not None:
            raise ValueError("Compiled target-files archive has corrupt members")
        props, modules = target_metadata(archive)
    target_sha = digest(target_files)
    proof = manifest(release_name=release_name, product_family=product,
                     properties=props, disk_sha=actual_sha, target_sha=target_sha)

    verifier = kernarium / "android/lineage-24/tools/ubd-disk.py"
    regular(verifier, "Kernarium GPT disk verifier")
    result = subprocess.run([sys.executable, "-B", str(verifier), "verify",
                             "--layout", str(layout), "--disk", str(disk), "--hash"],
                            capture_output=True, text=True, timeout=900)
    if result.returncode:
        raise ValueError("Kernarium rejected Android GPT disk: " + result.stderr[-2000:])

    output.parent.mkdir(parents=True, exist_ok=True)
    # Writes only into a scratch directory. Failure never publishes half a proof.
    with tempfile.TemporaryDirectory(prefix=".andarium-red-proof-", dir=output.parent) as tmp:
        temp = Path(tmp)
        for rel, src in (
            ("guest/system.img", disk),
            ("guest/partition-layout.json", layout),
            ("boot/kernel-command-line.txt", command),
        ):
            destination = temp / rel
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, destination)
        if digest(temp / "guest/system.img") != actual_sha:
            raise ValueError("Android disk was modified while proof was being packaged")
        (temp / "release-manifest.json").write_text(
            json.dumps(proof, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if output.exists():
            raise ValueError("Proof output appeared while being packaged")
        temp.rename(output)
    return {
        "unsigned_proof_created": True,
        "release_directory": str(output),
        "release_id": proof["release_id"],
        "android_17_target_modules": modules,
        "target_files_sha256": target_sha,
        "disk_sha256": actual_sha,
        "magisk_root_verified": False,
        "iphone_build_verified": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kernarium", type=Path, required=True)
    ap.add_argument("--target-files", type=Path, required=True)
    ap.add_argument("--disk-dir", type=Path, required=True)
    ap.add_argument("--kernel-cmdline", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--release-name", required=True)
    a = ap.parse_args()
    try:
        out = create(kernarium=a.kernarium.resolve(), target_files=a.target_files.resolve(),
                     disk_dir=a.disk_dir.resolve(), cmdline=a.kernel_cmdline.resolve(),
                     output=a.output.absolute(), release_name=a.release_name)
        print(json.dumps(out, indent=2))
        return 0
    except (OSError, ValueError, zipfile.BadZipFile, subprocess.TimeoutExpired) as exc:
        print("ANDROID_PROOF_NO_GO: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
