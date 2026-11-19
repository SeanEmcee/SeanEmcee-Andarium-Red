# SPDX-License-Identifier: Apache-2.0
"""No app build: protect upstream entrypoint, preserve real AndariumProcess."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import prepare_embedded_kernarium as embedded


ORIGINAL = """import SwiftUI
@main
final class AndariumApp: UIResponder, UIApplicationDelegate {
    func launch() {}
}

/// The entry, model and runtime of the process.
@MainActor
final class AndariumProcess {
    static let shared = AndariumProcess()
}
struct RootView {}
"""


class EmbeddedKernariumGuardTests(unittest.TestCase):
    def test_idempotent_and_leaves_real_runtime_types_available(self):
        patched, changed = embedded.prepare(ORIGINAL)
        self.assertTrue(changed)
        self.assertIn("#if !NEXARIS_EMBEDDED_ANDARIUM\n@main", patched)
        self.assertIn("#endif // !NEXARIS_EMBEDDED_ANDARIUM\n\n/// The entry", patched)
        self.assertIn("final class AndariumProcess", patched)
        self.assertIn("struct RootView", patched)
        self.assertEqual(embedded.prepare(patched), (patched, False))

    def test_unknown_upstream_structure_is_rejected(self):
        for content in ("import SwiftUI\n", ORIGINAL.replace("@main", ""), ORIGINAL + ORIGINAL):
            with self.subTest(content=content[:40]):
                with self.assertRaises(ValueError):
                    embedded.prepare(content)

    def test_dry_run_does_not_write_anything(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / embedded.APP
            m = root / embedded.METADATA
            p.parent.mkdir(parents=True)
            m.parent.mkdir(parents=True)
            p.write_text(ORIGINAL)
            m.write_text("LINEAGE24_ANDROID_MAJOR=17\n")
            result = embedded.inspect(root)
            self.assertFalse(result["source_changed"])
            self.assertFalse(result["source_guard_ready"])
            self.assertEqual(p.read_text(), ORIGINAL)
            self.assertEqual(result["release_gate"], "NO-GO")

    def test_explicit_apply_is_narrow_and_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / embedded.APP
            m = root / embedded.METADATA
            p.parent.mkdir(parents=True)
            m.parent.mkdir(parents=True)
            p.write_text(ORIGINAL)
            m.write_text("LINEAGE24_ANDROID_MAJOR=17\n")
            first = embedded.inspect(root, apply=True)
            self.assertTrue(first["source_changed"])
            self.assertTrue(first["source_guard_ready"])
            self.assertFalse(first["runtime_verified"])
            after = p.read_text()
            second = embedded.inspect(root, apply=True)
            self.assertFalse(second["source_changed"])
            self.assertEqual(p.read_text(), after)

    def test_reject_non_android_17_guest(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / embedded.APP
            m = root / embedded.METADATA
            p.parent.mkdir(parents=True)
            m.parent.mkdir(parents=True)
            p.write_text(ORIGINAL)
            m.write_text("LINEAGE24_ANDROID_MAJOR=16\n")
            with self.assertRaisesRegex(ValueError, "not declared Android 17"):
                embedded.inspect(root, apply=True)
            self.assertEqual(p.read_text(), ORIGINAL)


if __name__ == "__main__":
    unittest.main()
