# SPDX-License-Identifier: Apache-2.0
"""Host iOS chrome follows verified guest RGB (source-only contract)."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import install_source_overlay as overlay


class HostAccentChromeTests(unittest.TestCase):
    def test_clipboard_button_uses_observable_theme_instead_of_fixed_red(self):
        ui = (ROOT / "host/RedClipboardControls.swift").read_text()
        state = (ROOT / "host/RedHostAccentState.swift").read_text()
        self.assertIn("@ObservedObject private var accentState", ui)
        self.assertIn(".foregroundStyle(accentState.color)", ui)
        self.assertIn(".stroke(accentState.color.opacity", ui)
        self.assertNotIn(".foregroundStyle(.red)", ui)
        self.assertIn("0xF22B43", state)
        self.assertIn("guard selected <= 0x00FF_FFFF", state)

    def test_host_theme_only_changes_after_android_readback(self):
        upstream = (
            "    // MARK: Android operations\n"
            "    private var operations: AdbGuestOperations { fatalError() }\n"
        )
        changed = overlay.patch_guest_accent_runtime(upstream)
        index_readback = changed.index("RedGuestAccentTransport.verifyRead(")
        index_publish = changed.index("RedHostAccentState.shared.acceptVerified(rgb)")
        self.assertLess(index_readback, index_publish)
        self.assertEqual(overlay.patch_guest_accent_runtime(changed), changed)

    def test_source_stager_copies_required_theme_state(self):
        patcher = (ROOT / "install_source_overlay.py").read_text()
        self.assertIn("'RedHostAccentState.swift'", patcher)


if __name__ == "__main__":
    unittest.main()
