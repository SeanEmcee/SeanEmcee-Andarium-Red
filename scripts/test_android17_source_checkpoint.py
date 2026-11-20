#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline regression tests for two-stage Android 17 source and seed safety."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parent
script = (root / "build_red_android17_proof.sh").read_text(encoding="utf-8")
guards = [
    "ANDARIUM_PREPARED_SOURCE_CHECKPOINT_MATCHED",
    "ANDARIUM_ANDROID17_SOURCE_CHECKPOINT_VERIFIED",
    "if (( ! use_prepared_source )) && [[ ! -d",
    "if (( ! use_prepared_source )) && [[ -n",
]
for guard in guards:
    assert guard in script, f"missing cache/source safety guard: {guard}"
spec = importlib.util.spec_from_file_location("seed", root / "prepare_pinned_repo_seed.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
for bad in ("../escape.git", "/absolute.git", "foo//bar.git",
            "foo/../bar.git", "foo\\bar.git", "wrong-type.txt"):
    try:
        mod.safe_relative(bad)
    except RuntimeError:
        continue
    raise AssertionError(f"unsafe Git source path accepted: {bad}")
assert mod.safe_relative("platform/frameworks/base.git").as_posix() == "platform/frameworks/base.git"
with tempfile.TemporaryDirectory() as tmp:
    repo = Path(tmp) / "bare.git"
    subprocess.run(["git", "init", "--bare", "--quiet", str(repo)], check=True)
    mod.checked_bare_git(repo)
    assert mod.apparent_size(repo) > 0
print("PASS: split source checkpoint, no double accessibility copy, Git object seed validation")
