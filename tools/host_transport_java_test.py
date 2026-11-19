#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Pure Java test of the host path receipt and strict trusted transport values.

This checks actual RedHostTransportStatus.java, not a mocked networking HAL.
Android provider/Activity APIs are additionally typechecked by
android_panel_stub_compile.py. Actual network migration remains a device test.
"""
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main() -> None:
    with tempfile.TemporaryDirectory(prefix="red-host-transport-") as folder:
        classes = Path(folder) / "classes"
        sources = [
            ROOT / "launcher_src/java/dev/twoyi/redlauncher/RedHostTransportStatus.java",
            ROOT / "tests/RedHostTransportStatusHarness.java",
        ]
        for cmd in (
            ["javac", "-d", str(classes), *map(str, sources)],
            ["java", "-cp", str(classes), "dev.twoyi.redlauncher.RedHostTransportStatusHarness"],
        ):
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=60)
            if result.returncode:
                raise SystemExit((result.stderr or result.stdout).strip())
            if cmd[0] == "java":
                if "RED_HOST_TRANSPORT_17_PASS" not in result.stdout:
                    raise SystemExit("Unexpected host transport behavior result: " + result.stdout)
                print(result.stdout.strip())

if __name__ == "__main__":
    main()
