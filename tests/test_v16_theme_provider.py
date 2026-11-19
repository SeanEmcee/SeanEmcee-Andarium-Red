# SPDX-License-Identifier: GPL-2.0-or-later
"""Check Android theme provider security, persistence and local Java behavior."""
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ThemeProviderTests(unittest.TestCase):
    def test_provider_declared_for_shell_only(self):
        manifest = (ROOT / "launcher_src/AndroidManifest.xml").read_text()
        provider = (ROOT / "launcher_src/java/dev/twoyi/redlauncher/RedThemeProvider.java").read_text()
        self.assertIn('android:name=".RedThemeProvider"', manifest)
        self.assertIn('android:permission="android.permission.DUMP"', manifest)
        self.assertIn("Binder.getCallingUid()", provider)
        self.assertIn("Process.SHELL_UID", provider)
        self.assertIn("RedAccentStore.acceptRGB", provider)
        self.assertIn('answer.putString("rgb"', provider)

    def test_compiled_java_provider_harness(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools/theme_provider_behavior_test.py")],
            capture_output=True, text=True, timeout=60
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("RED_THEME_PROVIDER_15_PASS", result.stdout)


if __name__ == "__main__":
    unittest.main()
