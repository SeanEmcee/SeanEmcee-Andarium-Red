# SPDX-License-Identifier: GPL-2.0-or-later
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'tools'))
import host_firstboot as fb
import integrate_andarium as it
import prebuild_parity as parity
import test_overlay

class V7PrebuildTests(unittest.TestCase):
    def test_source_gate_is_explicit_no_go(self):
        report = parity.inspect()
        self.assertEqual(report['release_gate'],'NO-GO')
        self.assertEqual(report['source_checks_total'],report['source_checks_passed'])
        self.assertTrue(any(x['state']=='unverified' for x in report['runtime_gates']))

    def test_fail_closed_exit_code(self):
        proc = subprocess.run([sys.executable,str(ROOT/'tools/prebuild_parity.py'),
                               '--require-release-go'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        self.assertEqual(proc.returncode,2)

    def test_live_clock_and_battery_source_has_real_inputs(self):
        src=(ROOT/'launcher_src/java/dev/twoyi/redlauncher/MainActivity.java').read_text()
        self.assertIn('BatteryManager.EXTRA_LEVEL',src)
        self.assertIn('Intent.ACTION_BATTERY_CHANGED',src)
        self.assertIn('drawRealDeviceStatus(canvas',src)
        self.assertIn('SimpleDateFormat("HH:mm"',src)

    def test_missing_install_badge_uses_package_manager(self):
        src=(ROOT/'launcher_src/java/dev/twoyi/redlauncher/MainActivity.java').read_text()
        self.assertIn('refreshInstalledApps()',src)
        self.assertIn('getPackageInfo(name',src)
        self.assertIn('drawInstalledState',src)
        self.assertIn('Not installed',src)

    def test_live_status_helper_executes(self):
        with tempfile.TemporaryDirectory() as tmp:
            cp=subprocess.run(['javac','-d',tmp,str(ROOT/'launcher_src/java/dev/twoyi/redlauncher/HomeStatusFormat.java'),
                              str(ROOT/'tests/HomeStatusHarness.java')],capture_output=True,text=True)
            self.assertEqual(cp.returncode,0,cp.stderr)
            run=subprocess.run(['java','-cp',tmp,'HomeStatusHarness'],capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr)
            self.assertIn('5/5',run.stdout)

    def test_termux_rejects_wrong_digest_or_size(self):
        with tempfile.TemporaryDirectory() as tmp:
            apk=Path(tmp)/'Termux.apk'
            apk.write_bytes(b'not an official APK')
            with self.assertRaisesRegex(ValueError,'size'):
                fb.validate_termux(apk)
            self.assertEqual(len(fb.TERMUX_RELEASE_SHA256),64)

    def test_fdroid_rejects_wrong_digest_or_size(self):
        with tempfile.TemporaryDirectory() as tmp:
            apk=Path(tmp)/'FDroid.apk'
            apk.write_bytes(b'not an official APK')
            with self.assertRaisesRegex(ValueError,'size'):
                fb.validate_fdroid(apk)
            self.assertEqual(len(fb.FDROID_RELEASE_SHA256),64)

    def test_swift_has_identical_fdroid_and_termux_pins(self):
        swift=(ROOT/'host/RedGuestApkInstaller.swift').read_text()
        self.assertIn(fb.TERMUX_RELEASE_SHA256,swift)
        self.assertIn(fb.FDROID_RELEASE_SHA256,swift)
        self.assertIn('com.termux',swift)
        self.assertIn('org.fdroid.fdroid',swift)

    def test_combined_fdroid_termux_dry_run(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            test_overlay.OverlayTests.prep(self,root)
            project=root/'Andarium/Andarium.xcodeproj/project.xcproj'
            project.parent.mkdir(parents=True,exist_ok=True)
            project.write_text('{"files": [\n'+fb.PROJECT_ANCHOR+'\n]}')
            fake=root/'fixture.apk'
            with zipfile.ZipFile(fake,'w') as z:z.writestr('AndroidManifest.xml',b'fixture')
            with patch.object(fb,'validate_termux',return_value={'fixture':'termux'}), \
                 patch.object(fb,'validate_fdroid',return_value={'fixture':'fdroid'}):
                report=it.integrate(root,ROOT,termux=fake,fdroid=fake,dry_run=True)
            self.assertFalse(report['source_patches_applied'])
            self.assertIn('Termux-v0.118.3-arm64.apk',report['firstboot']['input_apks'])
            self.assertIn('FDroid-v2.0.1.apk',report['firstboot']['input_apks'])
            self.assertFalse((root/'Andarium/RedBundledAPKs').exists())

    def test_reference_artworks_pinned(self):
        report=parity.inspect()
        for gate in report['source_gates'][:3]:
            self.assertEqual(gate['state'],'source-ready')
            self.assertTrue(gate['evidence'].startswith('sha256='))

if __name__=='__main__':unittest.main()
