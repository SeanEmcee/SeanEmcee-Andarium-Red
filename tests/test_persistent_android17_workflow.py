#!/usr/bin/env python3
"""Build-system contract checks, not an emulator or image test."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
b=(root/"scripts/andarium_persistent_build.sh").read_text()
w=(root/".github/workflows/andarium-persistent-self-hosted.yml").read_text()
assert "runs-on: [self-hosted, linux, x64, andarium-aosp17]" in w
assert "timeout-minutes: 6600" in w
assert "cancel-in-progress: false" in w
assert w.index("andarium_persistent_build.sh prepare") < w.index("andarium_persistent_build.sh compile")
assert "--source-checkpoint-only" in b and "--use-prepared-source" in b
assert "ANDARIUM_RESUMING_PERSISTENT_OUT" in b
assert "download_verified_kernel_circleci.py" in b
assert "verify_red_android17_guest.py" in b
assert "check_source" in b
assert "flock -n 9" in b
assert "git -C \"$kernarium\" rev-parse HEAD" in b
assert "PERSISTENT" in b
assert 'rm -rf "$source_root"' not in b
print("PASS: persistent Android17 build source and Ninja output retention contract")
