// SPDX-License-Identifier: GPL-2.0-or-later
import SwiftUI
import UIKit

/// User-initiated host↔guest clipboard controls, shown only in an Android session.
/// Never polls a clipboard or synchronizes anything in the background.
struct RedClipboardControls: View {
    let runtime: LiveRuntime?
    @ObservedObject private var accentState = RedHostAccentState.shared
    @State private var active = false
    @State private var message: String?

    var body: some View {
        Menu {
            Button("Paste into Android", systemImage: "arrow.down.doc") {
                Task { await pasteIntoGuest() }
            }
            Button("Copy from Android", systemImage: "arrow.up.doc") {
                Task { await copyFromGuest() }
            }
        } label: {
            Image(systemName: "doc.on.clipboard")
                .font(.system(size: 17, weight: .semibold))
                .foregroundStyle(accentState.color)
                .padding(11)
                .background(.black.opacity(0.92), in: Circle())
                .overlay(Circle().stroke(accentState.color.opacity(0.65), lineWidth: 1))
        }
        .disabled(active || runtime == nil)
        .accessibilityLabel("Android clipboard")
        .padding(.trailing, 14)
        .padding(.top, 30)
        .alert("Clipboard", isPresented: Binding(
            get: { message != nil }, set: { if !$0 { message = nil } }
        )) { Button("OK", role: .cancel) { message = nil } } message: { Text(message ?? "") }
    }

    @MainActor private func pasteIntoGuest() async {
        guard let runtime else { return }
        // UIPasteboard is accessed only after the person explicitly chooses Paste.
        guard let text = UIPasteboard.general.string else {
            message = "There is no plain text in the iOS clipboard."
            return
        }
        active = true
        defer { active = false }
        do {
            let command = try RedClipboardCodec.writeCommand(for: text)
            let result = try await runtime.redClipboardShell(command)
            try RedClipboardCodec.verifyWrite(result)
            message = "Text copied into Android's clipboard."
        } catch { message = error.localizedDescription }
    }

    @MainActor private func copyFromGuest() async {
        guard let runtime else { return }
        active = true
        defer { active = false }
        do {
            let result = try await runtime.redClipboardShell(RedClipboardCodec.readCommand)
            let text = try RedClipboardCodec.parseRead(result)
            UIPasteboard.general.string = text
            message = "Android clipboard copied to iOS."
        } catch { message = error.localizedDescription }
    }
}
