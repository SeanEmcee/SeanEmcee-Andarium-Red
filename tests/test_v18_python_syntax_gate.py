# SPDX-License-Identifier: Apache-2.0
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import python_syntax_gate as gate


class SyntaxGateTests(unittest.TestCase):
    def test_current_python_sources_parse(self):
        report = gate.inspect()
        self.assertTrue(report["passed"], report["issues"])
        self.assertGreater(report["files_checked"], 15)

    def test_detects_unterminated_python_literal(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "bad.py").write_text("value = 'unterminated\n")
            report = gate.inspect(root)
            self.assertFalse(report["passed"])
            self.assertIn("bad.py", str(report["issues"]))

    def test_detects_duplicate_android_verifier_functions(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            f = root / "tools/verify_guest.py"
            f.parent.mkdir()
            f.write_text(
                "def adb_run(): pass\n"
                "def adb_run(): pass\n"
                "if __name__ == '__main__': pass\n"
            )
            report = gate.inspect(root)
            self.assertFalse(report["passed"])
            self.assertIn("adb_run must be defined once", str(report["issues"]))


if __name__ == "__main__":
    unittest.main()
