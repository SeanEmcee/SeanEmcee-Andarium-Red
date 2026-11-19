#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Apply device-native resolution, custom resolution and memory-budget UI to a
verified Kernarium checkout. This is an iOS SOURCE overlay, never a signed IPA.

Fail closed when upstream interfaces change. On a second application, every
patch is idempotent. Runtime proof still requires an iOS device build.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

DISPLAY_CORE = "GuestHost/Core/Sources/GuestHostCore/GuestDisplayScale.swift"
DISPLAY_VIEW = "GuestHost/Sources/GuestDisplay.swift"
MODEL = "Andarium/Andarium/Shared/Model.swift"
RESOLUTION = "Andarium/Andarium/Shared/Resolution.swift"
HOME = "Andarium/Andarium/Shared/HomeView.swift"
GUEST_LAYER = "Andarium/Andarium/Live/GuestLayer.swift"
APP_ENTRY = "Andarium/Andarium/Live/AppEntry.swift"
PREFERENCES = "Andarium/Andarium/Live/PreferenceKeeper.swift"
APP = "Andarium/Andarium/Shared/AndariumApp.swift"
RULER = "Andarium/Andarium/Shared/Ruler.swift"
SHEETS = "Andarium/Andarium/Shared/Sheets.swift"
FILES = (DISPLAY_CORE, DISPLAY_VIEW, MODEL, RESOLUTION, HOME, GUEST_LAYER,
         APP_ENTRY, PREFERENCES, APP, RULER, SHEETS)
ADD_SWIFT = ("RedDisplayChoice.swift", "RedMemoryChoices.swift", "RedResolutionSheet.swift")


def once(text: str, old: str, new: str, name: str) -> str:
    if new in text:
        return text
    if text.count(old) != 1:
        raise ValueError(f"{name}: expected exactly one upstream source anchor, found {text.count(old)}")
    return text.replace(old, new, 1)


def patch_core(s: str) -> str:
    old = "    public var pixelSize: CGSize { CGSize(width: width, height: height) }"
    new = """    /// Explicit drawable pixels with density derived from the view width.
    /// ANDD and custom resolutions use the same geometry in Home and runtime.
    public init?(pixelWidth: Int, pixelHeight: Int, points: CGSize) {
        guard pixelWidth > 0, pixelHeight > 0,
              pixelWidth <= 8192, pixelHeight <= 8192,
              pixelWidth <= 16_777_216 / pixelHeight,
              points.width.isFinite, points.height.isFinite,
              points.width > 0, points.height > 0 else { return nil }
        let pixelsPerPoint = Double(pixelWidth) / Double(points.width)
        guard pixelsPerPoint.isFinite, pixelsPerPoint > 0 else { return nil }
        width = pixelWidth
        height = pixelHeight
        factor = pixelsPerPoint
        dotsPerInch = Self.dotsPerInch(factor: pixelsPerPoint)
    }

""" + old
    return once(s, old, new, DISPLAY_CORE)


def patch_display(s: str) -> str:
    s = once(s, "    let scale: GuestDisplayScale\n    /// What VoiceOver",
             "    let scale: GuestDisplayScale\n    var redPixelOverride: CGSize? = nil\n    /// What VoiceOver", DISPLAY_VIEW)
    anchor = "        view.scale = scale\n"
    if "        view.redPixelOverride = redPixelOverride\n" not in s:
        if s.count(anchor) != 2:
            raise ValueError("GuestDisplayView scale assignment changed")
        s = s.replace(anchor, anchor + "        view.redPixelOverride = redPixelOverride\n")
    s = once(s, "    var scale = GuestDisplayScale.points\n",
             "    var scale = GuestDisplayScale.points\n    var redPixelOverride: CGSize?\n", DISPLAY_VIEW)
    old = """        guard let screen = window?.screen,
              // SwiftUI supplies safe-area-excluded point bounds, which the
              // scale turns into guest pixels, fractional native scales
              // included.
              let layout = GuestDisplayLayout(
                  scale: scale, points: bounds.size, nativeScale: Double(screen.nativeScale)
              ) else { return }
        drawableSize = layout.pixelSize"""
    new = """        guard let screen = window?.screen else { return }
        // Physical/custom pixels must affect the Metal drawable, Android
        // geometry, and touchscreen mapping, not just a settings label.
        let layout: GuestDisplayLayout?
        if let redPixelOverride {
            layout = GuestDisplayLayout(
                pixelWidth: Int(redPixelOverride.width),
                pixelHeight: Int(redPixelOverride.height),
                points: bounds.size
            )
        } else {
            layout = GuestDisplayLayout(
                scale: scale, points: bounds.size, nativeScale: Double(screen.nativeScale)
            )
        }
        guard let layout else { return }
        drawableSize = layout.pixelSize"""
    return once(s, old, new, DISPLAY_VIEW)


