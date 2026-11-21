# SPDX-License-Identifier: GPL-2.0-or-later
"""Opt-in guest data persistence acceptance: fixture never touches real Android."""
import re
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import verify_guest


class PersistenceMarkerTests(unittest.TestCase):
    def test_new_guest_marker_is_readable(self):
        state = {}
        def fake_adb(_adb, *args):
            if args[:2] == ("sh", "-c"):
                cmd = args[-1]
                match = re.search(r"printf %s ([0-9a-f]{32}) >", cmd)
                if match is None:
                    raise AssertionError("Unexpected shell command")
                state["token"] = match.group(1)
                return ""
            if args[0] == "cat":
                self.assertEqual(args[1], verify_guest.PERSISTENCE_FILE)
                return state["token"]
            raise AssertionError("Unexpected ADB command")
        with patch.object(verify_guest, "adb_run", side_effect=fake_adb):
            token = verify_guest.create_persistence_marker("adb")
            self.assertRegex(token, r"^[0-9a-f]{32}$")
            self.assertIn("Guest data marker preserved",
                          verify_guest.verify_persistence_marker("adb", token))

    def test_mismatch_is_not_reported_as_preserved_data(self):
        with patch.object(verify_guest, "adb_run", return_value="0" * 32):
            with self.assertRaisesRegex(AssertionError, "did not retain"):
                verify_guest.verify_persistence_marker("adb", "1" * 32)

    def test_invalid_supplied_token_never_runs_shell(self):
        with patch.object(verify_guest, "adb_run") as runner:
            for value in ("", "abc", "A" * 32, "0" * 31 + ";", "0" * 33):
                with self.subTest(value=value):
                    with self.assertRaises(ValueError):
                        verify_guest.verify_persistence_marker("adb", value)
            runner.assert_not_called()


if __name__ == "__main__":
    unittest.main()
