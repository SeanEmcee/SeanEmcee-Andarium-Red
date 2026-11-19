// SPDX-License-Identifier: Apache-2.0
import SwiftUI

/// Cosmetic in-process state for Andarium-owned controls. The Nexaris adapter
/// updates this only after Android confirms the same RGB was persisted.
/// This is not an iOS entitlement, a standalone permission, or runtime proof.
@MainActor
final class RedHostAccentState: ObservableObject {
    static let shared = RedHostAccentState()
    @Published private(set) var rgb: UInt32 = 0xF22B43

    var color: Color {
        Color(
            red: Double((rgb >> 16) & 255) / 255,
            green: Double((rgb >> 8) & 255) / 255,
            blue: Double(rgb & 255) / 255
        )
    }

    func acceptVerified(_ selected: UInt32) {
        guard selected <= 0x00FF_FFFF else { return }
        rgb = selected
    }

    private init() {}
}
