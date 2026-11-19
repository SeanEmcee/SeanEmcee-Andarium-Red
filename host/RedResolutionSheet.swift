// SPDX-License-Identifier: GPL-2.0-or-later
import AndariumCore
import SwiftUI
import UIKit

/// Andarium Red's resolution control. The old factor-based modes remain
/// available, but an untouched install now selects ANDD. Both the preview
/// and the boot renderer read exactly the same selected pixel size.
struct RedResolutionSheet: View {
    @Environment(AppModel.self) private var model
    @Environment(\.dismiss) private var dismiss

    @State private var draft = RedResolutionSetting()
    @State private var widthText = ""
    @State private var heightText = ""
    @State private var selectedScaleIndex = 0

    private var native: CGSize? { model.redNativeOrientedPixelSize }

    private var changed: Bool {
        draft != model.redResolutionSetting ||
        (draft.mode == .scaled && selectedScaleIndex != model.resolutionIndex)
    }

    private var canSave: Bool {
        changed && (draft.mode != .custom || draft.customIsValid)
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 12) {
                    Text("Display resolution")
                        .font(.headline)
                    modeRow(.andd, title: "Automatic Native Device Display (ANDD)",
                            subtitle: "Detect and use this device's physical screen pixels")
                    if let native {
                        Label(
                            "\(Int(native.width.rounded())) × \(Int(native.height.rounded())) pixels · \(RedDeviceDisplay.modelLabel)",
                            systemImage: "iphone.gen3")
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                            .accessibilityIdentifier("red-native-pixel-dimensions")
                    } else {
                        Text("Physical screen dimensions will be read from this window.")
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                    }
                    modeRow(.custom, title: "Custom resolution",
                            subtitle: "Enter your own width and height in pixels")
                    if draft.mode == .custom {
                        customEditor
                    }
                    modeRow(.scaled, title: "Scaled resolution",
                            subtitle: "Optional lower resolutions for older or slower devices")
                    if draft.mode == .scaled {
                        scaledChoices
                    }
                    Text("The new resolution applies the next time Android starts. Very high custom resolutions may use more graphics memory.")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                        .padding(.top, 6)
                }
                .padding(16)
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("Resolution")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel", role: .cancel) { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        guard canSave else { return }
                        if draft.mode == .scaled {
                            model.chooseResolution(model.resolutionChoices.scale(at: selectedScaleIndex))
                        }
                        model.redResolutionSetting = draft
                        dismiss()
                    }
                    .fontWeight(.semibold)
                    .disabled(!canSave)
                    .accessibilityIdentifier("red-resolution-save")
                }
            }
        }
        .presentationDetents([.large])
        .onAppear {
            draft = model.redResolutionSetting
            selectedScaleIndex = model.resolutionIndex
            widthText = String(draft.width)
            heightText = String(draft.height)
        }
    }

    private func modeRow(_ mode: RedResolutionMode, title: String, subtitle: String) -> some View {
        Button {
            if mode == .custom && draft.mode != .custom {
                // A new custom choice begins with this phone's native pixels.
                if draft.width == 1080 && draft.height == 1920 {
                    draft.seedFromNative(native)
                }
                widthText = String(draft.width)
                heightText = String(draft.height)
            }
            draft.mode = mode
        } label: {
            HStack(spacing: 12) {
                Image(systemName: draft.mode == mode ? "checkmark.circle.fill" : "circle")
                    .font(.title3)
                    .foregroundStyle(draft.mode == mode ? Color.accentColor : Color.secondary)
                VStack(alignment: .leading, spacing: 3) {
                    Text(title).font(.subheadline.weight(.semibold))
                    Text(subtitle).font(.caption).foregroundStyle(.secondary)
                }
                Spacer(minLength: 0)
            }
            .padding(14)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Color(.secondarySystemGroupedBackground), in: .rect(cornerRadius: 16))
            .contentShape(.rect)
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier("red-resolution-mode-\(mode.rawValue)")
    }

    private var customEditor: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 10) {
                VStack(alignment: .leading, spacing: 5) {
                    Text("Width").font(.caption).foregroundStyle(.secondary)
                    TextField("Width", text: widthBinding)
                        .keyboardType(.numberPad)
                        .textFieldStyle(.roundedBorder)
                        .accessibilityIdentifier("red-custom-width")
                }
                Button {
                    draft.setLinked(!draft.linked)
                } label: {
                    Image(systemName: draft.linked ? "link" : "link.slash")
                        .font(.title3.weight(.medium))
                        .frame(width: 40, height: 40)
                }
                .accessibilityLabel(draft.linked ? "Unlock width and height" : "Lock aspect ratio")
                .accessibilityValue(draft.linked ? "Linked" : "Independent")
                .accessibilityIdentifier("red-custom-aspect-chain")
                VStack(alignment: .leading, spacing: 5) {
                    Text("Height").font(.caption).foregroundStyle(.secondary)
                    TextField("Height", text: heightBinding)
                        .keyboardType(.numberPad)
                        .textFieldStyle(.roundedBorder)
                        .accessibilityIdentifier("red-custom-height")
                }
            }
            Text(draft.linked
                 ? "Linked: changing either dimension preserves the selected aspect ratio."
                 : "Unlinked: width and height can be adjusted independently.")
                .font(.footnote)
                .foregroundStyle(.secondary)
            if !draft.customIsValid {
                Label("Each side must be 256–4095 pixels, with no more than 16.7 million pixels total.",
                      systemImage: "exclamationmark.triangle")
                    .foregroundStyle(.orange)
                    .font(.footnote)
            }
        }
        .padding(14)
        .background(Color(.secondarySystemGroupedBackground), in: .rect(cornerRadius: 16))
    }

    private var widthBinding: Binding<String> {
        Binding(get: { widthText }, set: { text in
            widthText = text
            draft.setWidth(Int(text) ?? 0)
            if draft.linked { heightText = String(draft.height) }
        })
    }

    private var heightBinding: Binding<String> {
        Binding(get: { heightText }, set: { text in
            heightText = text
            draft.setHeight(Int(text) ?? 0)
            if draft.linked { widthText = String(draft.width) }
        })
    }

    private var scaledChoices: some View {
        VStack(spacing: 0) {
            ForEach((0..<model.resolutionChoices.count).reversed(), id: \.self) { index in
                Button {
                    selectedScaleIndex = index
                } label: {
                    HStack {
                        Image(systemName: selectedScaleIndex == index ? "checkmark.circle.fill" : "circle")
                            .foregroundStyle(selectedScaleIndex == index ? Color.accentColor : Color.secondary)
                        if let layout = model.resolutionLayout(at: index) {
                            Text("\(layout.width) × \(layout.height)").monospacedDigit()
                        } else {
                            Text(model.resolutionChoices.scale(at: index).text)
                        }
                        Spacer()
                    }
                    .padding(12)
                    .contentShape(.rect)
                }
                .buttonStyle(.plain)
                .accessibilityIdentifier("red-scaled-resolution-\(index)")
                if index > 0 { Divider() }
            }
        }
        .background(Color(.secondarySystemGroupedBackground), in: .rect(cornerRadius: 16))
    }
}
