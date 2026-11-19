# SPDX-License-Identifier: GPL-2.0-or-later
import hashlib
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
import install_source_overlay as overlay

class HostGuestIntegrationTests(unittest.TestCase):
    def prep(self, root):
        import test_overlay
        return test_overlay.OverlayTests.prep(self, root)

    def test_installs_clipboard_both_sides(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = self.prep(root)
            result = overlay.apply(root, BASE/'launcher_src', None, False)
            self.assertIn(overlay.CLIPBOARD_MODULE, result['guest_modules'])
            self.assertTrue((root/'android/lineage-24/overlay/twoyi-red/clipboard/Android.bp').is_file())
            self.assertIn('TwoyiRedClipboard', cfg.read_text())
            host = root/'Andarium/Andarium/Live'
            self.assertIn('redClipboardShell', (host/'LiveRuntime.swift').read_text())
            self.assertIn('redProvisionHomeOnce()', (host/'LiveRuntime.swift').read_text())
            self.assertIn('RedClipboardControls(runtime: runtime)', (host/'SessionView.swift').read_text())
            self.assertTrue((host/'RedClipboardCodec.swift').is_file())
            self.assertTrue((host/'RedClipboardControls.swift').is_file())
            overlay.apply(root, BASE/'launcher_src', None, False)
            self.assertEqual((host/'LiveRuntime.swift').read_text().count('func redClipboardShell('),1)
            self.assertEqual((host/'LiveRuntime.swift').read_text().count('func redProvisionHomeOnce()'),1)
            self.assertEqual(cfg.read_text().count('PRODUCT_PACKAGES += TwoyiRedClipboard'),1)

    def test_dry_run_never_changes_host(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            self.prep(root)
            before=(root/'Andarium/Andarium/Live/LiveRuntime.swift').read_bytes()
            overlay.apply(root, BASE/'launcher_src', None, True)
            self.assertEqual(before, (root/'Andarium/Andarium/Live/LiveRuntime.swift').read_bytes())

    def test_mismatched_host_fails_without_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            cfg=self.prep(root)
            (root/'Andarium/Andarium/Live/SessionView.swift').write_text('changed upstream')
            with self.assertRaisesRegex(ValueError,'SessionView.swift'):
                overlay.apply(root,BASE/'launcher_src',None,False)
            self.assertNotIn('TwoyiRed',cfg.read_text())

    def test_guest_provider_privileged_and_shell_only(self):
        manifest=(BASE/'guest_clipboard/AndroidManifest.xml').read_text()
        bp=(BASE/'guest_clipboard/Android.bp').read_text()
        java=(BASE/'guest_clipboard/java/dev/twoyi/redclipboard/ClipboardBridgeProvider.java').read_text()
        self.assertIn('READ_CLIPBOARD_IN_BACKGROUND',manifest)
        self.assertIn('certificate: "platform"',bp)
        self.assertIn('privileged: true',bp)
        self.assertIn('Process.SHELL_UID',java)
        self.assertIn('Process.ROOT_UID',java)
        self.assertNotIn('INTERNET',manifest)
        self.assertNotIn('OnPrimaryClipChangedListener',java)

    def test_titanium_sha256_and_import_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            cfg=self.prep(root)
            fake=root/'Titanium.apk'
            with zipfile.ZipFile(fake,'w') as z:
                z.writestr('AndroidManifest.xml','fixture only')
            with patch.object(overlay,'TITANIUM_RELEASE_SIZE',fake.stat().st_size),\
                 patch.object(overlay,'TITANIUM_RELEASE_SHA256',hashlib.sha256(fake.read_bytes()).hexdigest()):
                report=overlay.apply(root,BASE/'launcher_src',None,False,titanium_apk=fake)
                again=overlay.apply(root,BASE/'launcher_src',None,False)
            self.assertIsNotNone(report['titanium_apk'])
            self.assertEqual((root/'android/lineage-24/overlay/twoyi-red/titanium/Titanium.apk').read_bytes(),fake.read_bytes())
            self.assertIn(overlay.TITANIUM_MODULE,again['guest_modules'])
            self.assertEqual(cfg.read_text().count('PRODUCT_PACKAGES += TwoyiRedTitaniumBrowser'),1)

    def test_titanium_rejects_unverified(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'unknown.apk'
            p.write_bytes(b'not official')
            with self.assertRaisesRegex(ValueError,'size'):
                overlay.validate_titanium(p)

if __name__=='__main__':
    unittest.main()
