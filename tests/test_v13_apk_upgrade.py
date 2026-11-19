# SPDX-License-Identifier: GPL-2.0-or-later
import sys
import hashlib
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'tools'))
import host_firstboot as first
import audit_staged_apks as auditor


class UpgradeAuditTests(unittest.TestCase):
    def prepare(self, root):
        live=root/'Andarium/Andarium/Live'
        live.mkdir(parents=True)
        (live/'LiveRuntime.swift').write_text('''@MainActor
final class LiveRuntime {
    // MARK: Android operations
    private var operations: AdbGuestOperations { fatalError() }
    func reached() {
        if bootCompleted {
            partialSweep?.guestBooted()
        }
    }
}
''')
        project=root/'Andarium/Andarium.xcodeproj/project.xcproj'
        project.parent.mkdir(parents=True)
        project.write_text('{"files": [\n'+first.PROJECT_ANCHOR+'\n]}')
        apk=root/'apksource.apk'
        with zipfile.ZipFile(apk,'w') as z:
            z.writestr('AndroidManifest.xml',b'synthetic test fixture')
        return apk, project

    def make_bundle(self, root):
        apk, project=self.prepare(root)
        with patch.object(first,'validate_apk',return_value={'fixture':True}):
            first.stage(root,ROOT,apk,None)
        return apk,project

    def test_audit_detects_valid_fixture_using_consistent_metadata(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            apk, project=self.make_bundle(root)
            # Replace official Magisk descriptor for this synthetic test only.
            import hashlib
            digest=hashlib.sha256(apk.read_bytes()).hexdigest()
            swift=root/'Andarium/Andarium/Live/RedGuestApkInstaller.swift'
            src=swift.read_text().replace(first.METHOD_SIGNATURE,'')
            src=src.replace('expectedBytes: 10_679_283,\n                expectedSHA256: "89cefac0a318afa39fb3880c45c87b036c05bc1ebf02a7a715b7f8d7c26ac6e7"',
                            f'expectedBytes: {len(apk.read_bytes())},\n                expectedSHA256: "{digest}"')
            swift.write_text(src)
            with patch.object(first,'validate_apk',return_value={}):
                outcome=auditor.audit(root)
            self.assertTrue(outcome['source_apk_bundle_consistent'])
            self.assertFalse(outcome['guest_install_verified'])

    def test_xcode_group_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            apk,project=self.make_bundle(root)
            project.write_text(project.read_text().replace('Magisk-v31.1.apk','Unknown.apk'))
            with self.assertRaisesRegex(ValueError,'resources differ'):
                auditor.audit(root)

    def test_missing_swift_descriptor_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            self.make_bundle(root)
            swift=root/'Andarium/Andarium/Live/RedGuestApkInstaller.swift'
            swift.write_text('// empty')
            with self.assertRaisesRegex(ValueError,'no APK descriptors'):
                auditor.audit(root)

    def test_unpinned_extraneous_resource_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            self.make_bundle(root)
            (root/'Andarium/RedBundledAPKs/untrusted.apk').write_bytes(b'x')
            with self.assertRaisesRegex(ValueError,'Unrecognized staged'):
                auditor.audit(root)

    def test_preserves_custom_launcher_pin_on_later_apk_addition(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            apk,project=self.prepare(root)
            launcher=root/'red-home.apk'
            dex=bytearray(112)
            dex[:8]=b'dex\n039\x00'
            struct.pack_into('<III',dex,32,len(dex),112,0x12345678)
            with zipfile.ZipFile(launcher,'w') as archive:
                archive.writestr('AndroidManifest.xml',b'\x03\x00\x08\x00'+bytes(12))
                archive.writestr('classes.dex',bytes(dex))
            first.stage(root,ROOT,None,None,launcher=launcher)
            with patch.object(first,'validate_apk',return_value={}):
                first.stage(root,ROOT,apk,None)
            installed=(root/'Andarium/Andarium/Live/RedGuestApkInstaller.swift').read_text()
            self.assertIn(hashlib.sha256(launcher.read_bytes()).hexdigest(),installed)
            self.assertEqual(installed.count('Package(filename: "TwoyiRedLauncher.apk"'),1)
            self.assertIn('Magisk-v31.1.apk',project.read_text())
            self.assertIn('TwoyiRedLauncher.apk',project.read_text())

    def test_swift_descriptor_digest_mismatch_detected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            apk,project=self.make_bundle(root)
            # Official pin mismatch in synthetic fixture must remain NO-GO.
            with patch.object(first,'validate_apk',return_value={}):
                with self.assertRaisesRegex(ValueError,'Swift APK installer digest or size'):
                    auditor.audit(root)

    def test_project_group_rejects_duplicate_entries(self):
        project='{"files": [\n'+first.PROJECT_ANCHOR+'\n]}'
        one=first.patch_project(project,['Magisk-v31.1.apk'])
        duplicate=one.replace('      { "path": "Magisk-v31.1.apk", "target-membership": [ "Andarium/resources" ] }',
            '      { "path": "Magisk-v31.1.apk", "target-membership": [ "Andarium/resources" ] },\n'
            '      { "path": "Magisk-v31.1.apk", "target-membership": [ "Andarium/resources" ] }')
        with self.assertRaisesRegex(ValueError,'duplicate'):
            first.patch_project(duplicate,['Magisk-v31.1.apk'])

    def test_no_staged_bundle_is_not_claimed_ready(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            self.prepare(root)
            with self.assertRaisesRegex(ValueError,'missing a real APK'):
                auditor.audit(root)


if __name__=='__main__':unittest.main()
