// SPDX-License-Identifier: GPL-2.0-or-later
import Foundation

/// Concrete host side of Android's Nexaris launcher mailbox. A real embedded
/// NexarisAndariumGuestRuntime driver calls these on its LiveRuntime instance.
/// This does not attempt to call UIApplication.open or open another iOS app.
extension LiveRuntime {
    /// A normal successful ADB response is an exact single Bundle:
    /// Result: Bundle[{event=v1:<32 lowercase hex>:nexaris}]
    /// or Result: Bundle[{event=~}] when no request is pending.
    func redReadNativeHostLaunchMessage() async throws -> String {
        try await redClipboardShell(
            "content call --uri content://dev.twoyi.redlauncher.host/launch --method next"
        )
    }

    /// The Android provider removes the event only after an exact ack. This
    /// prevents an interrupted native navigation from silently losing a tap.
    func redAcknowledgeNativeHostLaunchMessage(id: String) async throws -> String {
        let valid = id.utf8.count == 32 && id.utf8.allSatisfy {
            (48...57).contains($0) || (97...102).contains($0)
        }
        guard valid else { throw RedHostLaunchError.invalidID }
        return try await redClipboardShell(
            "content call --uri content://dev.twoyi.redlauncher.host/launch --method ack --arg " + id
        )
    }
}

enum RedHostLaunchError: Error, LocalizedError {
    case invalidID
    var errorDescription: String? {
        "Android host launch contained an invalid message identifier."
    }
}
