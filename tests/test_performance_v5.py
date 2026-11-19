# SPDX-License-Identifier: GPL-2.0-or-later
import tempfile
import unittest
from pathlib import Path
from install_source_overlay import patch_native_resolution_default, aot_readiness, apply
from test_overlay import OverlayTests
BASE=Path(__file__).resolve().parents[1]

class NativeResolutionTests(unittest.TestCase):
    def test_selected_resolutions_preserved(self):
        source='model.chosenScale = DisplayOptionsStore.load().chosenScale\n'
        modified=patch_native_resolution_default(source)
        self.assertEqual(modified.strip(),
            'model.chosenScale = DisplayOptionsStore.load().chosenScale ?? .native')
    def test_reapply_stable(self):
        source='model.chosenScale = DisplayOptionsStore.load().chosenScale\n'
        self.assertEqual(patch_native_resolution_default(patch_native_resolution_default(source)),
                         patch_native_resolution_default(source))
    def test_fail_closed_if_upstream_changed(self):
        with self.assertRaisesRegex(ValueError,'resolution initializer changed'):
            patch_native_resolution_default('nothing matches')
    def test_apply_edits_host_and_preserves_heat(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);OverlayTests().prep(root)
            result=apply(root,BASE/'launcher_src',None,False)
            app=(root/'Andarium/Andarium/Live/AppEntry.swift').read_text()
            self.assertIn('chosenScale ?? .native',app)
            self.assertTrue(result['native_resolution_default'])
            self.assertTrue(result['thermal_frame_rate_safeguard_preserved'])
            apply(root,BASE/'launcher_src',None,False)
            self.assertEqual((root/'Andarium/Andarium/Live/AppEntry.swift').read_text().count('?? .native'),1)
    def test_dry_run_not_modified(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);OverlayTests().prep(root)
            path=root/'Andarium/Andarium/Live/AppEntry.swift'
            before=path.read_bytes()
            result=apply(root,BASE/'launcher_src',None,True)
            self.assertEqual(path.read_bytes(),before)
            self.assertTrue(result['native_resolution_default'])
    def test_aot_missing_not_success(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            report=aot_readiness(root)
            self.assertFalse(report['toolchain_sources_present'])
            self.assertFalse(report['archives_approved_in_descriptor'])
            self.assertFalse(report['active_on_device_verified'])
    def test_aot_sources_are_not_aot_runtime(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for p in ('tools/aot/rewrite.py','tools/aot/release_artifact.py',
                      'tools/aot/libraries.txt','darwin/cpu/arm64/aot/CMakeLists.txt'):
                f=root/p;f.parent.mkdir(parents=True,exist_ok=True);f.write_text('placeholder')
            report=aot_readiness(root)
            self.assertTrue(report['toolchain_sources_present'])
            self.assertFalse(report['archives_approved_in_descriptor'])
            self.assertFalse(report['compiled_native_aot_verified'])
    def test_aot_descriptor_is_not_device_proof(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            f=root/'android/lineage-24/metadata/accepted-aot.env'
            f.parent.mkdir(parents=True,exist_ok=True)
            f.write_text("LINEAGE24_ACCEPTED_AOT_ARCHIVES='yes'\n")
            report=aot_readiness(root)
            self.assertTrue(report['archives_approved_in_descriptor'])
            self.assertFalse(report['active_on_device_verified'])

if __name__=='__main__': unittest.main()
