# SPDX-License-Identifier: GPL-2.0-or-later
"""Mocked ADB integration contract; never touches a real user's theme."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import verify_guest


class LiveThemeContractTests(unittest.TestCase):
    def test_roundtrip_restores_existing_color(self):
        state = [0xF22B43]
        writes = []

        def adb(_tool, *argv):
            if "get" in argv:
                return f"Result: Bundle[{{rgb={state[0]}}}]"
            if "set" in argv:
                value = int(argv[-1].split(":")[-1])
                state[0] = value
                writes.append(value)
                return "Result: Bundle[{status=ok}]"
            raise AssertionError("Unexpected ADB call")

        with patch.object(verify_guest, "adb_run", side_effect=adb):
            detail = verify_guest.theme_roundtrip("adb")
        self.assertIn("restoration passed", detail)
        self.assertEqual(state[0], 0xF22B43)
        self.assertEqual(writes, [0xF22B42, 0xF22B43])

    def test_newer_theme_is_never_overwritten(self):
        state = [0x112233]
        reads = [0]
        writes = []

        def adb(_tool, *argv):
            if "get" in argv:
                reads[0] += 1
                if reads[0] == 4:
                    state[0] = 0x445566  # A newer user selection.
                return f"Result: Bundle[{{rgb={state[0]}}}]"
            if "set" in argv:
                state[0] = int(argv[-1].split(":")[-1])
                writes.append(state[0])
                return "Result: Bundle[{status=ok}]"
            raise AssertionError("Unexpected ADB call")

        with patch.object(verify_guest, "adb_run", side_effect=adb):
            with self.assertRaisesRegex(RuntimeError, "preserving newer color"):
                verify_guest.theme_roundtrip("adb")
        self.assertEqual(state[0], 0x445566)
        self.assertEqual(len(writes), 1)

    def test_malformed_readback_is_rejected(self):
        for value in ("Result: Bundle[{rgb=16777216}]", "Result: Bundle[{rgb=-1}]",
                      "Result: Bundle[{rgb=0,another=1}]", "not a bundle"):
            with self.subTest(value=value):
                with patch.object(verify_guest, "adb_run", return_value=value):
                    with self.assertRaises(ValueError):
                        verify_guest.read_theme_rgb("adb")

    def test_invalid_color_never_reaches_adb(self):
        with patch.object(verify_guest, "adb_run") as adb:
            with self.assertRaises(ValueError):
                verify_guest.write_theme_rgb("adb", 0x1000000)
            adb.assert_not_called()

    def test_no_false_ack_from_guest(self):
        with patch.object(verify_guest, "adb_run", return_value="Result: Bundle[{status=not_ready}]"):
            with self.assertRaises(RuntimeError):
                verify_guest.write_theme_rgb("adb", 0xF22B43)


if __name__ == "__main__":
    unittest.main()
