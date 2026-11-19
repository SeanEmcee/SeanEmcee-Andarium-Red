# SPDX-License-Identifier: GPL-2.0-or-later
"""Behavioral regression tests for v11, including upgrading an already patched host."""
from __future__ import annotations
import hashlib
import importlib.util
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'tools'))
import host_firstboot as first
import aot_artifact_pipeline as aot


def launcher_fixture(path: Path, *, binary_manifest: bool = True, dex_magic: bool = True) -> None:
    dex = bytearray(112)
    dex[:8] = b'dex\n039\x00' if dex_magic else b'NOT-DEX!'
    struct.pack_into('<III', dex, 32, len(dex), 112, 0x12345678)
    with zipfile.ZipFile(path, 'w') as archive:
        archive.writestr('AndroidManifest.xml', b'\x03\x00\x08\x00'+bytes(12)
                             if binary_manifest else b'<manifest/>')
        archive.writestr('classes.dex', dex)


class NativeInputCorrectnessTests(unittest.TestCase):
    def test_structurally_shaped_launcher_can_be_pinned(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'launcher.apk'
            launcher_fixture(path)
            report = first.verify_launcher(path)
            self.assertEqual(report['sha256'], hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertIn('verification', report['note'])

    def test_rejects_placeholder_dex_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'launcher.apk'
            launcher_fixture(path, dex_magic=False)
            with self.assertRaisesRegex(ValueError, 'compiled Android DEX'):
                first.verify_launcher(path)

    def test_rejects_text_manifest_in_zip(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'launcher.apk'
            launcher_fixture(path, binary_manifest=False)
            with self.assertRaisesRegex(ValueError, 'compiled binary AndroidManifest'):
                first.verify_launcher(path)

    def test_existing_v10_installer_replaced_without_duplicate_hooks(self):
        old = '''    // MARK: Android operations

''' + first.legacy_v10_install_method() + '''    private var operations: AdbGuestOperations { fatalError() }
    func reached() {
        partialSweep?.guestBooted()
        Task { [weak self] in await self?.redInstallBundledAppsAfterBoot() }
    }
'''
        new = first.patch_live_runtime(old)
        self.assertIn('redInstallerCompletedRun', new)
        self.assertEqual(new.count('private func redInstallBundledAppsAfterBoot()'), 1)
        self.assertEqual(new.count('Task { [weak self] in await self?.redInstallBundledAppsAfterBoot() }'), 1)
        self.assertEqual(first.patch_live_runtime(new), new)

    def test_v10_installer_with_owner_changes_fails_closed(self):
        edited=first.legacy_v10_install_method().replace('return }', 'return /* customization */ }', 1)
        content='    // MARK: Android operations\n\n'+edited+'    private var operations: AdbGuestOperations { fatalError() }\n'
        with self.assertRaisesRegex(ValueError,'local changes'):
            first.patch_live_runtime(content)

    def test_finished_run_does_not_rescan_package_bundle(self):
        self.assertIn('redInstallerCompletedRun != startedRun', first.INSTALL_METHOD)
        self.assertIn('redInstallerCompletedRun = startedRun', first.INSTALL_METHOD)
        self.assertIn('runMark == startedRun', first.INSTALL_METHOD)
        self.assertIn('normalRun && runMark == startedRun && !Task.isCancelled', first.INSTALL_METHOD)

    def test_aot_archive_candidate_is_opt_in(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for rel in aot.EXPECTED:
                path=root/rel;path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text('LINEAGE24_ANDROID_MAJOR=17' if rel.endswith('lineage.env') else 'fixture')
            release=root/'release';release.mkdir()
            fsck=root/'fsck.erofs';fsck.write_text('stub');fsck.chmod(0o755)
            normal=aot.plan(root,release,fsck,root/'aot')
            archive=aot.plan(root,release,fsck,root/'aot',archive_candidate=True)
            self.assertEqual(normal[2][-1], 'no')
            self.assertEqual(archive[2][-1], 'yes')
            self.assertFalse((root/'android/lineage-24/metadata/accepted-aot.env').exists())

    def test_swift_clipboard_protocol_adversarial_cases(self):
        with tempfile.TemporaryDirectory() as temp:
            exe=Path(temp)/'swiftclip'
            comp=subprocess.run(['swiftc',str(ROOT/'host/RedClipboardCodec.swift'),
                                 str(ROOT/'tests/SwiftClipboardHarness.swift'),'-o',str(exe)],
                                capture_output=True,text=True)
            self.assertEqual(comp.returncode,0,comp.stderr)
            run=subprocess.run([str(exe)],capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr)
            self.assertIn('malformed-output rejection',run.stdout)

    def test_android_provider_rejects_malformed_utf8(self):
        result=subprocess.run([sys.executable,str(ROOT/'tools/clipboard_provider_behavior_test.py')],
                              capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('10 assertions',result.stdout)


if __name__=='__main__':
    unittest.main()
