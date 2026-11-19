# SPDX-License-Identifier: GPL-2.0-or-later
import subprocess
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

class ProgressTests(unittest.TestCase):
    def test_assets_not_decoded_on_launch(self):
        main=(ROOT/'launcher_src/java/dev/twoyi/redlauncher/MainActivity.java').read_text()
        creation=main.split('onCreate(Bundle state)',1)[1].split('onResume()',1)[0]
        self.assertIn('designs = new Bitmap[3]',creation)
        self.assertNotIn('readAsset(',creation)
        self.assertIn('Bitmap src = designForPreview(screen);',main)
        self.assertIn('designs[index] = readAsset(file);',main)

    def test_explicit_root_check_and_nonblocking_ui(self):
        main=(ROOT/'launcher_src/java/dev/twoyi/redlauncher/RedNativeDashboard.java').read_text()
        self.assertIn('checkRootOnUserTap()',main)
        self.assertIn('new Thread(() ->',main)
        self.assertIn('RedRootProbe.check(RedRootProbe.PROCESS_RUNNER)',main)
        self.assertIn('rootProbeRunning',main)
        probe=(ROOT/'launcher_src/java/dev/twoyi/redlauncher/RedRootProbe.java').read_text()
        self.assertIn('"0".equals(su.output.trim())',probe)
        self.assertIn('if (su.exit != 0',probe)
        self.assertNotIn('Runtime.getRuntime().exec("',probe)

    def test_root_probe_harness(self):
        p=subprocess.run([sys.executable,str(ROOT/'tools/root_probe_java_test.py')],text=True,capture_output=True)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn('RED_ROOT_PROBE_7_PASS',p.stdout)

    def test_installer_is_run_scoped_and_single_flight(self):
        host=(ROOT/'host_firstboot.py').read_text()
        self.assertIn('private var redInstallerActiveRun: GuestRunMark?',host)
        self.assertIn('guard redInstallerActiveRun != startedRun',host)
        self.assertIn('defer {',host)
        self.assertIn('APK absent from bundle:',host)

if __name__=='__main__':unittest.main()
