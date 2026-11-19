// SPDX-License-Identifier: GPL-2.0-or-later
// swiftc host/RedMemoryPresetSettings.swift tests/RedMemoryPresetHarness.swift -o /tmp/red-memory-test
import Foundation

@main struct RedMemoryPresetHarness {
    static var passed = 0

    static func check(_ truth: @autoclosure () -> Bool, _ label: String) {
        if !truth() {
            print("FAIL: \(label)")
            exit(1)
        }
        passed += 1
        print("PASS: \(label)")
    }

    static func main() throws {
        let domain = "andarium.test.memory.\(UUID().uuidString)"
        guard let prefs = UserDefaults(suiteName: domain) else { fatalError("defaults unavailable") }
        defer { prefs.removePersistentDomain(forName: domain) }

        check(RedMemoryPresetStore.load(from: prefs) == .quality, "quality is safe default")
        check(RedMemoryPreset.allCases.count == 4, "four supported profiles")
        for preset in RedMemoryPreset.allCases {
            RedMemoryPresetStore.save(preset, to: prefs)
            check(RedMemoryPresetStore.load(from: prefs) == preset,
                  "stored preference remains \(preset.rawValue)")
            check(!preset.title.isEmpty, "profile \(preset.rawValue) has a readable label")
        }
        prefs.set("unknown-memory-mode", forKey: RedMemoryPresetStore.key)
        check(RedMemoryPresetStore.load(from: prefs) == .quality,
              "corrupt memory default falls back to quality")
        prefs.removeObject(forKey: RedMemoryPresetStore.key)
        check(RedMemoryPresetStore.load(from: prefs) == .quality,
              "removing memory preference resets to quality")
        print("RED_MEMORY_PRESET_\(passed)_PASS")
    }
}
