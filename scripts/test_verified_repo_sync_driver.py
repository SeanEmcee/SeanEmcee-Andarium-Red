#!/usr/bin/env python3
"""Offline tests for fail-fast, pinned-source Repo checkout recovery."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile

file = Path(__file__).with_name("create_verified_repo_sync_driver.py")
spec = importlib.util.spec_from_file_location("sync_driver", file)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
with tempfile.TemporaryDirectory() as tmp:
    repo = Path(tmp) / "Kernarium"
    original = repo / "android/lineage-24/build/prepare-sources.sh"
    original.parent.mkdir(parents=True)
    original.write_text(
        '#!/bin/sh\nset -eu\n'
        'AOSP_SOURCE=/tmp/example\nJOBS=4\n'
        'python3 pin.py --output .repo/local_manifests/pin.xml\n'
        '\trepo sync -c --detach -j "$JOBS"\n'
        'echo unchanged_lfs_and_verifiers\n',
        encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=CI",
                    "-c", "user.email=ci@example.invalid", "commit",
                    "-qm", "pinned-fixture"], check=True)
    module.PIN = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    before = original.read_bytes()
    derived = original.with_name("prepare-sources.andarium-ci.sh")
    audit = Path(tmp) / "sync-audit.txt"
    module.create(original, derived, audit)
    data = derived.read_text()
    assert data.index("--output .repo/local_manifests/pin.xml") < data.index(
        "prebuilts/module_sdk/ConfigInfrastructure")
    assert data.count("prebuilts/module_sdk/ConfigInfrastructure") == 2
    assert data.count("ANDARIUM_SOURCE_GLOBAL_RETRY_SINGLE_WORKER") == 1
    assert data.count("repo sync -c --detach -j 1 --fail-fast") >= 2
    assert "echo unchanged_lfs_and_verifiers" in data
    assert original.read_bytes() == before
    subprocess.run(["sh", "-n", str(derived)], check=True)
    try:
        module.create(original, derived, audit)
    except SystemExit:
        pass
    else:
        raise AssertionError("unsafe duplicate derivative was accepted")
print("PASS: exact pinned Repo sync, scoped checkout first, bounded retry, original producer untouched")
