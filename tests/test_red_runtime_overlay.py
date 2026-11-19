#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Source-level regression checks for the ANDD/memory overlay. These are not
iOS compile, Android boot, graphics FPS, or physical-device validation.
"""
import tempfile
import unittest
from pathlib import Path

import red_runtime_overlay as red


def fixture() -> dict[str, str]:
    # Minimal real upstream anchors; if Kernarium changes, the overlay still
    # fails closed when applied to the actual checkout.
    return {
        red.DISPLAY_CORE: """
public struct GuestDisplayLayout {
    public var pixelSize: CGSize { CGSize(width: width, height: height) }
}
""",
        red.DISPLAY_VIEW: """
struct GuestDisplayView {
    let scale: GuestDisplayScale
    /// What VoiceOver
    let accessibility: GuestDisplayAccessibility?
    func makeUIViewController() {
        view.scale = scale
    }
    func updateUIViewController() {
        view.scale = scale
    }
}
class GuestMetalView {
    var scale = GuestDisplayScale.points
    func reportLayout() {
        guard let screen = window?.screen,
              // SwiftUI supplies safe-area-excluded point bounds, which the
              // scale turns into guest pixels, fractional native scales
              // included.
              let layout = GuestDisplayLayout(
                  scale: scale, points: bounds.size, nativeScale: Double(screen.nativeScale)
              ) else { return }
        drawableSize = layout.pixelSize
    }
}
""",
        red.MODEL: """
    var chosenScale: GuestDisplayScale?
    var resolutionLayout: GuestDisplayLayout? { resolutionLayout(at: resolutionIndex) }
""",
        red.RESOLUTION: """
        let end = choices.end(at: model.resolutionIndex)
            subtitle: ResolutionWords.summary(layout: layout, end: end),
            spoken: ResolutionWords.spokenSummary(layout: layout, end: end),
                    model.screenDidChange(nativeScale: $0.nativeScale)
                    publish()
    var nativeScale = 1.0
            nativeScale: Double(scene.screen.nativeScale),
            topInset:
""",
        red.HOME: "case .resolution: ResolutionSheet()",
        red.GUEST_LAYER: """
            scale: model.resolution,
            accessibility: accessibility,
""",
        red.APP_ENTRY: "        model.chosenScale = DisplayOptionsStore.load().chosenScale",
        red.PREFERENCES:
            "        if let options = model.displayOptionsToKeep { DisplayOptionsStore.save(options, to: defaults) }",
        red.APP: "        model.screenDidChange(nativeScale: Double(scene.screen.nativeScale))",
        red.RULER: """
            memory
            if let vram = host.memory.graphicsMemoryMiB(
""",
        red.SHEETS: """
struct NewGuestSheet {
    var draftBinding = Guest.fresh(on: model.host)
    var draft = Guest.fresh(on: model.host)
}
struct SystemSheet: View {
    var current = Guest.fresh(on: model.host)
}
""",
    }


class RedRuntimeOverlayTests(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory()
        self.addCleanup(self.workspace.cleanup)
        self.root = Path(self.workspace.name) / "Kernarium"
        self.root.mkdir()
        self.source = Path(__file__).resolve().parents[1]
        for name, data in fixture().items():
            dest = self.root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(data)

    def test_dry_run_has_no_mutations(self):
        result = red.apply(self.root, self.source, dry_run=True)
        self.assertEqual(len(result["planned_host_edits"]), len(fixture()))
        self.assertFalse(result["applied"])
        self.assertFalse((self.root / "Andarium/Andarium/Shared/RedDisplayChoice.swift").exists())
        for name, data in fixture().items():
            self.assertEqual((self.root / name).read_text(), data)

    def test_apply_and_repeat_idempotently(self):
        first = red.apply(self.root, self.source, dry_run=False)
        self.assertTrue(first["applied"])
        patched = {name: (self.root / name).read_text() for name in fixture()}
        self.assertIn("redNativeOrientedPixelSize", patched[red.MODEL])
        self.assertIn("redPixelOverride", patched[red.DISPLAY_VIEW])
        self.assertIn("RedMemoryPresetRow", patched[red.RULER])
        self.assertIn("RedResolutionSheet()", patched[red.HOME])
        self.assertIn("redResolutionSetting", patched[red.APP_ENTRY])
        self.assertIn("nativePixels: scene.screen.nativeBounds.size", patched[red.RESOLUTION])
        for fname in red.ADD_SWIFT:
            self.assertEqual(
                (self.root / "Andarium/Andarium/Shared" / fname).read_bytes(),
                (self.source / "host" / fname).read_bytes())
        second = red.apply(self.root, self.source, dry_run=True)
        self.assertEqual(second["planned_host_edits"], [])
        red.apply(self.root, self.source, dry_run=False)
        self.assertEqual(
            {name: (self.root / name).read_text() for name in fixture()}, patched)

    def test_rejects_upstream_drift_without_partial_write(self):
        missing = self.root / red.DISPLAY_VIEW
        missing.write_text("Kernarium updated the renderer interface")
        before = (self.root / red.DISPLAY_CORE).read_text()
        with self.assertRaises(ValueError):
            red.apply(self.root, self.source, dry_run=False)
        self.assertEqual((self.root / red.DISPLAY_CORE).read_text(), before)

    def test_does_not_fake_a_success_without_full_source(self):
        (self.root / red.APP_ENTRY).unlink()
        self.assertFalse(red.is_complete_checkout(self.root))
        with self.assertRaises(ValueError):
            red.apply(self.root, self.source, dry_run=True)

    def test_retrofit_keeps_existing_user_resolution(self):
        text = red.patch_app_entry(
            "        model.chosenScale = DisplayOptionsStore.load().chosenScale")
        self.assertIn("existingRedMode = RedResolutionStore.load()", text)
        self.assertIn("redSavedDisplay.chosenScale != nil", text)
        self.assertEqual(red.patch_app_entry(text), text)

    def test_custom_pixel_dimensions_reach_drawable(self):
        patched = red.patch_display(fixture()[red.DISPLAY_VIEW])
        self.assertEqual(patched.count("view.redPixelOverride = redPixelOverride"), 2)
        self.assertIn("pixelWidth: Int(redPixelOverride.width)", patched)
        self.assertIn("drawableSize = layout.pixelSize", patched)
        self.assertIn("var redPixelOverride: CGSize? = nil", patched)
        self.assertEqual(red.patch_display(patched), patched)

    def test_memory_presets_keep_runtime_safety(self):
        source = (self.source / "host/RedMemoryChoices.swift").read_text()
        self.assertIn("safeMemoryMiB(vCPUs: cores)", source)
        self.assertIn("graphicsLineMiB(vCPUs: cores", source)
        self.assertIn("maximumMiB(vCPUs: cores)", source)
        self.assertIn("host.memory.risk(", source)

    def test_link_logic_and_independent_modes_present(self):
        source = (self.source / "host/RedDisplayChoice.swift").read_text()
        self.assertIn("if linked, newValue > 0", source)
        self.assertIn("ratioWidth", source)
        self.assertIn("ratioHeight", source)
        self.assertIn("func setLinked(_ on: Bool)", source)
        self.assertIn("maximumPixels = 16_777_216", source)


if __name__ == "__main__":
    unittest.main()
