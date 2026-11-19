# SPDX-License-Identifier: GPL-2.0-or-later
"""Fail closed on Android guest package visibility and restricted intents.

These regression tests are source/stub checks, not Android 17 device tests.
"""
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
JAVA = ROOT / "launcher_src/java/dev/twoyi/redlauncher"


class AndroidIntentSafetyTests(unittest.TestCase):
    def test_all_three_navigation_surfaces_handle_restricted_intents(self):
        launcher = (JAVA / "MainActivity.java").read_text()
        native = (JAVA / "RedNativeDashboard.java").read_text()
        panels = (JAVA / "RedPanelActivity.java").read_text()
        self.assertIn("catch (SecurityException denied)", launcher)
        self.assertIn("catch (ActivityNotFoundException | SecurityException error)", launcher)
        self.assertIn("catch (ActivityNotFoundException | SecurityException denied)", native)
        self.assertIn("catch (ActivityNotFoundException | SecurityException e)", panels)
        self.assertIn("catch (ActivityNotFoundException | SecurityException ignored)", panels)

    def test_native_views_compile_with_restricted_intent_handlers(self):
        for tool, expected in [
            ("native_home_stub_compile.py", "NATIVE_HOME_JAVA_STUB_COMPILE_PASS"),
            ("android_panel_stub_compile.py", "RED_PANEL_JAVA_STUB_COMPILE_PASS"),
        ]:
            with self.subTest(tool=tool):
                result = subprocess.run(
                    [sys.executable, str(ROOT / "tools" / tool)],
                    capture_output=True, text=True, timeout=45,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(expected, result.stdout)


if __name__ == "__main__":
    unittest.main()
