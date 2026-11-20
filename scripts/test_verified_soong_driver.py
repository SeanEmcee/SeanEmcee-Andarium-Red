#!/usr/bin/env python3
"""Offline proof: pinned source verifies before Go runtime changes."""
from pathlib import Path
import subprocess
import sys
import tempfile

helper = Path(__file__).with_name("create_verified_soong_build_driver.py")
with tempfile.TemporaryDirectory() as d:
    root = Path(d)/"Kernarium"
    original = root/"android/lineage-24/build/build-aosp.sh"
    original.parent.mkdir(parents=True)
    original.write_text(
        '#!/bin/bash\nset -euo pipefail\nKERNEL_ARTIFACT_VERIFIER=/example\n'
        'KERNEL_ARTIFACT=/example\nAOSP_SOURCE=/example\n'
        'python3 -B "$KERNEL_ARTIFACT_VERIFIER" --artifact "$KERNEL_ARTIFACT"\n'
        'SOONG_BUILD_GRAPH="/example/build.ninja"\necho build\n',
        encoding="utf-8")
    subprocess.run(["git","-C",str(root),"init","-q"],check=True)
    subprocess.run(["git","-C",str(root),"add","."],check=True)
    subprocess.run(["git","-C",str(root),"-c","user.name=CI","-c","user.email=ci@example.invalid",
                    "commit","-qm","pinned"],check=True)
    raw=original.read_bytes()
    derived=original.with_name("build-aosp.andarium-host-ci.sh")
    args=[sys.executable,str(helper),"--original",str(original),"--derived",str(derived),
          "--audit",str(Path(d)/"audit.txt")]
    subprocess.run(args,check=True)
    text=derived.read_text()
    assert text.index('python3 -B "$KERNEL_ARTIFACT_VERIFIER"') < text.index('python3 -B "$ANDARIUM_RED_MEMORY_PATCH_SCRIPT" apply')
    assert text.index('python3 -B "$ANDARIUM_RED_MEMORY_PATCH_SCRIPT" apply') < text.index('SOONG_BUILD_GRAPH=')
    assert original.read_bytes()==raw
    subprocess.run(["bash","-n",str(derived)],check=True)
    assert subprocess.run(args,capture_output=True).returncode!=0
print("PASS: pinned vendor source intact, original checks first, host-only patch after")
