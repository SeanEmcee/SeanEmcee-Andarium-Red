# SPDX-License-Identifier: GPL-2.0-or-later
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from install_source_overlay import apply, patch_makefile, launcher_manifest
import install_source_overlay as overlay
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]

class OverlayTests(unittest.TestCase):
    def prep(self,root):
        a=root/'android/lineage-24/overlay/lineage_andarium.mk'; a.parent.mkdir(parents=True,exist_ok=True)
        a.write_text('PRODUCT_NAME := lineage_andarium\n')
        l=root/'android/lineage-24/metadata/lineage.env'; l.parent.mkdir(parents=True,exist_ok=True)
        l.write_text("LINEAGE24_ANDROID_MAJOR=17\nLINEAGE24_BUILD_VARIANT='user'\n")
        i=root/'Andarium/Andarium/Shared/AndariumApp.swift'; i.parent.mkdir(parents=True,exist_ok=True)
        i.write_text('import SwiftUI\n')
        live=root/'Andarium/Andarium/Live'
        live.mkdir(parents=True,exist_ok=True)
        (live/'AppEntry.swift').write_text('''struct Entry {
    func configure() {
        model.chosenScale = DisplayOptionsStore.load().chosenScale
        model.launchScale = launch.displayScale
    }
}
''')
        (live/'LiveRuntime.swift').write_text('''@MainActor
final class LiveRuntime {
    // MARK: Android operations
    private var operations: AdbGuestOperations { fatalError() }
    func reached() {
        if bootCompleted {
            partialSweep?.guestBooted()
        }
    }
    func reached() {
        if bootCompleted {
            partialSweep?.guestBooted()
        }
    }
}
''')
        (live/'SessionView.swift').write_text('''struct SessionView: View {
    var body: some View {
        content
            // The text message bar, over Android and above the keyboard.
            .overlay(alignment: .bottom) { TextMessageBarOverlay() }
    }
}
''')
        return a

    def test_manifest_explicit_package(self):
        m=(BASE/'launcher_src/AndroidManifest.xml').read_bytes()
        self.assertIn(b'package="dev.twoyi.redlauncher"',launcher_manifest(m))

    def test_dry_run_no_write(self):
        with tempfile.TemporaryDirectory() as x:
            r=Path(x); cfg=self.prep(r)
            result=apply(r,BASE/'launcher_src',None,True)
            self.assertFalse(result['changes_applied'])
            self.assertNotIn('TwoyiRedLauncher',cfg.read_text())

    def test_overlay_and_idempotent(self):
        with tempfile.TemporaryDirectory() as x:
            r=Path(x); cfg=self.prep(r)
            result=apply(r,BASE/'launcher_src',None,False)
            self.assertEqual(result['android'],17)
            self.assertTrue((r/'android/lineage-24/overlay/twoyi-red/launcher/Android.bp').exists())
            self.assertTrue((r/'android/lineage-24/overlay/twoyi-red/launcher/assets/home.png').exists())
            self.assertIn('TwoyiRedLauncher',cfg.read_text())
            apply(r,BASE/'launcher_src',None,False)
            self.assertEqual(cfg.read_text().count('PRODUCT_PACKAGES += TwoyiRedLauncher'),1)

    def test_android_version_fails_closed(self):
        with tempfile.TemporaryDirectory() as x:
            r=Path(x); self.prep(r)
            (r/'android/lineage-24/metadata/lineage.env').write_text('LINEAGE24_ANDROID_MAJOR=13\n')
            with self.assertRaisesRegex(ValueError,'not pinned to Android 17'):
                apply(r,BASE/'launcher_src',None,False)

    def test_diagnostic_variant_requires_opt_in(self):
        with tempfile.TemporaryDirectory() as x:
            r=Path(x); self.prep(r)
            before=(r/'android/lineage-24/metadata/lineage.env').read_text()
            result=apply(r,BASE/'launcher_src',None,True,'userdebug')
            self.assertTrue(result['diagnostic_build_not_releasable'])
            self.assertEqual(before,(r/'android/lineage-24/metadata/lineage.env').read_text())
            apply(r,BASE/'launcher_src',None,False,'userdebug')
            self.assertIn("LINEAGE24_BUILD_VARIANT='userdebug'",(r/'android/lineage-24/metadata/lineage.env').read_text())
            self.assertFalse(result['guest_root_enabled'])

    def test_diagnostic_variant_fails_if_not_known(self):
        with tempfile.TemporaryDirectory() as x:
            r=Path(x); self.prep(r)
            (r/'android/lineage-24/metadata/lineage.env').write_text('LINEAGE24_ANDROID_MAJOR=17\n')
            with self.assertRaisesRegex(ValueError,'pinned LineageOS build variant'):
                apply(r,BASE/'launcher_src',None,False,'userdebug')


