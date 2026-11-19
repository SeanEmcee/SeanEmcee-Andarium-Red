// SPDX-License-Identifier: GPL-2.0-or-later
// Compiled in Andarium/Shared by Kernarium's synchronized source folder.
import Foundation

/// ANDD reads the scene's *physical* pixels, never a hard-coded model table.
/// Legacy scaled selections remain available for people who chose them.
enum RedResolutionMode: String, Codable, CaseIterable {
    case andd, custom, scaled
}

struct RedResolutionSetting: Codable, Equatable {
    var mode: RedResolutionMode = .andd
    var width = 1080
    var height = 1920
    var linked = true
    private(set) var ratioWidth = 1080
    private(set) var ratioHeight = 1920

    static let minimumSide = 256
    static let maximumSide = 4095
    static let maximumPixels = 16_777_216

    var customIsValid: Bool {
        width >= Self.minimumSide && height >= Self.minimumSide &&
        width <= Self.maximumSide && height <= Self.maximumSide &&
        width <= Self.maximumPixels / height
    }

    /// ANDD is relative to the current connected window scene, not the phone
    /// model identifier. Saved choices therefore work on a new phone or screen.
    func pixels(native: CGSize?) -> CGSize? {
        switch mode {
        case .andd:
            guard let native, native.width.isFinite, native.height.isFinite,
                  native.width >= CGFloat(Self.minimumSide),
                  native.height >= CGFloat(Self.minimumSide),
                  native.width <= CGFloat(Self.maximumSide),
                  native.height <= CGFloat(Self.maximumSide),
                  native.width <= CGFloat(Self.maximumPixels) / native.height
            else { return nil }
            return CGSize(width: native.width.rounded(), height: native.height.rounded())
        case .custom:
            guard customIsValid else { return nil }
            return CGSize(width: width, height: height)
        case .scaled:
            return nil
        }
    }

    mutating func seedFromNative(_ native: CGSize?) {
        guard let native, native.width.isFinite, native.height.isFinite,
              native.width >= CGFloat(Self.minimumSide),
              native.height >= CGFloat(Self.minimumSide),
              native.width <= CGFloat(Self.maximumSide),
              native.height <= CGFloat(Self.maximumSide) else { return }
        let w = Int(native.width.rounded()), h = Int(native.height.rounded())
        guard w >= Self.minimumSide, h >= Self.minimumSide,
              w <= Self.maximumSide, h <= Self.maximumSide,
              w <= Self.maximumPixels / h else { return }
        width = w
        height = h
        ratioWidth = w
        ratioHeight = h
    }

    mutating func setLinked(_ on: Bool) {
        linked = on
        if on {
            ratioWidth = max(width, 1)
            ratioHeight = max(height, 1)
        }
    }

    /// The chain preserves the aspect measured when it was switched on;
    /// editing only one field with the chain off never touches the other.
    mutating func setWidth(_ newValue: Int) {
        width = newValue
        if linked, newValue > 0, newValue <= 100_000 {
            height = Int((Double(newValue) * Double(ratioHeight) /
                Double(max(ratioWidth, 1))).rounded())
        }
    }

    mutating func setHeight(_ newValue: Int) {
        height = newValue
        if linked, newValue > 0, newValue <= 100_000 {
            width = Int((Double(newValue) * Double(ratioWidth) /
                Double(max(ratioHeight, 1))).rounded())
        }
    }
}

enum RedResolutionStore {
    static let key = "andarium.red.resolution.v1"

    static func load(from defaults: UserDefaults = .standard) -> RedResolutionSetting? {
        guard let data = defaults.data(forKey: key),
              let setting = try? JSONDecoder().decode(RedResolutionSetting.self, from: data),
              setting.mode != .custom || setting.customIsValid else { return nil }
        return setting
    }

    static func save(_ setting: RedResolutionSetting, to defaults: UserDefaults = .standard) {
        guard setting.mode != .custom || setting.customIsValid,
              let data = try? JSONEncoder().encode(setting) else { return }
        defaults.set(data, forKey: key)
    }
}
