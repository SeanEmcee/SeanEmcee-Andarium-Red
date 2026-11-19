# SPDX-License-Identifier: GPL-2.0-or-later
from __future__ import annotations
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'tools'))
import host_firstboot as firstboot
import integrate_andarium as integration
import prebuild_parity
import aot_artifact_pipeline as aot
import root_readiness
import test_overlay

class V8PreBuildTests(unittest.TestCase):
    def test_heliboard_official_release_pin(self):
        swift=(ROOT/'host/RedGuestApkInstaller.swift').read_text()
        self.assertIn(firstboot.HELIBOARD_RELEASE_SHA256,swift)
        self.assertIn('helium314.keyboard',swift)
        self.assertEqual(firstboot.HELIBOARD_RELEASE_SIZE,22_431_797)
        self.assertIn('v4.2/HeliBoard_4.2-release.apk',firstboot.HELIBOARD_RELEASE_URL)

    def test_heliboard_rejects_fake_apk(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'HeliBoard.apk'
            with zipfile.ZipFile(p,'w') as z:z.writestr('AndroidManifest.xml',b'test')
            with self.assertRaisesRegex(ValueError,'size'):
                firstboot.validate_heliboard(p)

    def test_combined_heliboard_input_is_apk_pinned(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            test_overlay.OverlayTests.prep(self,root)
            project=root/'Andarium/Andarium.xcodeproj/project.xcproj'
            project.parent.mkdir(parents=True,exist_ok=True)
            project.write_text('{"files": [\n'+firstboot.PROJECT_ANCHOR+'\n]}')
            fake=root/'fixture.apk'
            with zipfile.ZipFile(fake,'w') as z:z.writestr('AndroidManifest.xml',b'fixture')
            with patch.object(firstboot,'validate_heliboard',return_value={'official':True}):
                report=integration.integrate(root,ROOT,heliboard=fake,dry_run=True)
            self.assertIn('HeliBoard-v4.2-release.apk',report['firstboot']['input_apks'])
            self.assertFalse(report['source_patches_applied'])

    def test_heliboard_visible_in_real_settings(self):
        native=(ROOT/'launcher_src/java/dev/twoyi/redlauncher/RedPanelActivity.java').read_text()
        manifest=(ROOT/'launcher_src/AndroidManifest.xml').read_text()
        self.assertIn('helium314.keyboard',native)
        self.assertIn('Settings.ACTION_INPUT_METHOD_SETTINGS',native)
        self.assertIn('android:name=".RedPanelActivity"',manifest)
        self.assertIn('android:exported="false"',manifest)

    def test_real_red_settings_is_not_image_only(self):
        source=(ROOT/'launcher_src/java/dev/twoyi/redlauncher/RedPanelActivity.java').read_text()
        self.assertIn('buildSettings()',source)
        self.assertIn('buildBrowser()',source)
        self.assertIn('Settings.ACTION_ACCESSIBILITY_SETTINGS',source)
        self.assertIn('new Intent(Intent.ACTION_VIEW, uri)',source)
        self.assertIn('isInstalled(TITANIUM_PACKAGE)',source)
        self.assertNotIn('rootVerified = true',source)

    def test_link_policy_compiles_and_rejects_unsafe_urls(self):
        with tempfile.TemporaryDirectory() as temp:
            src=ROOT/'launcher_src/java/dev/twoyi/redlauncher/PanelLinkPolicy.java'
            harness=ROOT/'tests/PanelLinkPolicyHarness.java'
            c=subprocess.run(['javac','-d',temp,str(src),str(harness)],capture_output=True,text=True)
            self.assertEqual(c.returncode,0,c.stderr)
            r=subprocess.run(['java','-cp',temp,'PanelLinkPolicyHarness'],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr)
            self.assertIn('12/12',r.stdout)

    def test_aot_fails_without_real_release(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)
            with self.assertRaisesRegex(ValueError,'Missing upstream AOT source'):
                aot.plan(p,p,p,p/'aot-artifact')

    def test_aot_arguments_use_real_upstream_tool(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)
            for rel in aot.EXPECTED:
                q=p/rel;q.parent.mkdir(parents=True,exist_ok=True)
                q.write_text('LINEAGE24_ANDROID_MAJOR=17' if rel.endswith('lineage.env') else 'fixture')
            rel=p/'release';rel.mkdir()
            fsck=p/'fsck.erofs';fsck.write_text('fixture');fsck.chmod(0o755)
            commands=aot.plan(p,rel,fsck,p/'artifact',2)
            self.assertEqual(len(commands),3)
            self.assertIn('build',commands[0])
            self.assertIn('verify',commands[1])
            self.assertIn('describe',commands[2])
            self.assertIn('no',commands[2])

    def test_root_readiness_fails_without_source(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError,'source tree not present'):
                root_readiness.inspect(Path(temp))

    def test_root_modes_not_equivalent_to_magisk(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)
            a=p/'android/lineage-24/metadata/lineage.env';a.parent.mkdir(parents=True)
            b=p/'android/lineage-24/overlay/lineage_andarium.mk';b.parent.mkdir(parents=True)
            a.write_text("LINEAGE24_ANDROID_MAJOR=17\nLINEAGE24_BUILD_VARIANT='userdebug'")
            b.write_text('TARGET_NO_KERNEL_OVERRIDE := true\nifneq ($(TARGET_BUILD_VARIANT),user)\nWITH_SU := true\nendif')
            report=root_readiness.inspect(p)
            self.assertTrue(report['diagnostic_su_possible'])
            self.assertFalse(report['magisk_kernel_runtime_integrated'])
            self.assertFalse(report['root_proven_in_guest'])

    def test_prebuild_gate_still_no_go(self):
        report=prebuild_parity.inspect()
        self.assertEqual(report['release_gate'],'NO-GO')
        self.assertEqual(report['source_checks_passed'],report['source_checks_total'])
        self.assertGreater(report['source_checks_total'],17)
        self.assertIn('Play Store',str(report['runtime_gates']))

if __name__=='__main__':unittest.main()
