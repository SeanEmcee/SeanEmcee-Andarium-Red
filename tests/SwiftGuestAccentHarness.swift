// SPDX-License-Identifier: Apache-2.0
import Foundation

private func check(_ condition: Bool, _ description: String) {
    precondition(condition, description)
}

@main
struct GuestAccentHarness {
    static func main() throws {
        let expectedPrefix = "content call --uri content://dev.twoyi.redlauncher.theme/"
        let crimson = try RedGuestAccentTransport.command(rgb: 0xF22B43)
        check(crimson == expectedPrefix + " --method set --extra rgb:i:15870787", "default RGB")
        check(try RedGuestAccentTransport.command(rgb: 0) == expectedPrefix + " --method set --extra rgb:i:0", "black RGB")
        check(try RedGuestAccentTransport.command(rgb: 0xFFFFFF).hasSuffix("16777215"), "white RGB")
        check(RedGuestAccentTransport.readCommand == expectedPrefix + " --method get", "readback command")
        do {
            _ = try RedGuestAccentTransport.command(rgb: 0x01000000)
            preconditionFailure("invalid RGB accepted")
        } catch RedGuestAccentTransport.AccentError.outOfRange {}

        try RedGuestAccentTransport.verify("Result: Bundle[{status=ok}]", exitCode: 0)
        try RedGuestAccentTransport.verifyRead("Result: Bundle[{rgb=15870787}]", exitCode: 0, expectedRGB: 0xF22B43)
        for bad in ["", "Result: Bundle[{status=permission_denied}]", "Result: Bundle[{status=ok,other=ok}]", "Injected\nResult: Bundle[{status=ok}]", "Result: Bundle[{not_status=ok}]"] {
            do {
                try RedGuestAccentTransport.verify(bad, exitCode: 0)
                preconditionFailure("bad status accepted")
            } catch RedGuestAccentTransport.AccentError.guestRejected {}
        }
        for bad in ["", "Result: Bundle[{rgb=0}]", "Result: Bundle[{rgb=15870787,foo=bar}]", "Result: Bundle[{rgb=0xF22B43}]"] {
            do {
                try RedGuestAccentTransport.verifyRead(bad, exitCode: 0, expectedRGB: 0xF22B43)
                preconditionFailure("bad readback accepted")
            } catch RedGuestAccentTransport.AccentError.guestRejected {}
        }
        do {
            try RedGuestAccentTransport.verify("Result: Bundle[{status=ok}]", exitCode: nil)
            preconditionFailure("unknown shell exit accepted")
        } catch RedGuestAccentTransport.AccentError.guestRejected {}
        print("GUEST_ACCENT_SWIFT_17_PASS (local provider protocol; not guest execution)")
    }
}
