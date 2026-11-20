#!/usr/bin/env python3
"""Fetch the publicly released, independently verified Andarium kernel.

CircleCI needs no personal GitHub token. The publishing GitHub workflow first
rechecks the artifact against pinned Kernarium ABI 29 and 4 KiB descriptors.
CircleCI repeats the pinned upstream verification before compiling Android 17.
"""
import hashlib
import io
import os
import pathlib
import tarfile
import time
import urllib.error
import urllib.request

NAME = "andarium-kernel-abi29-ca1-20261119"
BASE = (
    "https://github.com/SeanEmcee/SeanEmcee-Andarium-Red/"
    "releases/download/" + NAME + "/"
)
MAX_ARCHIVE = 128 * 1024 * 1024
MAX_EXTRACTED = 512 * 1024 * 1024


def get_public_asset(filename):
    for attempt in range(8):
        try:
            req = urllib.request.Request(
                BASE + filename,
                headers={"User-Agent": "Andarium-Red-CircleCI-Pinned-Artifact/1"},
            )
            with urllib.request.urlopen(req, timeout=180) as response:
                data = response.read(MAX_ARCHIVE + 1)
            if len(data) > MAX_ARCHIVE:
                raise SystemExit("Kernel release asset exceeds size bound")
            return data
        except urllib.error.HTTPError as exc:
            if exc.code == 404 and attempt < 7:
                print("Kernel release not published yet; retrying public transfer", flush=True)
                time.sleep(15)
                continue
            raise SystemExit(
                "Verified public kernel release not available (HTTP "
                + str(exc.code)
                + "). Check the publish-verified-kernel GitHub Actions workflow."
            ) from None


checksum_data = get_public_asset(NAME + ".sha256").decode("ascii", "strict").strip().split()
if len(checksum_data) != 2 or checksum_data[1] != NAME + ".tar.gz":
    raise SystemExit("Invalid release checksum manifest")
expected = checksum_data[0]
if len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
    raise SystemExit("Invalid SHA256 in release manifest")
archive = get_public_asset(NAME + ".tar.gz")
if hashlib.sha256(archive).hexdigest() != expected:
    raise SystemExit("Published kernel archive SHA256 mismatch")

dest = pathlib.Path(".build/android-6.18-arm64-4k-20261119-6.18.60-ca1")
if dest.exists():
    raise SystemExit("Refusing to overwrite an existing kernel artifact directory")
written = 0
files = 0
with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
    for member in tar:
        path = pathlib.PurePosixPath(member.name)
        if (path.is_absolute() or ".." in path.parts or not path.parts
                or path.parts[0] != "android-6.18-arm64-4k-20261119-6.18.60-ca1"):
            raise SystemExit("Invalid kernel archive path")
        if member.isdir():
            continue
        if not member.isfile():
            raise SystemExit("Kernel archive contains an unsupported file type")
        written += member.size
        if written > MAX_EXTRACTED:
            raise SystemExit("Kernel archive exceeds unpacked size bound")
        relative = path.parts[1:]
        if not relative:
            raise SystemExit("Invalid kernel artifact file path")
        target = dest.joinpath(*relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        extracted = tar.extractfile(member)
        if extracted is None:
            raise SystemExit("Failed reading a kernel artifact member")
        with extracted, target.open("xb") as output:
            while True:
                chunk = extracted.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
        files += 1
if files == 0:
    raise SystemExit("Empty verified kernel artifact")
print("Downloaded public verified ABI29 kernel, SHA256:", expected)
print("Extracted kernel artifact regular files:", files)
