#!/usr/bin/env python3
"""Derive a fail-fast, retryable Repo checkout from the exact pinned producer.

The original Kernarium prepare-sources.sh remains byte-for-byte unchanged.
Only its 'repo sync' call changes. The unchanged pinned manifest, original
patch verifiers and LFS handling must still run. No forced checkout, deleted
project, switched Git revision or cache replacement is performed.
"""
import argparse
import hashlib
from pathlib import Path
import subprocess

PIN = "fbe12ee72d195f0241c4fc24090a98b259026604"
OLD_SYNC = '\trepo sync -c --detach -j "$JOBS"\n'
NEW_SYNC = """\t# CI preflight: reproduce the prior failing pinned ConfigInfrastructure
\t# checkout BEFORE fetching more than a thousand other projects.
\tif ! repo sync -c --detach -j 1 --fail-fast prebuilts/module_sdk/ConfigInfrastructure; then
\t\tprintf '%s\\n' 'ANDARIUM_SOURCE_SCOPED_CHECKOUT_RETRY=1' >&2
\t\trepo sync -c --detach -j 1 --fail-fast prebuilts/module_sdk/ConfigInfrastructure
\tfi
\t# Same original pinned Repo sync, now fail-fast rather than waiting for
\t# every unrelated checkout after an error. Retry ONCE at one worker, using
\t# existing already-fetched objects without rewriting pinned source policy.
\tif ! repo sync -c --detach -j "$JOBS" --fail-fast; then
\t\tprintf '%s\\n' 'ANDARIUM_SOURCE_GLOBAL_RETRY_SINGLE_WORKER=1' >&2
\t\tdf -h "$AOSP_SOURCE" / >&2 || true
\t\trepo sync -c --detach -j 1 --fail-fast
\tfi
"""

def create(original: Path, derivative: Path, audit: Path):
    if original.is_symlink() or not original.is_file():
        raise SystemExit("ERROR: pinned source preparer unavailable")
    if derivative.parent != original.parent or derivative.exists() or derivative.is_symlink():
        raise SystemExit("ERROR: derived Repo preparer must be a new sibling")
    repo = original.parents[3]
    if repo.is_symlink():
        raise SystemExit("ERROR: unexpected vendor checkout symlink")
    rev = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    if rev != PIN:
        raise SystemExit("ERROR: source checkout does not match reviewed Kernarium commit")
    rel = original.relative_to(repo).as_posix()
    pristine = subprocess.check_output(["git", "-C", str(repo), "show", "HEAD:" + rel])
    if original.read_bytes() != pristine:
        raise SystemExit("ERROR: original vendor source preparer is dirty")
    script = pristine.decode("utf-8")
    if script.count(OLD_SYNC) != 1:
        raise SystemExit("ERROR: pinned Repo sync statement unexpectedly changed")
    # Ensure the reviewed pin manifest is rendered before synchronization.
    pin_anchor = '--output .repo/local_manifests/pin.xml'
    if script.find(pin_anchor) < 0 or script.find(pin_anchor) > script.find(OLD_SYNC):
        raise SystemExit("ERROR: pinned manifest render is missing or reordered")
    derived = script.replace(OLD_SYNC, NEW_SYNC, 1)
    derivative.write_text(derived, encoding="utf-8")
    derivative.chmod(0o755)
    audit.parent.mkdir(parents=True, exist_ok=True)
    audit.write_text(
        "KERNARIUM_COMMIT=" + rev + "\n" +
        "ORIGINAL_PREPARER_SHA256=" + hashlib.sha256(pristine).hexdigest() + "\n" +
        "DERIVED_PREPARER_SHA256=" + hashlib.sha256(derived.encode()).hexdigest() + "\n" +
        "POLICY=pinned_manifest;scoped_ConfigInfrastructure_prefetch;fail_fast;one_single_worker_retry\n",
        encoding="utf-8"
    )
    print("ANDARIUM_REPO_SYNC_DERIVED_PRODUCER_READY")
    print(audit.read_text(encoding="utf-8"))

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--original", required=True, type=Path)
    p.add_argument("--derived", required=True, type=Path)
    p.add_argument("--audit", required=True, type=Path)
    a = p.parse_args()
    create(a.original, a.derived, a.audit)
