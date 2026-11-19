// SPDX-License-Identifier: GPL-2.0-or-later
import Foundation
import UIKit
import Darwin

/// Device identification is informational. Resolution comes from nativeBounds,
/// which also supports new iPhones without a table or an app update.
enum RedDeviceDisplay {
    static var hardwareID: String {
        var count: size_t = 0
        guard sysctlbyname("hw.machine", nil, &count, nil, 0) == 0,
              count > 1, count < 128 else { return UIDevice.current.model }
        var buffer = [CChar](repeating: 0, count: count)
        guard sysctlbyname("hw.machine", &buffer, &count, nil, 0) == 0 else {
            return UIDevice.current.model
        }
        return String(cString: buffer)
    }

    static var modelLabel: String {
        let id = hardwareID
        if id == "iPhone15,3" { return "iPhone 14 Pro Max" }
        return UIDevice.current.model + " (" + id + ")"
    }
}
