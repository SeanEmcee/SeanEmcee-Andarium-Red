#!/usr/bin/env python3
"""Derive auditable CI-only vendor producer after exact upstream verification."""
import argparse
import hashlib
from pathlib import Path
import subprocess

ANCHOR = "\nSOONG_BUILD_GRAPH="
UPSTREAM_SHA = "fbe12ee72d195f0241c4fc24090a98b259026604"
# This verifier occurs both before compilation and after packaging.
FINAL_VERIFY = ('"$VERIFIER" --android-root "$ANDROID_ROOT" ' + chr(92)
                + '\n\t--aosp-source "$AOSP_SOURCE" --expect final')
RESTORE = """
# Restore pinned Soong files before the upstream final clean-source check.
python3 -B "$ANDARIUM_RED_MEMORY_PATCH_SCRIPT" restore --workspace "$AOSP_SOURCE"
trap - EXIT
"""
INSERT = """
# CI-only Soong host runtime instrumentation. All upstream integrity checks
# above must pass first. The original vendor script stays byte-identical.
test -f "$ANDARIUM_RED_MEMORY_PATCH_SCRIPT"
python3 -B "$ANDARIUM_RED_MEMORY_PATCH_SCRIPT" apply --workspace "$AOSP_SOURCE" --audit "$ANDARIUM_RED_MEMORY_AUDIT"
trap 'python3 -B "$ANDARIUM_RED_MEMORY_PATCH_SCRIPT" restore --workspace "$AOSP_SOURCE"' EXIT
"""

def create(original, derivative, audit):
    if original.is_symlink() or not original.is_file():
        raise SystemExit("ERROR: original pinned vendor script unavailable")
    if derivative.parent != original.parent or derivative.exists() or derivative.is_symlink():
        raise SystemExit("ERROR: derived vendor script must be a new sibling file")
    repo = original.parents[3]
    path = original.relative_to(repo).as_posix()
    upstream = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"],
                                       text=True).strip()
    if upstream != UPSTREAM_SHA:
        raise SystemExit("ERROR: expected the exact reviewed Kernarium commit")
    pristine = subprocess.check_output(["git", "-C", str(repo), "show", "HEAD:" + path])
    actual = original.read_bytes()
    if pristine != actual:
        raise SystemExit("ERROR: vendor script differs from the pinned Git commit")
    text = actual.decode("utf-8")
    verifier = 'python3 -B "$KERNEL_ARTIFACT_VERIFIER" --artifact "$KERNEL_ARTIFACT"'
    if text.count(ANCHOR) != 1 or text.find(verifier) < 0 or text.find(verifier) > text.find(ANCHOR):
        raise SystemExit("ERROR: unable to prove original verifiers precede instrumentation")
    if text.count(FINAL_VERIFY) != 2 or text.rfind(FINAL_VERIFY) <= text.find(ANCHOR):
        raise SystemExit("ERROR: final upstream source verifier missing or altered")
    first_compile = text.find('m -j"$JOBS"', text.find(ANCHOR))
    if first_compile < 0 or first_compile >= text.rfind(FINAL_VERIFY):
        raise SystemExit("ERROR: cannot prove compilation runs before final verification")
    changed = text.replace(ANCHOR, "\n" + INSERT + ANCHOR, 1)
    final = changed.rfind(FINAL_VERIFY)
    changed = changed[:final] + RESTORE + changed[final:]
    derivative.write_text(changed, encoding="utf-8")
    derivative.chmod(0o755)
    audit.parent.mkdir(parents=True, exist_ok=True)
    audit.write_text(
        "KERNARIUM_COMMIT=" + subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip() + "\n"
        + "ORIGINAL_SHA256=" + hashlib.sha256(actual).hexdigest() + "\n"
        + "CI_DERIVATIVE_SHA256=" + hashlib.sha256(changed.encode()).hexdigest() + "\n"
        + "PATCH_ORDER=initial_verifiers_then_host_memory_then_restored_pristine_final_verifier\n",
        encoding="utf-8")
    print("VERIFIED_PINNED_VENDOR_BUILD_DERIVATIVE_CREATED")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--original", required=True, type=Path)
    p.add_argument("--derived", required=True, type=Path)
    p.add_argument("--audit", required=True, type=Path)
    a = p.parse_args()
    create(a.original, a.derived, a.audit)
