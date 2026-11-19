// SPDX-License-Identifier: GPL-2.0-or-later
import Foundation

@main struct SwiftClipboardHarness {
    static func run(_ input: String) throws {
        let command = try RedClipboardCodec.writeCommand(for: input)
        precondition(command.hasPrefix("content call --uri content://dev.twoyi.redclipboard/clipboard --method write --extra b64:s:"))
        let payload = String(command.split(separator: ":").last ?? "")
        let result = try RedClipboardCodec.parseRead("Result: Bundle[{b64=\(payload)}]")
        precondition(input == result, "roundtrip mismatch")
        try RedClipboardCodec.verifyWrite("Result: Bundle[{status=ok}]")
    }
    static func main() throws {
        try run("Hello, Android 17!")
        try run("Emoji 👩‍💻 and Japanese 日本語 🚀\nNewlines")
        try run("' ; && | $(touch /tmp/unsafe) \" " )
        try run(String(repeating: "x", count: RedClipboardCodec.limit))
        do {
            _ = try RedClipboardCodec.writeCommand(for: String(repeating: "z", count: RedClipboardCodec.limit+1))
            fatalError("limit not enforced")
        } catch RedClipboardCodec.BridgeError.tooLarge { }
        do { _ = try RedClipboardCodec.parseRead("Result: Bundle[{b64=~}]"); fatalError("expected empty") }
        catch RedClipboardCodec.BridgeError.empty { }
        do { _ = try RedClipboardCodec.parseRead("Result: Bundle[{status=permission_denied}]"); fatalError("expected permission") }
        catch RedClipboardCodec.BridgeError.guestRejected(let code) { precondition(code == "permission_denied") }
        do { try RedClipboardCodec.verifyWrite("not a bundle"); fatalError("expected invalid") }
        catch RedClipboardCodec.BridgeError.invalidResponse { }
        for spoof in [
            "noise status=ok Result: Bundle[{status=ok}]",
            "Result: Bundle[{xstatus=ok}]",
            "Result: Bundle[{status=ok, status=ok}]",
            "Result: Bundle[{b64=QQ, b64=Qg}]",
            "Result: Bundle[{b64=QQ==}]",
            "Result: Bundle[{b64=🧪}]",
            "Result: Bundle[{status=ok}]\nsecondary output",
        ] {
            do {
                try RedClipboardCodec.verifyWrite(spoof)
                fatalError("malformed clipboard response accepted: \(spoof)")
            } catch RedClipboardCodec.BridgeError.invalidResponse { }
        }
        for ambiguous in ["AB", "Zh", "AA_", "____B"] {
            do { _ = try RedClipboardCodec.parseRead("Result: Bundle[{b64=\(ambiguous)}]")
                fatalError("noncanonical base64 accepted: \(ambiguous)") }
            catch RedClipboardCodec.BridgeError.invalidResponse { }
        }
        let badUTF8 = "Result: Bundle[{b64=wyg}]"
        do { _ = try RedClipboardCodec.parseRead(badUTF8); fatalError("malformed UTF8 accepted") }
        catch RedClipboardCodec.BridgeError.invalidUTF8 { }
        do { _ = try RedClipboardCodec.parseRead("Result: Bundle[{b64=QQ, status=ok}]"); fatalError("mixed fields accepted") }
        catch RedClipboardCodec.BridgeError.invalidResponse { }
        print("SWIFT_CLIPBOARD_TESTS_PASS (UTF-8, 32KiB, shell-safe, malformed-output rejection)")
    }
}
