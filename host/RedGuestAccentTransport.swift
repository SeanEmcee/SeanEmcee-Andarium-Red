// SPDX-License-Identifier: Apache-2.0
import Foundation

/// Prepares a restricted, argv-safe integer handoff to the Android launcher.
/// This is not a guest emulator, a privilege escalation, or runtime proof.
/// The host should invoke it only on an explicit guest launch/theme action:
/// 'am start' brings the launcher to the foreground.
enum RedGuestAccentTransport {
    static let extra = "dev.twoyi.redlauncher.NEXARIS_ACCENT_RGB"
    static let component = "dev.twoyi.redlauncher/.MainActivity"

    enum AccentError: Error, LocalizedError, Equatable {
        case outOfRange
        case guestRejected

        var errorDescription: String? {
            switch self {
            case .outOfRange: return "Nexaris accent must be a 24-bit RGB color."
            case .guestRejected: return "Android did not accept the accent launch command."
            }
        }
    }

    static func command(rgb: UInt32) throws -> String {
        guard rgb <= 0x00FF_FFFF else { throw AccentError.outOfRange }
        // All string content is fixed. Only a checked decimal integer is interpolated.
        return "am start --user 0 -n \(component) --ei \(extra) \(rgb)"
    }

    static func verify(_ output: String, exitCode: Int?) throws {
        guard exitCode == 0 else { throw AccentError.guestRejected }
        let lower = output.lowercased()
        // Android CLI sometimes reports intent/component failures while the
        // shell exits successfully. Reject such responses rather than
        // claiming the Android UI accepted the theme.
        if lower.contains("error:") || lower.contains("exception") ||
            lower.contains("permission denial") || lower.contains("does not exist") {
            throw AccentError.guestRejected
        }
        // Avoid mistaking empty/noisy shell output for a confirmed launch.
        // Android may report either a new Activity start or a delivered intent
        // to an existing top-most Activity. Both require device acceptance
        // before claiming pixels actually changed.
        let acceptedStart = output.contains("Starting: Intent")
        let delivered = output.contains("Warning: Activity not started, intent has been delivered")
        guard acceptedStart || delivered else { throw AccentError.guestRejected }
    }
}
