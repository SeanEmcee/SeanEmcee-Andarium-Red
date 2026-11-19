// SPDX-License-Identifier: GPL-2.0-or-later
import Foundation

/// Persistent preference for the next new guest. Existing guest memory is
/// unaffected when the preference changes in the current guest's settings.
enum RedMemoryPreset: String, Codable, CaseIterable, Identifiable {
    case quality = "max-quality"
    case graphics = "graphics-priority"
    case safe = "high-ram"
    case deviceLimit = "device-limit"

    var id: String { rawValue }

    var title: String {
        switch self {
        case .quality: return "Max quality"
        case .graphics: return "Graphics priority"
        case .safe: return "High RAM"
        case .deviceLimit: return "Device limit"
        }
    }
}

enum RedMemoryPresetStore {
    static let key = "andarium.red.memory.defaultPreset.v1"

    static func load(from defaults: UserDefaults = .standard) -> RedMemoryPreset {
        guard let value = defaults.string(forKey: key),
              let preset = RedMemoryPreset(rawValue: value) else { return .quality }
        return preset
    }

    static func save(_ preset: RedMemoryPreset, to defaults: UserDefaults = .standard) {
        defaults.set(preset.rawValue, forKey: key)
    }
}
