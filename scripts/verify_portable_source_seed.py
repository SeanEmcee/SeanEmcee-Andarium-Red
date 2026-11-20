#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Validate public pinned Git-object cache before portable release."""
import json
import os
import subprocess
import sys
from pathlib import Path, PurePosixPath

MAX_BYTES = 3 * 1024**3
PIN = "fbe12ee72d195f0241c4fc24090a98b259026604"

def fail(message):
    raise SystemExit("ERROR: unsafe portable source cache: " + message)

if len(sys.argv) != 2:
    fail("expected cache directory argument")
root = Path(sys.argv[1])
manifest = root / "seed-manifest.json"
if root.name != ".andarium-repo-seed" or root.is_symlink() or not root.is_dir():
    fail("invalid cache root")
if manifest.is_symlink() or not manifest.is_file():
    fail("missing cache manifest")
doc = json.loads(manifest.read_text(encoding="utf8"))
if doc.get("schema") != 1 or doc.get("kernarium") != PIN:
    fail("unrecognized pinned upstream revision")
paths = doc.get("objects")
if not isinstance(paths, list) or not paths or len(paths) != len(set(paths)):
    fail("invalid object path list")
if type(doc.get("apparent_bytes")) is not int or not 0 < doc["apparent_bytes"] <= MAX_BYTES:
    fail("reported object size invalid")
actual = 0
for item in paths:
    if not isinstance(item, str) or not item.endswith(".git"):
        fail("invalid object entry")
    rel = PurePosixPath(item)
    if rel.is_absolute() or rel.as_posix() != item or ".." in rel.parts or "\\" in item:
        fail("unsafe object path")
    obj = root / "project-objects" / Path(*rel.parts)
    if obj.is_symlink() or not obj.is_dir():
        fail("missing object directory")
    cp = subprocess.run(["git", "-C", str(obj), "rev-parse", "--is-bare-repository"], capture_output=True, text=True)
    if cp.returncode != 0 or cp.stdout.strip() != "true":
        fail("not a bare Git repo")
    cache_root = root.resolve(strict=True)
    def validate_link(link):
        try:
            resolved = link.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            fail("broken or recursive Git metadata link " + str(link) + ": " + str(exc))
        if not resolved.is_relative_to(cache_root):
            fail("Git metadata link escapes source seed: " + str(link) + " -> " + str(resolved))
        return resolved
    for folder, dirs, files in os.walk(obj, followlinks=False):
        kept = []
        for name in dirs:
            directory = Path(folder) / name
            if directory.is_symlink():
                if not validate_link(directory).is_dir():
                    fail("symlinked Git directory target is not a directory")
            else:
                kept.append(name)
        dirs[:] = kept
        for filename in files:
            file = Path(folder) / filename
            if file.is_symlink():
                if not validate_link(file).is_file():
                    fail("symlinked Git file target is not a file")
                continue
            actual += file.stat().st_size
            if actual > MAX_BYTES:
                fail("object data exceeds 3GiB budget")
print(f"VERIFIED_PORTABLE_SOURCE_CACHE={len(paths)}_repos_{actual}_bytes")
print("This accelerator does not replace the original pinned Repo sync or verification")
