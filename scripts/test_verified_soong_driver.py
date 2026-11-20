#!/usr/bin/env python3
"""Offline regression: Soong runtime change is reverted before final verification."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile

helper_path = Path(__file__).with_name("create_verified_soong_build_driver.py")
spec = importlib.util.spec_from_file_location("driver", helper_path)
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)
with tempfile.TemporaryDirectory() as d:
    root = Path(d) / "Kernarium"
    original = root / "android/lineage-24/build/build-aosp.sh"
    original.parent.mkdir(parents=True)
    verifier = ('"$VERIFIER" --android-root "$ANDROID_ROOT" ' + chr(92)
                + '\n\t--aosp-source "$AOSP_SOURCE" --expect final\n')
    original.write_text(
        '#!/bin/bash\nset -euo pipefail\n'
        + verifier
        + 'python3 -B "$KERNEL_ARTIFACT_VERIFIER" --artifact "$KERNEL_ARTIFACT"\n'
        + 'SOONG_BUILD_GRAPH="$OUT_DIR/soong/build.ninja"\n'
        + 'm -j"$JOBS" target-files-package\n'
        + verifier + 'echo build complete\n', encoding="utf-8"
    )
    subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(root), "-c", "user.name=CI", "-c",
                    "user.email=ci@example.invalid", "commit", "-qm", "pinned"], check=True)
    driver.UPSTREAM_SHA = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    original_bytes = original.read_bytes()
    derived = original.with_name("build-aosp.andarium-host-ci.sh")
    audit = Path(d) / "audit.txt"
    driver.create(original, derived, audit)
    output = derived.read_text(encoding="utf-8")
    assert output.index('python3 -B "$KERNEL_ARTIFACT_VERIFIER"') < output.index(
        'python3 -B "$ANDARIUM_RED_MEMORY_PATCH_SCRIPT" apply')
    assert output.index('m -j"$JOBS"') < output.rfind(
        'python3 -B "$ANDARIUM_RED_MEMORY_PATCH_SCRIPT" restore')
    assert output.rfind('python3 -B "$ANDARIUM_RED_MEMORY_PATCH_SCRIPT" restore') < output.rfind(
        '"$VERIFIER" --android-root "$ANDROID_ROOT"')
    assert "trap - EXIT" in output
    assert original.read_bytes() == original_bytes
    subprocess.run(["bash", "-n", str(derived)], check=True)
    try:
        driver.create(original, derived, audit)
    except SystemExit:
        pass
    else:
        raise AssertionError("duplicate derivation was permitted")
print("PASS: initial pristine verification, Soong memory patch, clean restore, final pristine verification")
