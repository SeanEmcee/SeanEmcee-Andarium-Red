# SPDX-License-Identifier: GPL-2.0-or-later
"""Source + compiled Swift coverage for prebuild RGB handoff to Android."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import install_source_overlay as overlay


class GuestAccentTransportTests(unittest.TestCase):
    def test_transport_injected_once_into_host(self):
        upstream = (
            "    // MARK: Android operations\n"
            "    private var operations: AdbGuestOperations { fatalError() }\n"
        )
        patched = overlay.patch_guest_accent_runtime(upstream)
        self.assertIn("func redApplyAccentRGB(_ rgb: UInt32) async throws", patched)
        self.assertIn("RedGuestAccentTransport.command(rgb: rgb)", patched)
        self.assertIn("operations.shell(command, limit: .seconds(15))", patched)
        self.assertEqual(overlay.patch_guest_accent_runtime(patched), patched)

    def test_rejects_changed_host_interface(self):
        with self.assertRaisesRegex(ValueError, "Android operations"):
            overlay.patch_guest_accent_runtime("unrelated source")

    def test_compiled_swift_rgb_command_validator(self):
        with tempfile.TemporaryDirectory() as td:
            binary = Path(td) / "red-accent"
            result = subprocess.run(
                ["swiftc", "-parse-as-library",
                 str(ROOT / "host/RedGuestAccentTransport.swift"),
                 str(ROOT / "tests/SwiftGuestAccentHarness.swift"),
                 "-o", str(binary)],
                capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=15)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn("GUEST_ACCENT_SWIFT_8_PASS", run.stdout)


if __name__ == "__main__":
    unittest.main()
