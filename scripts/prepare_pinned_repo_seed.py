#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Cache a bounded, non-executable seed of pinned Repo Git objects on Btrfs.

Not a source proof and not a replacement for the original pinned Repo sync
or Kernarium source verifier. Only immutable Git project object stores are
cached, never edited AOSP worktrees, generated Soong state or signing data.
GitHub cache size is capped to avoid evicting other immutable project caches.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess

PINNED_KERNARIUM = "fbe12ee72d195f0241c4fc24090a98b259026604"
BUDGET_BYTES = 3 * 1024**3


def run(*args: str) -> str:
    return subprocess.check_output(args, text=True, stderr=subprocess.PIPE).strip()


def safe_relative(value: str) -> Path:
    path = PurePosixPath(value)
    if (
        not value or value.startswith("/") or "\\" in value
        or str(path) != value or any(part in ("", ".", "..") for part in path.parts)
        or not value.endswith(".git")
    ):
        raise RuntimeError(f"unsafe cached project-object path: {value!r}")
    return Path(*path.parts)


def checked_bare_git(path: Path) -> None:
    if path.is_symlink() or not path.is_dir():
        raise RuntimeError(f"cached Git directory invalid: {path}")
    if run("git", "-C", str(path), "rev-parse", "--is-bare-repository") != "true":
        raise RuntimeError(f"cached object store is not bare: {path}")


def apparent_size(path: Path) -> int:
    # A regular file's logical size bounds cache staging; ignore symlink targets.
    total = 0
    for root, dirs, files in os.walk(path, followlinks=False):
        dirs[:] = [d for d in dirs if not (Path(root) / d).is_symlink()]
        for filename in files:
            entry = Path(root) / filename
            if not entry.is_symlink():
                total += entry.stat().st_size
    return total


def create(workspace: Path, cache: Path) -> None:
    objects = workspace / ".repo/project-objects"
    if not objects.is_dir() or objects.is_symlink():
        raise RuntimeError("source Repo object store missing; source sync did not finish")
    if cache.exists() or cache.is_symlink():
        raise RuntimeError("refusing to replace an existing immutable seed")
    if shutil.disk_usage(workspace).free < 2 * 1024**3:
        print("REPO_SOURCE_SEED_SKIPPED=insufficient_btrfs_metadata_space")
        return
    candidates = []
    for path in objects.rglob("*.git"):
        if not path.is_dir() or path.is_symlink():
            continue
        rel = safe_relative(path.relative_to(objects).as_posix())
        # Cache only recognized bare Repo object stores.
        try:
            checked_bare_git(path)
        except (OSError, subprocess.SubprocessError, RuntimeError):
            continue
        size = apparent_size(path)
        if 0 < size <= BUDGET_BYTES:
            candidates.append((size, rel))
    # Prefer large source stores to avoid expensive delta re-downloads.
    candidates.sort(key=lambda x: (-x[0], x[1].as_posix()))
    chosen = []
    used = 0
    for size, rel in candidates:
        if used + size <= BUDGET_BYTES:
            used += size
            chosen.append((size, rel))
    if not chosen:
        print("REPO_SOURCE_SEED_SKIPPED=no_bare_object_stores_within_budget")
        return
    for _, rel in chosen:
        dest = cache / "project-objects" / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        # On the mounted Btrfs workspace this is copy-on-write, not an
        # additional full-size physical checkout. Git may update its own copy.
        subprocess.run(
            ("cp", "-a", "--reflink=always", str(objects / rel), str(dest)),
            check=True,
        )
    (cache / "seed-manifest.json").write_text(
        json.dumps(
            {
                "schema": 1,
                "kernarium": PINNED_KERNARIUM,
                "max_apparent_bytes": BUDGET_BYTES,
                "apparent_bytes": used,
                "objects": [rel.as_posix() for _, rel in chosen],
            },
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )
    print(f"REPO_SOURCE_SEED_CREATED={len(chosen)}_repositories_{used}_bytes")


def restore(workspace: Path, cache: Path) -> None:
    if not cache.is_dir() or cache.is_symlink():
        raise RuntimeError("cached Repo source seed absent")
    doc = json.loads((cache / "seed-manifest.json").read_text(encoding="utf-8"))
    if doc.get("schema") != 1 or doc.get("kernarium") != PINNED_KERNARIUM:
        raise RuntimeError("cached Repo source version differs")
    entries = doc.get("objects")
    if not isinstance(entries, list) or not entries or len(entries) != len(set(entries)):
        raise RuntimeError("cached Repo source list missing or duplicated")
    if not isinstance(doc.get("apparent_bytes"), int) or not 0 < doc["apparent_bytes"] <= BUDGET_BYTES:
        raise RuntimeError("cached Repo source exceeds budget")
    dest_root = workspace / ".repo/project-objects"
    for value in entries:
        rel = safe_relative(value)
        src = cache / "project-objects" / rel
        dest = dest_root / rel
        checked_bare_git(src)
        if dest.exists() or dest.is_symlink():
            raise RuntimeError(f"refusing to overwrite existing Repo Git objects: {dest}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(("cp", "-a", "--reflink=always", str(src), str(dest)), check=True)
    print(f"REPO_SOURCE_SEED_RESTORED={len(entries)}_bare_git_stores")
    print("NOTE: repo sync + upstream patch verification are still mandatory")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("create", "restore"))
    p.add_argument("--workspace", type=Path, required=True)
    p.add_argument("--cache", type=Path, required=True)
    args = p.parse_args()
    workspace = args.workspace.resolve()
    cache = args.cache.absolute()
    if not workspace.is_dir() or run("stat", "-f", "-c", "%T", str(workspace)) != "btrfs":
        raise SystemExit("source seed must be created or restored on a mounted Btrfs workspace")
    if cache.parent != workspace or cache.name != ".andarium-repo-seed":
        raise SystemExit("cache must be <workspace>/.andarium-repo-seed (refuse external paths)")
    try:
        if args.mode == "create":
            create(workspace, cache)
        else:
            restore(workspace, cache)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"Repo seed {args.mode} failed: {exc}") from exc


if __name__ == "__main__":
    main()
