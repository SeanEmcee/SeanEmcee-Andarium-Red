// SPDX-License-Identifier: Apache-2.0
import Foundation

private func check(_ condition: Bool, _ description: String) {
    precondition(condition, description)
}

@main
struct GuestAccentHarness {
    static func main() throws {
        let defaultRed = try RedGuestAccentTransport.command(rgb: 0xF22B43)
        check(defaultRed == "am start --user 0 -n dev.twoyi.redlauncher/.MainActivity --ei dev.twoyi.redlauncher.NEXARIS_ACCENT_RGB 15870787", "default RGB command")
        let black = try RedGuestAccentTransport.command(rgb: 0)
        check(black.hasSuffix(" 0"), "black RGB")
        let white = try RedGuestAccentTransport.command(rgb: 0xFFFFFF)
        check(white.hasSuffix(" 16777215"), "max RGB")
        do {
            _ = try RedGuestAccentTransport.command(rgb: 0x01000000)
            preconditionFailure("out-of-range RGB accepted")
        } catch RedGuestAccentTransport.AccentError.outOfRange {}
        try RedGuestAccentTransport.verify("Starting: Intent { ... }", exitCode: 0)
        try RedGuestAccentTransport.verify("Warning: Activity not started, intent has been delivered to currently running top-most instance.", exitCode: 0)
        for message in ["", "Success without explicit activity confirmation", "Error: Activity class does not exist", "java.lang.SecurityException", "Permission Denial: not exported"] {
            do {
                try RedGuestAccentTransport.verify(message, exitCode: 0)
                preconditionFailure("Android error reply accepted")
            } catch RedGuestAccentTransport.AccentError.guestRejected {}
        }
        do {
            try RedGuestAccentTransport.verify("", exitCode: 1)
            preconditionFailure("nonzero exit accepted")
        } catch RedGuestAccentTransport.AccentError.guestRejected {}
        print("GUEST_ACCENT_SWIFT_11_PASS (local command validator; not guest execution)")
    }
}