def patch_model(s: str) -> str:
    s = once(s, "    var chosenScale: GuestDisplayScale?\n",
             """    var chosenScale: GuestDisplayScale?
    /// ANDD is default; a migrated explicit scale keeps the old mode.
    var redResolutionSetting = RedResolutionSetting()
    var redNativePixelSize: CGSize?
    /// Physical nativeBounds is typically portrait-sized; line it up with
    /// the visible window's orientation instead of stretching landscape.
    var redNativeOrientedPixelSize: CGSize? {
        guard let pixels = redNativePixelSize, pixels.width > 0, pixels.height > 0 else {
            return nil
        }
        guard let points = displayPoints, points.width > 0, points.height > 0 else {
            return pixels
        }
        if (pixels.width > pixels.height) != (points.width > points.height) {
            return CGSize(width: pixels.height, height: pixels.width)
        }
        return pixels
    }
    /// Nil selects the upstream scaled-resolution behavior.
    var redPixelSize: CGSize? {
        guard launchScale == nil else { return nil }
        return redResolutionSetting.pixels(native: redNativeOrientedPixelSize)
    }
""", MODEL)
    old = "    var resolutionLayout: GuestDisplayLayout? { resolutionLayout(at: resolutionIndex) }"
    new = """    var resolutionLayout: GuestDisplayLayout? {
        if let pixels = redPixelSize, let points = displayPoints {
            return GuestDisplayLayout(pixelWidth: Int(pixels.width),
                                      pixelHeight: Int(pixels.height), points: points)
        }
        return resolutionLayout(at: resolutionIndex)
    }"""
    return once(s, old, new, MODEL)


def patch_resolution(s: str) -> str:
    s = once(s, "        let end = choices.end(at: model.resolutionIndex)\n",
             """        let end = model.redResolutionSetting.mode == .scaled
            ? choices.end(at: model.resolutionIndex) : nil
        let modeName: String
        switch model.redResolutionSetting.mode {
        case .andd: modeName = "ANDD"
        case .custom: modeName = "Custom"
        case .scaled: modeName = "Scaled"
        }
""", RESOLUTION)
    s = once(s, """            subtitle: ResolutionWords.summary(layout: layout, end: end),
            spoken: ResolutionWords.spokenSummary(layout: layout, end: end),""",
             """            subtitle: layout.map { "\\(ResolutionWords.pixels($0)) · \\(modeName)" } ?? modeName,
            spoken: ResolutionWords.spokenSummary(layout: layout, end: end) + ", " + modeName,""",
             RESOLUTION)
    s = once(s, """                    model.screenDidChange(nativeScale: $0.nativeScale)
                    publish()""",
             """                    model.screenDidChange(nativeScale: $0.nativeScale)
                    model.redNativePixelSize = $0.nativePixels
                    publish()""", RESOLUTION)
    s = once(s, "    var nativeScale = 1.0\n",
             "    var nativeScale = 1.0\n    var nativePixels: CGSize = .zero\n", RESOLUTION)
    s = once(s, """            nativeScale: Double(scene.screen.nativeScale),
            topInset:""",
             """            nativeScale: Double(scene.screen.nativeScale),
            nativePixels: scene.screen.nativeBounds.size,
            topInset:""", RESOLUTION)
    return s


def patch_app_entry(s: str) -> str:
    old1 = "        model.chosenScale = DisplayOptionsStore.load().chosenScale ?? .native"
    old2 = "        model.chosenScale = DisplayOptionsStore.load().chosenScale"
    new = """        let redSavedDisplay = DisplayOptionsStore.load()
        model.chosenScale = redSavedDisplay.chosenScale ?? .native
        if let existingRedMode = RedResolutionStore.load() {
            model.redResolutionSetting = existingRedMode
        } else if redSavedDisplay.chosenScale != nil {
            // Respect an existing user's saved scaled resolution on upgrade.
            model.redResolutionSetting.mode = .scaled
        }"""
    if new in s:
        return s
    if old1 in s:
        return once(s, old1, new, APP_ENTRY)
    return once(s, old2, new, APP_ENTRY)