class OptionalMagiskTests(unittest.TestCase):
    prep = OverlayTests.prep
    def test_magisk_staging_preserves_bytes_and_signature(self):
        import hashlib, zipfile
        with tempfile.TemporaryDirectory() as x:
            r=Path(x); cfg=self.prep(r)
            apk=r/'manager.apk'
            with zipfile.ZipFile(apk,mode='w') as z:
                z.writestr('AndroidManifest.xml',b'\x03\x00test-fixture-manifest')
                z.writestr('META-INF/test-signature',b'fixture-only')
            with patch.object(overlay,'MAGISK_RELEASE_SIZE',apk.stat().st_size), patch.object(overlay,'MAGISK_RELEASE_SHA256',hashlib.sha256(apk.read_bytes()).hexdigest()):
                result=apply(r,BASE/'launcher_src',apk,False)
            dest=r/'android/lineage-24/overlay/twoyi-red/magisk'
            self.assertEqual((dest/'Magisk.apk').read_bytes(),apk.read_bytes())
            self.assertIn('presigned: true',(dest/'Android.bp').read_text())
            self.assertIn('preprocessed: true',(dest/'Android.bp').read_text())
            self.assertNotIn('certificate:',(dest/'Android.bp').read_text())
            self.assertEqual(result['magisk_apk']['sha256'], hashlib.sha256(apk.read_bytes()).hexdigest())
            self.assertIn('PRODUCT_PACKAGES += TwoyiRedMagiskManager',cfg.read_text())
            self.assertFalse(result['guest_root_enabled'])

    def test_magisk_requires_apk_manifest(self):
        import zipfile
        with tempfile.TemporaryDirectory() as x:
            r=Path(x); cfg=self.prep(r)
            bad=r/'not-apk.zip'
            with zipfile.ZipFile(bad,'w') as z:z.writestr('readme.txt','nothing')
            with patch.object(overlay,'MAGISK_RELEASE_SIZE',bad.stat().st_size), patch.object(overlay,'MAGISK_RELEASE_SHA256',__import__('hashlib').sha256(bad.read_bytes()).hexdigest()):
                with self.assertRaisesRegex(ValueError,'Missing AndroidManifest.xml'):
                    apply(r,BASE/'launcher_src',bad,False)
            self.assertNotIn('TwoyiRedMagiskManager',cfg.read_text())


class VerificationTests(unittest.TestCase):
    def test_reject_nonofficial_magisk_content(self):
        with tempfile.TemporaryDirectory() as x:
            p=Path(x)/'Magisk-v31.1.apk'
            p.write_bytes(b'not a real magisk apk')
            with self.assertRaisesRegex(ValueError,'size/SHA-256'):
                overlay.validate_apk(p)


class DesignAssetTests(unittest.TestCase):
    def test_preserve_three_exact_generated_images(self):
        from hashlib import sha256
        from PIL import Image
        expected = {
            'home.png':'5e998a1f650c6241a4c1c40cde5182d4263960a0749c2b9b6e0c4e1f07eaa687',
            'settings.png':'385f327af32a272e946fef66a175af00142991ed407756cbb836970243b37b52',
            'browser.png':'3302c693d585e351e9a3c5ad7a821b55167fd036d4c5ce7140c163c7cbdbc87f',
        }
        for name,digest in expected.items():
            p=BASE/'launcher_src/assets'/name
            self.assertEqual(sha256(p.read_bytes()).hexdigest(),digest)
            with Image.open(p) as im:self.assertEqual(im.size,(863,1822))

if __name__ == "__main__":
    unittest.main()
