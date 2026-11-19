# SPDX-License-Identifier: GPL-2.0-or-later
import hashlib
import sys
import tempfile
import unittest
import zipfile
import struct
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import host_firstboot as first

BASE = Path(__file__).resolve().parents[1]

class HostFirstBootTests(unittest.TestCase):
    @staticmethod
    def prep(root):
        folder = root/'Andarium/Andarium/Live'
        folder.mkdir(parents=True)
        host = folder/'LiveRuntime.swift'
        host.write_text('''@MainActor
final class LiveRuntime {
    var normalRun = true
    // MARK: Android operations
    private var operations: AdbGuestOperations { fatalError() }
    func reached() {
        if bootCompleted {
            partialSweep?.guestBooted()
        }
    }
}
''')
        project = root/'Andarium/Andarium.xcodeproj/project.xcproj'
        project.parent.mkdir(parents=True)
        project.write_text('{"files": [\n'+first.PROJECT_ANCHOR+'\n]}')
        return host,project

    @staticmethod
    def fixture(root):
        apk=root/'test-fixture.apk'
        with zipfile.ZipFile(apk,'w') as z:
            z.writestr('AndroidManifest.xml', 'fixture not executable')
        return apk

    def test_hooks_existing_android_runtime(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);host,project=self.prep(root)
            apk=self.fixture(root)
            with patch.object(first,'validate_apk',return_value={'fixture':'verified'}):
                result=first.stage(root,BASE,apk,None)
            self.assertTrue(result['changes_applied'])
            self.assertTrue((root/'Andarium/RedBundledAPKs/Magisk-v31.1.apk').exists())
            self.assertIn('installApk(at: url',host.read_text())
            self.assertIn('Task.isCancelled',host.read_text())
            self.assertIn('runMark == startedRun',host.read_text())
            self.assertIn('Magisk-v31.1.apk',project.read_text())
            self.assertIn('RedGuestApkInstaller.swift',(root/'Andarium/Andarium/Live/RedGuestApkInstaller.swift').as_posix())
            self.assertTrue((root/'Andarium/Andarium/Live/RedGuestApkInstaller.swift').exists())

    def test_dry_run_is_immutable(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);host,project=self.prep(root)
            apk=self.fixture(root)
            original=(host.read_bytes(),project.read_bytes())
            with patch.object(first,'validate_apk',return_value={}):
                result=first.stage(root,BASE,apk,None,dry_run=True)
            self.assertFalse(result['changes_applied'])
            self.assertEqual(original,(host.read_bytes(),project.read_bytes()))
            self.assertFalse((root/'Andarium/RedBundledAPKs').exists())

    def test_repeat_run_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);host,project=self.prep(root)
            apk=self.fixture(root)
            with patch.object(first,'validate_apk',return_value={}):
                first.stage(root,BASE,apk,None)
                first.stage(root,BASE,apk,None)
            self.assertEqual(host.read_text().count('private func redInstallBundledAppsAfterBoot()'),1)
            self.assertEqual(host.read_text().count('Task { [weak self] in await self?.redInstallBundledAppsAfterBoot() }'),1)
            self.assertEqual(project.read_text().count('"name": "Red Bundled APKs"'),1)

    def test_incremental_staging_preserves_old_files_and_adds_new_apps(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);host,project=self.prep(root)
            magisk=self.fixture(root)
            titanium=root/'second.apk'
            titanium.write_bytes(magisk.read_bytes()+b'2')
            with patch.object(first,'validate_apk',return_value={}),patch.object(first,'validate_titanium',return_value={}):
                first.stage(root,BASE,magisk,None)
                original=(root/'Andarium/RedBundledAPKs/Magisk-v31.1.apk').read_bytes()
                outcome=first.stage(root,BASE,None,titanium)
                self.assertEqual(original,(root/'Andarium/RedBundledAPKs/Magisk-v31.1.apk').read_bytes())
                self.assertEqual(titanium.read_bytes(),(root/'Andarium/RedBundledAPKs/Titanium-v157.apk').read_bytes())
                self.assertEqual(outcome['preserved_existing_apks'],['Magisk-v31.1.apk'])
                self.assertEqual(set(outcome['bundled_apks_after_update']), {'Magisk-v31.1.apk','Titanium-v157.apk'})
                self.assertEqual(project.read_text().count('"path": "Magisk-v31.1.apk"'),1)
                self.assertEqual(project.read_text().count('"path": "Titanium-v157.apk"'),1)
                repeat=first.stage(root,BASE,None,None)
                self.assertEqual(repeat['bundled_apks_after_update'],outcome['bundled_apks_after_update'])
                self.assertEqual(project.read_text().count('"name": "Red Bundled APKs"'),1)

    def test_rejects_conflicting_update_without_modifying_bundle(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);host,project=self.prep(root)
            old=self.fixture(root)
            different=root/'different.apk'
            different.write_bytes(old.read_bytes()+b'different valid release')
            with patch.object(first,'validate_apk',return_value={}):
                first.stage(root,BASE,old,None)
                original=(host.read_bytes(),project.read_bytes(),
                    (root/'Andarium/RedBundledAPKs/Magisk-v31.1.apk').read_bytes())
                with self.assertRaisesRegex(ValueError,'differs from requested file'):
                    first.stage(root,BASE,different,None)
                self.assertEqual(original,(host.read_bytes(),project.read_bytes(),
                    (root/'Andarium/RedBundledAPKs/Magisk-v31.1.apk').read_bytes()))

    def test_rejects_unknown_and_symlinked_existing_apks(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.prep(root)
            apk=self.fixture(root)
            with patch.object(first,'validate_apk',return_value={}):
                first.stage(root,BASE,apk,None)
                target=root/'Andarium/RedBundledAPKs'
                (target/'Unknown.apk').write_bytes(b'unknown')
                with self.assertRaisesRegex(ValueError,'unknown resource'):
                    first.stage(root,BASE,None,None)
                (target/'Unknown.apk').unlink()
                (target/'Magisk-v31.1.apk').unlink()
                (target/'Magisk-v31.1.apk').symlink_to(apk)
                with self.assertRaisesRegex(ValueError,'symlink'):
                    first.stage(root,BASE,None,None)

    def test_dry_run_incremental_does_not_write_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);host,project=self.prep(root)
            apk=self.fixture(root)
            titanium=root/'titanium.apk';titanium.write_bytes(apk.read_bytes()+b'B')
            with patch.object(first,'validate_apk',return_value={}),patch.object(first,'validate_titanium',return_value={}):
                first.stage(root,BASE,apk,None)
                before=(host.read_bytes(),project.read_bytes())
                outcome=first.stage(root,BASE,None,titanium,dry_run=True)
                self.assertFalse(outcome['changes_applied'])
                self.assertEqual(before,(host.read_bytes(),project.read_bytes()))
                self.assertFalse((root/'Andarium/RedBundledAPKs/Titanium-v157.apk').exists())

    def test_unknown_host_fails_before_modifying(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);host,project=self.prep(root)
            host.write_text('unknown host revision')
            before=project.read_bytes()
            apk=self.fixture(root)
            with patch.object(first,'validate_apk',return_value={}):
                with self.assertRaisesRegex(ValueError,'does not match'):
                    first.stage(root,BASE,apk,None)
            self.assertEqual(before,project.read_bytes())

    def test_dont_claim_host_install_provides_guest_root(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.prep(root)
            apk=self.fixture(root)
            with patch.object(first,'validate_apk',return_value={}):
                result=first.stage(root,BASE,apk,None,dry_run=True)
            self.assertFalse(result['guest_root_enabled'])
            self.assertTrue(result['image_rebuild_needed_for_clipboard_privilege'])

    def test_custom_launcher_is_pinned_and_home_provisioned(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);host,project=self.prep(root)
            launcher=root/'launcher.apk'
            # This is a *synthetic structural fixture*, not an installable app.
            dex=bytearray(112)
            dex[:8]=b'dex\n039\x00'
            struct.pack_into('<III',dex,32,len(dex),112,0x12345678)
            with zipfile.ZipFile(launcher,'w') as z:
                z.writestr('AndroidManifest.xml', b'\x03\x00\x08\x00'+bytes(12))
                z.writestr('classes.dex', bytes(dex))
            outcome=first.stage(root,BASE,None,None,launcher=launcher)
            installed=(root/'Andarium/Andarium/Live/RedGuestApkInstaller.swift').read_text()
            self.assertIn(hashlib.sha256(launcher.read_bytes()).hexdigest(),installed)
            self.assertIn('TwoyiRedLauncher.apk',installed)
            self.assertIn('cmd package set-home-activity dev.twoyi.redlauncher/.MainActivity',host.read_text())
            self.assertTrue((root/'Andarium/RedBundledAPKs/TwoyiRedLauncher.apk').exists())
            self.assertIn('TwoyiRedLauncher.apk',project.read_text())
            self.assertFalse(outcome['guest_root_enabled'])

    def test_reject_incomplete_launcher_fixture(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.prep(root)
            bad=self.fixture(root)  # manifest without DEX
            with self.assertRaisesRegex(ValueError,'compiled APK'):
                first.stage(root,BASE,None,None,launcher=bad)

    def test_upgrading_existing_rom_overlay_removes_home_race(self):
        original = ('    // MARK: Android operations\n'
                    '    private var operations: AdbGuestOperations { fatalError() }\n'
                    '    func reached() {\n'
                    '            partialSweep?.guestBooted()\n'
                    '            Task { [weak self] in await self?.redProvisionHomeOnce() }\n'
                    '    }\n')
        output = first.patch_live_runtime(original)
        self.assertNotIn('Task { [weak self] in await self?.redProvisionHomeOnce() }', output)
        self.assertEqual(output.count('Task { [weak self] in await self?.redInstallBundledAppsAfterBoot() }'), 1)

    def test_no_apks_is_error(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.prep(root)
            with self.assertRaisesRegex(ValueError,'Supply at least one'):
                first.stage(root,BASE,None,None)

    def test_package_project_layout_is_stable(self):
        project='"files": [\n'+first.PROJECT_ANCHOR+'\n]'
        patched=first.patch_project(project,['Magisk-v31.1.apk','Titanium-v157.apk'])
        self.assertIn('"path": "Andarium/RedBundledAPKs"',patched)
        self.assertEqual(patched.count('Andarium/resources'),3)
        self.assertEqual(first.patch_project(patched,['Magisk-v31.1.apk','Titanium-v157.apk']),patched)

if __name__=='__main__': unittest.main()
