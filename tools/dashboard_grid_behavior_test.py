#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Run responsive-layout arithmetic tests without compiling an Android app."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]

def run():
    with tempfile.TemporaryDirectory(prefix='red-grid-') as td:
        files = [
            ROOT / "launcher_src/java/dev/twoyi/redlauncher/DashboardGridPolicy.java",
            ROOT / "tests/DashboardGridPolicyHarness.java",
        ]
        compiled = subprocess.run(
            ["javac", "-d", td, *map(str, files)],
            capture_output=True, text=True, timeout=30
        )
        if compiled.returncode:
            raise RuntimeError(compiled.stderr)
        tested = subprocess.run(["java", "-cp", td, "dev.twoyi.redlauncher.DashboardGridPolicyHarness"],
                                capture_output=True, text=True, timeout=15)
        if tested.returncode:
            raise RuntimeError(tested.stdout + tested.stderr)
        print(tested.stdout.strip())

if __name__ == '__main__':
    run()
