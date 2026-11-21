// SPDX-License-Identifier: Apache-2.0
import Foundation

/// Local authenticated guest ADB content-provider protocol. Does not launch
/// an Activity or change the foreground Android app. Readback confirms
/// persistent RGB storage, not pixel-perfect live rendering.
enum RedGuestAccentTransport {
    static let authority = "content://dev.twoyi.redlauncher.theme/"

    enum AccentError: Error, LocalizedError, Equatable {
        case outOfRange
        case guestRejected

        var errorDescription: String? {
            switch self {
            case .outOfRange: return "Nexaris accent must be a 24-bit RGB color."
            case .guestRejected: return "Android did not confirm the theme color update."
            }
        }
    }

    static func command(rgb: UInt32) throws -> String {
        guard rgb <= 0x00FF_FFFF else { throw AccentError.outOfRange }
        // Every shell token is fixed except the validated decimal integer.
        return "content call --uri \(authority) --method set --extra rgb:i:\(rgb)"
    }

    static let readCommand = "content call --uri \(authority) --method get"

    static func verify(_ output: String, exitCode: Int?) throws {
        guard exitCode == 0 else { throw AccentError.guestRejected }
        guard output.trimmingCharacters(in: .whitespacesAndNewlines) ==
            "Result: Bundle[{status=ok}]" else { throw AccentError.guestRejected }
    }

    static func verifyRead(_ output: String, exitCode: Int?, expectedRGB: UInt32) throws {
        guard expectedRGB <= 0x00FF_FFFF, exitCode == 0 else {
            throw AccentError.guestRejected
        }
        let expected = "Result: Bundle[{rgb=\(expectedRGB)}]"
        guard output.trimmingCharacters(in: .whitespacesAndNewlines) == expected else {
            throw AccentError.guestRejected
        }
    }
}
