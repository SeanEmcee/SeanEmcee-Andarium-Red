// SPDX-License-Identifier: GPL-2.0-or-later
import Foundation

/// Pure, testable ADB text protocol. All reads require an explicit button tap.
/// The commands go over Andarium's existing authenticated, in-process ADB channel.
enum RedClipboardCodec {
    static let limit = 32_768
    private static let authority = "content://dev.twoyi.redclipboard/clipboard"

    enum BridgeError: Error, LocalizedError, Equatable {
        case empty
        case tooLarge
        case invalidResponse
        case invalidUTF8
        case guestRejected(String)

        var errorDescription: String? {
            switch self {
            case .empty: return "Android clipboard has no plain text."
            case .tooLarge: return "Clipboard text exceeds 32 KiB."
            case .invalidResponse: return "Android clipboard bridge returned an invalid response."
            case .invalidUTF8: return "Clipboard text is not valid UTF-8."
            case .guestRejected(let status): return "Android clipboard bridge: \(status)."
            }
        }
    }

    static let readCommand = "content call --uri \(authority) --method read"

    static func writeCommand(for text: String) throws -> String {
        let data = Data(text.utf8)
        guard data.count <= limit else { throw BridgeError.tooLarge }
        // URL-safe base64 contains no shell metacharacters, preventing injection.
        let b64 = data.base64EncodedString()
            .replacingOccurrences(of: "+", with: "-")
            .replacingOccurrences(of: "/", with: "_")
            .replacingOccurrences(of: "=", with: "")
        return "content call --uri \(authority) --method write --extra b64:s:\(b64)"
    }

    /// Android's `content call` result is a Bundle line, not arbitrary stdout.
    /// Refuse duplicated keys, other shell output and ambiguous field names.
    /// Values in this protocol are ASCII tokens: unpadded URL-safe base64,
    /// `~` for a missing clip, and fixed status words.
    private static func fields(_ raw: String) throws -> [String: String] {
        let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        let prefix = "Result: Bundle[{"
        guard trimmed.hasPrefix(prefix), trimmed.hasSuffix("}]") else {
            throw BridgeError.invalidResponse
        }
        let start = trimmed.index(trimmed.startIndex, offsetBy: prefix.count)
        let end = trimmed.index(trimmed.endIndex, offsetBy: -2)
        let body = String(trimmed[start..<end])
        var values: [String: String] = [:]
        for entry in body.split(separator: ",", omittingEmptySubsequences: false) {
            guard let equals = entry.firstIndex(of: "=") else { throw BridgeError.invalidResponse }
            let name = entry[..<equals].trimmingCharacters(in: .whitespaces)
            let value = entry[entry.index(after: equals)...].trimmingCharacters(in: .whitespaces)
            guard name == "b64" || name == "status", values[name] == nil else {
                throw BridgeError.invalidResponse
            }
            // No whitespace or shell control characters in wire values.
            guard value.unicodeScalars.allSatisfy({ $0.value >= 33 && $0.value <= 126 }) || value.isEmpty else {
                throw BridgeError.invalidResponse
            }
            values[name] = value
        }
        guard !values.isEmpty else { throw BridgeError.invalidResponse }
        return values
    }

    static func parseRead(_ output: String) throws -> String {
        let values = try fields(output)
        if let status = values["status"] {
            guard values.count == 1 else { throw BridgeError.invalidResponse }
            if status == "too_large" { throw BridgeError.tooLarge }
            throw BridgeError.guestRejected(status)
        }
        guard let payload = values["b64"], values.count == 1 else { throw BridgeError.invalidResponse }
        if payload == "~" { throw BridgeError.empty }
        // Prevent malformed/oversized shell output allocating a large buffer.
        guard payload.count <= (limit + 2) / 3 * 4 else { throw BridgeError.tooLarge }
        guard payload.allSatisfy({ ("A"..."Z").contains(String($0)) || ("a"..."z").contains(String($0)) ||
            ("0"..."9").contains(String($0)) || $0 == "-" || $0 == "_" }) else {
            throw BridgeError.invalidResponse
        }
        let converted = payload.replacingOccurrences(of: "-", with: "+")
            .replacingOccurrences(of: "_", with: "/")
        let padded = converted + String(repeating: "=", count: (4 - converted.count % 4) % 4)
        guard let decoded = Data(base64Encoded: padded) else { throw BridgeError.invalidResponse }
        // Non-zero discarded base64 bits can decode to the same data. Require
        // the exact canonical, unpadded URL-safe spelling from the provider.
        let canonical = decoded.base64EncodedString()
            .replacingOccurrences(of: "+", with: "-")
            .replacingOccurrences(of: "/", with: "_")
            .replacingOccurrences(of: "=", with: "")
        guard canonical == payload else { throw BridgeError.invalidResponse }
        guard decoded.count <= limit else { throw BridgeError.tooLarge }
        guard let value = String(data: decoded, encoding: .utf8) else { throw BridgeError.invalidUTF8 }
        return value
    }

    static func verifyWrite(_ output: String) throws {
        let values = try fields(output)
        guard values.count == 1, let status = values["status"] else { throw BridgeError.invalidResponse }
        guard status == "ok" else { throw BridgeError.guestRejected(status) }
    }
}
