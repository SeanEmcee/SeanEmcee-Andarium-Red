# SPDX-License-Identifier: Apache-2.0
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from accent_store_behavior_test import run

class AccentBehaviorTests(unittest.TestCase):
    def test_store_persists_invalid_values_do_not_overwrite(self):
        run()

    def test_uses_native_launcher_and_native_panels(self):
        root=Path(__file__).resolve().parents[1]
        files={n:(root/'launcher_src/java/dev/twoyi/redlauncher'/n).read_text()
               for n in ('MainActivity.java','RedNativeDashboard.java','RedPanelActivity.java')}
        self.assertIn('RedAccentStore.acceptLaunchAccent(this, getIntent())',files['MainActivity.java'])
        self.assertIn('RedAccentStore.load(owner)',files['RedNativeDashboard.java'])
        self.assertIn('RedAccentStore.load(this)',files['RedPanelActivity.java'])
        self.assertNotIn('private static final int RED',files['RedNativeDashboard.java'])
        self.assertNotIn('private static final int ACCENT',files['RedPanelActivity.java'])

if __name__=='__main__':unittest.main()
