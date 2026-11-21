#!/usr/bin/env python3
"""Prevent a repeat of the expensive ZRAM pre-init-check failure."""
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
z=(ROOT/"scripts/provision_android17_zram_swap.sh").read_text()
w=(ROOT/".github/workflows/andarium-github-free-and-real.yml").read_text()
assert z.index("sudo modprobe zram") < z.index("if [[ ! -e /sys/class/zram-control/hot_add ]]")
assert 'ANDARIUM_ZRAM_KERNEL_MODULE_LOADED' in z
assert w.count("bash scripts/provision_android17_zram_swap.sh 16")==1
early=w.index("      - name: Load ZRAM module and enable 16 GiB")
preflight=w.index("      - name: Verify all 167+ source tests")
reclaim=w.index("      - name: Reclaim disk space")
sync=w.index("      - name: Synchronize genuine pinned Android 17")
assert preflight < early < reclaim < sync
assert "bash scripts/provision_android17_host_swap.sh 6" in w
assert "python3 -B scripts/android17_build_telemetry.py start" in w
assert "andarium-gh-kernarium-fbe12ee" in w
assert "andarium-gh-repo-object-seed-v1-" in w
print("PASS: modprobe precedes sysfs; 16GiB compressed swap checked before 100GiB AOSP sync")
