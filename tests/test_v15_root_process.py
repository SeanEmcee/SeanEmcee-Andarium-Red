# SPDX-License-Identifier: GPL-2.0-or-later
"""Regression for real subprocess stdout/stderr drainage in the root verifier.

The Java harness launches itself as a child, emits >200 KiB to a pipe,
and verifies that the bounded collector drains without hanging or treating
truncated output as evidence of root. This is not an Android runtime test.
"""
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RootProcessDrainTests(unittest.TestCase):
    def test_real_subprocess_never_deadlocks_on_full_output_pipe(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools/root_probe_java_test.py")],
            capture_output=True, text=True, timeout=45,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("RED_ROOT_PROBE_10_PASS", result.stdout)


if __name__ == "__main__":
    unittest.main()
