// SPDX-License-Identifier: GPL-2.0-or-later
// Compile with the real policy source:
// swiftc host/RedDisplayChoice.swift tests/RedResolutionValuesHarness.swift -o /tmp/red-andd-test
// /tmp/red-andd-test
import Foundation

@main struct RedResolutionValuesHarness {
    static var passed = 0

    static func assert(_ condition: @autoclosure () -> Bool, _ label: String) {
        guard condition() else {
            fputs("FAIL: \(label)\n", stderr)
            exit(1)
        }
        passed += 1
        print("PASS: \(label)")
    }

    static func main() throws {
        var setting = RedResolutionSetting()
        assert(setting.mode == .andd, "fresh installs default ANDD")
        assert(setting.pixels(native: CGSize(width: 1290, height: 2796)) ==
               CGSize(width: 1290, height: 2796), "native iPhone 14 Pro Max pixels")
        assert(setting.pixels(native: CGSize(width: 2796, height: 1290)) ==
               CGSize(width: 2796, height: 1290), "orientation-swapped native pixels")
        assert(setting.pixels(native: nil) == nil, "unknown native screen needs fallback")
        assert(setting.pixels(native: CGSize(width: 8192, height: 8192)) == nil,
               "unsupported EDID dimensions rejected")
        assert(setting.pixels(native: CGSize(width: .infinity, height: 1080)) == nil,
               "nonfinite physical screen dimensions rejected")
        assert(setting.pixels(native: CGSize(width: 4095, height: 4095)) != nil,
               "4095-pixel EDID boundary is admitted")

        setting.mode = .custom
        setting.seedFromNative(CGSize(width: 1290, height: 2796))
        assert(setting.width == 1290 && setting.height == 2796, "custom initialized from device")
        setting.setWidth(645)
        assert(setting.height == 1398, "chain scales height from width")
        setting.setHeight(2796)
        assert(setting.width == 1290, "chain scales width from height")
        setting.setLinked(false)
        setting.setWidth(1600)
        assert(setting.height == 2796, "unlinked width never changes height")
        setting.setHeight(2100)
        assert(setting.width == 1600, "unlinked height never changes width")
        setting.setLinked(true)
        setting.setWidth(800)
        assert(setting.height == 1050, "new link locks current dimensions' ratio")
        setting.setLinked(false)
        setting.setWidth(4096)
        assert(!setting.customIsValid && setting.pixels(native: nil) == nil,
               "width over display limit cannot be saved")
        setting.setWidth(256)
        setting.setHeight(256)
        assert(setting.customIsValid, "minimum custom pixel size supported")
        setting.setWidth(255)
        assert(!setting.customIsValid, "less than minimum size rejected")
        setting.setWidth(800)
        setting.setHeight(800)
        assert(setting.customIsValid, "valid custom dimensions accepted")
        setting.seedFromNative(CGSize(width: Double.greatestFiniteMagnitude, height: 1080))
        assert(setting.width == 800 && setting.height == 800,
               "extreme finite device size cannot crash or change custom fields")

        let name = "red-display-harness-\(UUID().uuidString)"
        guard let defaults = UserDefaults(suiteName: name) else { fatalError("No defaults suite") }
        defer { defaults.removePersistentDomain(forName: name) }
        RedResolutionStore.save(setting, to: defaults)
        assert(RedResolutionStore.load(from: defaults) == setting,
               "settings survive save and restore")
        let old = setting
        setting.setWidth(5000)
        RedResolutionStore.save(setting, to: defaults)
        assert(RedResolutionStore.load(from: defaults) == old,
               "invalid settings cannot overwrite the last good value")
        print("ANDD_VALUE_HARNESS_\(passed)_PASS")
    }
}
