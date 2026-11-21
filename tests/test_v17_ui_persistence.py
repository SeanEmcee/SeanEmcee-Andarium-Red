# SPDX-License-Identifier: Apache-2.0
"""Source contracts for visual updates that must not discard user input."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "launcher_src/java/dev/twoyi/redlauncher"


class NativeUIThemePersistenceTests(unittest.TestCase):
    def test_browser_keeps_in_progress_address_on_theme_change(self):
        source = (UI / "RedPanelActivity.java").read_text()
        self.assertIn("private EditText browserAddress;", source)
        self.assertIn("pendingBrowserAddress = browserAddress.getText().toString()", source)
        self.assertIn("address.setText(pendingBrowserAddress)", source)
        self.assertIn("unregisterOnSharedPreferenceChangeListener(themeObserver)", source)

    def test_launcher_relayouts_when_configuration_changes(self):
        source = (UI / "MainActivity.java").read_text()
        self.assertIn("onConfigurationChanged(Configuration c)", source)
        method = source[source.index("onConfigurationChanged(Configuration c)"):
                        source.index("private final class SkinView")]
        self.assertIn("dashboard.refresh()", method)
        self.assertIn("skin.invalidate()", method)


if __name__ == "__main__":
    unittest.main()
