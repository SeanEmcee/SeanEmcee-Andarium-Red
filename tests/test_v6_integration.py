# SPDX-License-Identifier: GPL-2.0-or-later
import hashlib
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import integrate_andarium as integrate
import host_firstboot as firstboot
import test_overlay


class V6IntegrationTests(unittest.TestCase):
    def prepare(self, root):
        return test_overlay.OverlayTests.prep(self, root)

    def test_overlay_without_apks(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.prepare(root)
            result = integrate.integrate(root, ROOT)
            self.assertTrue(result['source_patches_applied'])
            self.assertIsNone(result['firstboot'])
            self.assertFalse(result['iphone_tested'])
            self.assertIn('TwoyiRedClipboard', (root/'android/lineage-24/overlay/lineage_andarium.mk').read_text())

    def test_combined_dry_run_does_not_mutate(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            cfg = self.prepare(root)
            before = cfg.read_bytes()
            result = integrate.integrate(root, ROOT, dry_run=True)
            self.assertFalse(result['source_patches_applied'])
            self.assertEqual(cfg.read_bytes(), before)
            self.assertFalse((root/'android/lineage-24/overlay/twoyi-red').exists())

    def test_combined_after_firstboot_fixture(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.prepare(root)
            (root/'Andarium/Andarium.xcodeproj').mkdir(parents=True)
            project = root/'Andarium/Andarium.xcodeproj/project.xcproj'
            project.write_text('{"files": [\n'+firstboot.PROJECT_ANCHOR+'\n]}')
            fake = root/'fake.apk'
            with zipfile.ZipFile(fake,'w') as z:
                z.writestr('AndroidManifest.xml',b'fixture')
            with patch.object(firstboot,'validate_apk',return_value={'fixture':True}):
                report = integrate.integrate(root, ROOT, magisk=fake)
            content = (root/'Andarium/Andarium/Live/LiveRuntime.swift').read_text()
            self.assertEqual(content.count('Task { [weak self] in await self?.redInstallBundledAppsAfterBoot() }'),1)
            self.assertNotIn('Task { [weak self] in await self?.redProvisionHomeOnce() }',content)
            self.assertIn('redClipboardShell',content)
            self.assertTrue(report['source_patches_applied'])
            self.assertFalse(report['magisk_root_verified'])

    def test_unknown_host_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            cfg=self.prepare(root)
            (root/'Andarium/Andarium/Live/SessionView.swift').write_text('unknown layout')
            with self.assertRaisesRegex(ValueError,'SessionView'):
                integrate.integrate(root, ROOT)
            self.assertNotIn('TwoyiRedLauncher', cfg.read_text())

    def test_official_appmanager_signature_pinned(self):
        swift = (ROOT/'host/RedGuestApkInstaller.swift').read_text()
        self.assertIn(firstboot.APPMANAGER_RELEASE_SHA256, swift)
        self.assertIn('io.github.muntashirakon.AppManager', swift)
        self.assertIn('AppManager-v4.1.1.apk',swift)
        self.assertIn('dev.twoyi.redlauncher', (ROOT/'launcher_src/java/dev/twoyi/redlauncher/MainActivity.java').read_text())
        with tempfile.TemporaryDirectory() as d:
            fake=Path(d)/'fake.apk'
            fake.write_bytes(b'fake')
            with self.assertRaisesRegex(ValueError,'size'):
                firstboot.validate_appmanager(fake)

    def test_java_catalog_real_compilation(self):
        with tempfile.TemporaryDirectory() as d:
            compile_ = subprocess.run(['javac','-d',d,
                  str(ROOT/'launcher_src/java/dev/twoyi/redlauncher/LauncherCatalog.java'),
                  str(ROOT/'tests/LauncherCatalogHarness.java')], capture_output=True,text=True)
            self.assertEqual(compile_.returncode,0,compile_.stderr)
            test = subprocess.run(['java','-cp',d,'LauncherCatalogHarness'],capture_output=True,text=True)
            self.assertEqual(test.returncode,0,test.stderr)
            self.assertIn('7/7',test.stdout)

    def test_launcher_non_deceptive(self):
        content = (ROOT/'launcher_src/java/dev/twoyi/redlauncher/MainActivity.java').read_text()
        self.assertIn('showAppDrawer("")',content)
        self.assertIn('LauncherCatalog.filter(launchableApps(), query)',content)
        self.assertIn('Root: not verified', (ROOT/'launcher_src/java/dev/twoyi/redlauncher/LauncherCatalog.java').read_text())

if __name__ == '__main__': unittest.main()