def patch_sheets(s: str) -> str:
    marker = "struct SystemSheet: View {"
    if marker not in s:
        raise ValueError("System sheet anchor changed")
    if "RedMemoryChoices.fresh(on: model.host)" in s:
        return s
    first, rest = s.split(marker, 1)
    old = "Guest.fresh(on: model.host)"
    if first.count(old) < 2:
        raise ValueError("New guest default creation changed")
    first = first.replace(old, "RedMemoryChoices.fresh(on: model.host)")
    return first + marker + rest


def patch_ruler(s: str) -> str:
    old = """            memory
            if let vram = host.memory.graphicsMemoryMiB("""
    new = """            memory
            RedMemoryPresetRow(guest: $guest, host: host, cameraLive: cameraLive)
            if let vram = host.memory.graphicsMemoryMiB("""
    return once(s, old, new, RULER)


def patch_prefs(s: str) -> str:
    old = "        if let options = model.displayOptionsToKeep { DisplayOptionsStore.save(options, to: defaults) }"
    new = old + """
        if model.launchScale == nil {
            RedResolutionStore.save(model.redResolutionSetting, to: defaults)
        }"""
    return once(s, old, new, PREFERENCES)


def patch_guest_layer(s: str) -> str:
    old = """            scale: model.resolution,
            accessibility: accessibility,"""
    new = """            scale: model.resolution,
            redPixelOverride: model.redPixelSize,
            accessibility: accessibility,"""
    return once(s, old, new, GUEST_LAYER)


def patch_home(s: str) -> str:
    return once(s, "case .resolution: ResolutionSheet()",
                "case .resolution: RedResolutionSheet()", HOME)


def patch_app(s: str) -> str:
    old = "        model.screenDidChange(nativeScale: Double(scene.screen.nativeScale))"
    new = old + "\n        model.redNativePixelSize = scene.screen.nativeBounds.size"
    return once(s, old, new, APP)


PATCHES = {
    DISPLAY_CORE: patch_core, DISPLAY_VIEW: patch_display, MODEL: patch_model,
    RESOLUTION: patch_resolution, HOME: patch_home, GUEST_LAYER: patch_guest_layer,
    APP_ENTRY: patch_app_entry, PREFERENCES: patch_prefs, APP: patch_app,
    RULER: patch_ruler, SHEETS: patch_sheets,
}


def is_complete_checkout(root: Path) -> bool:
    return all((root / name).is_file() for name in FILES)


def plan(root: Path, source: Path) -> dict[Path, str]:
    if not is_complete_checkout(root):
        missing = [name for name in FILES if not (root / name).is_file()]
        raise ValueError(f"Kernarium host tree incomplete: {missing}")
    for fname in ADD_SWIFT:
        if not (source / "host" / fname).is_file():
            raise ValueError(f"Andarium Red source file missing: host/{fname}")
    return {root / name: PATCHES[name]((root / name).read_text()) for name in FILES}


def apply(root: Path, source: Path, *, dry_run: bool = False) -> dict:
    changes = plan(root, source)
    changed = [str(p.relative_to(root)) for p, value in changes.items()
               if p.read_text() != value]
    if not dry_run:
        # Preflight all source anchors before the first write.
        for path, value in changes.items():
            if path.read_text() != value:
                path.write_text(value)
        dest = root / "Andarium/Andarium/Shared"
        for name in ADD_SWIFT:
            shutil.copy2(source / "host" / name, dest / name)
    return {
        "planned_host_edits": changed,
        "source_files": list(ADD_SWIFT),
        "applied": not dry_run,
        "native_display_default": True,
        "custom_aspect_lock_source": True,
        "runtime_budget_used_for_memory_presets": True,
        "android_ios_build_passed": False,
        "device_frame_rate_benchmarked": False,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kernarium", type=Path, required=True)
    ap.add_argument("--source", type=Path, default=Path(__file__).resolve().parent)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    print(json.dumps(apply(a.kernarium.resolve(), a.source.resolve(),
                           dry_run=a.dry_run), indent=2))


if __name__ == "__main__":
    main()
