#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""v16 source contracts: configurable UI + reproducible build. NOT device proof."""
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ConfigurableFirstBuildTests(unittest.TestCase):
    def test_reference_home_is_default_but_switchable(self):
        src = (ROOT / "launcher_src/java/dev/twoyi/redlauncher/MainActivity.java").read_text()
        self.assertIn('getInt(HOME_STYLE_KEY, 1) == 1', src)
        self.assertIn('private void setHomeStyle(boolean reference, boolean persist)', src)
        self.assertIn('.putInt(HOME_STYLE_KEY, reference ? 1 : 0).apply()', src)
        self.assertIn("Use exact-reference layout", src)
        self.assertIn("Use lightweight native layout", src)
        self.assertIn('skin = new SkinView()', src)
        self.assertIn('dashboard = new RedNativeDashboard(this)', src)

    def test_mockup_settings_is_interactive(self):
        src = (ROOT / "launcher_src/java/dev/twoyi/redlauncher/MainActivity.java").read_text()
        self.assertIn('else if(screen==SETTINGS) settingsTap(xx,yy)', src)
        self.assertIn('else browserTap(xx,yy)', src)
        self.assertIn('screen = SETTINGS; skin.invalidate()', src)
        self.assertIn('safeAction(actions[index])', src)

    def test_design_root_only_verified_on_request(self):
        src = (ROOT / "launcher_src/java/dev/twoyi/redlauncher/MainActivity.java").read_text()
        self.assertIn('private void checkRootOnUserTap()', src)
        self.assertIn('RedRootProbe.check(RedRootProbe.PROCESS_RUNNER)', src)
        self.assertIn('rootVerified = result.root && result.magisk', src)
        self.assertIn('if (rootCheckRunning) return;', src)
        startup = src.split('@Override public void onCreate(Bundle state)', 1)[1].split(
            '@Override protected void onNewIntent', 1)[0]
        self.assertNotIn('checkRootOnUserTap()', startup)
        self.assertNotIn('RedRootProbe.check(', startup)

    def test_default_ram_mode_is_configurable_and_persistent(self):
        source = (ROOT / "host/RedMemoryChoices.swift").read_text()
        state = (ROOT / "host/RedMemoryPresetSettings.swift").read_text()
        self.assertIn('RedMemoryPresetStore.load()', source)
        self.assertIn('RedMemoryPresetStore.save(option)', source)
        self.assertIn('guest.memoryMiB = value(for:', source)
        self.assertIn('case deviceLimit', state)
        self.assertIn('return .quality', state)

    def test_first_build_script_parses_and_supports_real_image(self):
        script = ROOT / 'scripts/first_build.sh'
        p = subprocess.run(['bash', '-n', str(script)],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        src = script.read_text()
        self.assertIn('--with-apps', src)
        self.assertIn('fetch_official_apks.py', src)
        self.assertIn('audit_staged_apks.py', src)
        self.assertIn('--guest-proof', src)
        self.assertIn('--unsigned-proof', src)
        self.assertIn('CODE_SIGNING_ALLOWED=NO', src)
        self.assertNotIn('gh workflow run', src)
        help_ = subprocess.run(['bash', str(script), '--help'],
                               capture_output=True, text=True)
        self.assertEqual(help_.returncode, 0, help_.stderr)
        self.assertIn('--guest-proof DIRECTORY', help_.stdout)

    def test_first_build_rejects_invalid_options_before_mutation(self):
        script = ROOT / 'scripts/first_build.sh'
        bad = subprocess.run(['bash', str(script), '/nonexistent',
                              '--guest-proof', '/nonexistent'],
                             capture_output=True, text=True)
        self.assertNotEqual(bad.returncode, 0)
        self.assertIn('requires --build', bad.stderr)


if __name__ == '__main__':
    unittest.main()
