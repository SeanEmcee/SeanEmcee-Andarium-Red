# SPDX-License-Identifier: GPL-2.0-or-later
"""The offline source checker can never certify an unbuilt Android runtime."""
from contextlib import redirect_stdout
from io import StringIO
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import prebuild_validate_v16 as validation
import prebuild_parity as source_parity


class PrebuildValidatorTests(unittest.TestCase):
    def test_command_roster_has_no_app_build_or_actions(self):
        roster = validation.commands()
        names = " ".join(name for name, _, _ in roster)
        self.assertIn("Python regression suite", names)
        self.assertIn("Android RGB provider permission behavior", names)
        for _, argv, _ in roster:
            self.assertNotIn("xcodebuild", argv)
            self.assertNotIn("gradle", argv)
            self.assertNotIn("gh", argv)
            self.assertNotIn("swift build", " ".join(argv))

    def test_prebuild_command_must_require_every_source_gate(self):
        gate_commands = [argv for label, argv, _ in validation.commands()
                         if label == "Evidence-based source gates"]
        self.assertEqual(len(gate_commands), 1)
        self.assertIn("--require-source-ready", gate_commands[0])
        self.assertNotIn("--require-release-go", gate_commands[0])

    def test_source_gate_exits_nonzero_when_any_source_check_fails(self):
        fixture = {
            "source_checks_passed": 44,
            "source_checks_total": 45,
            "release_gate": "NO-GO",
        }
        with redirect_stdout(StringIO()), \\
             patch.object(source_parity, "inspect", return_value=fixture), \\
             patch.object(sys, "argv", ["prebuild_parity.py", "--require-source-ready"]):
            with self.assertRaises(SystemExit) as caught:
                source_parity.main()
            self.assertEqual(caught.exception.code, 1)

    def test_partial_run_does_not_claim_complete_coverage(self):
        with redirect_stdout(StringIO()), \\
             patch.object(validation, "commands", return_value=[
                 ("one", ["true"], 5), ("two", ["true"], 5)
             ]), \\
             patch.object(validation.subprocess, "run", return_value=SimpleNamespace(
                 returncode=0, stdout="pass", stderr=""
             )):
            with tempfile.TemporaryDirectory() as td:
                report_path = Path(td) / "partial.json"
                self.assertEqual(validation.run(only="one", report=report_path), 0)
                report = json.loads(report_path.read_text())
                self.assertEqual(report["checks_attempted"], 1)
                self.assertEqual(report["checks_configured"], 2)
                self.assertIn("FILTERED", report["check_scope"])
                self.assertEqual(report["release_gate"], "NO-GO")

    def test_green_source_tests_still_report_release_no_go(self):
        with tempfile.TemporaryDirectory() as d, redirect_stdout(StringIO()):
            dest = Path(d) / "source.json"
            with patch.object(validation, "commands", return_value=[("fixture", ["true"], 5)]), \
                 patch.object(validation.subprocess, "run", return_value=SimpleNamespace(
                     returncode=0, stdout="pass", stderr="")):
                self.assertEqual(validation.run(report=dest), 0)
            report = json.loads(dest.read_text())
            self.assertTrue(report["source_checks_passed"])
            self.assertEqual(report["release_gate"], "NO-GO")
            self.assertEqual(report["runtime_acceptance"], "UNVERIFIED")

    def test_red_source_tests_fail_closed(self):
        with redirect_stdout(StringIO()), \
             patch.object(validation, "commands", return_value=[("fixture", ["false"], 5)]), \
             patch.object(validation.subprocess, "run", return_value=SimpleNamespace(
                 returncode=2, stdout="", stderr="failed")):
            self.assertEqual(validation.run(), 1)


if __name__ == "__main__":
    unittest.main()
