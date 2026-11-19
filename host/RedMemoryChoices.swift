// SPDX-License-Identifier: GPL-2.0-or-later
import AndariumCore
import SwiftUI

/// All choices derive from Kernarium's *runtime* budgets for this device.
/// Pushing guest RAM to the raw ceiling can starve GPU memory or trigger
/// iOS jetsam; the highest no-warning choice keeps both host and GPU headroom.
enum RedMemoryChoices {
    static func qualityMiB(on host: HostDevice, cores: Int, cameraLive: Bool = false) -> Int {
        min(host.memory.safeMemoryMiB(vCPUs: cores),
            host.memory.graphicsLineMiB(vCPUs: cores, cameraLive: cameraLive))
    }

    /// Retain Kernarium's tested default guest RAM while leaving extra room
    /// for heavy graphics when RAM and GPU headroom trade off.
    static func graphicsPriorityMiB(on host: HostDevice, cores: Int, cameraLive: Bool = false) -> Int {
        min(host.memory.defaultMemoryMiB(vCPUs: cores),
            qualityMiB(on: host, cores: cores, cameraLive: cameraLive))
    }

    static func safeMiB(on host: HostDevice, cores: Int) -> Int {
        host.memory.safeMemoryMiB(vCPUs: cores)
    }

    static func ceilingMiB(on host: HostDevice, cores: Int) -> Int {
        host.memory.maximumMiB(vCPUs: cores)
    }

    static func value(for preset: RedMemoryPreset, on host: HostDevice, cores: Int,
                      cameraLive: Bool = false) -> Int {
        switch preset {
        case .quality: return qualityMiB(on: host, cores: cores, cameraLive: cameraLive)
        case .graphics: return graphicsPriorityMiB(on: host, cores: cores, cameraLive: cameraLive)
        case .safe: return safeMiB(on: host, cores: cores)
        case .deviceLimit: return ceilingMiB(on: host, cores: cores)
        }
    }

    static func fresh(on host: HostDevice) -> Guest {
        var guest = Guest.fresh(on: host)
        guest.memoryMiB = value(for: RedMemoryPresetStore.load(),
                                on: host, cores: guest.cores)
        return guest
    }
}


/// Presets are truthful about the difference between a safe GPU/host budget
/// and the device's theoretical allocatable RAM ceiling.
struct RedMemoryPresetRow: View {
    @Binding var guest: Guest
    let host: HostDevice
    var cameraLive = false
    @State private var preferredPreset = RedMemoryPresetStore.load()

    var body: some View {
        VStack(alignment: .leading, spacing: 9) {
            Text("Memory profiles").font(.subheadline.weight(.semibold))
            ViewThatFits(in: .horizontal) {
                HStack(spacing: 8) { presetButtons }
                VStack(alignment: .leading, spacing: 8) { presetButtons }
            }
            Menu {
                ForEach(RedMemoryPreset.allCases) { option in
                    Button {
                        preferredPreset = option
                        RedMemoryPresetStore.save(option)
                    } label: {
                        if preferredPreset == option {
                            Label(option.title, systemImage: "checkmark")
                        } else {
                            Text(option.title)
                        }
                    }
                }
            } label: {
                HStack {
                    Text("Default for new guests")
                    Spacer()
                    Text(preferredPreset.title).foregroundStyle(.secondary)
                    Image(systemName: "chevron.up.chevron.down")
                }
                .font(.footnote)
                .padding(10)
                .background(Color(.tertiarySystemGroupedBackground),
                            in: .rect(cornerRadius: 12))
            }
            .accessibilityIdentifier("red-memory-new-guest-default")
            Text("Device limit is the highest allocation the runtime permits, not a guarantee of stability. iOS may close the app, and less memory may remain for graphics.")
                .font(.footnote)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
            if host.memory.risk(guest.memoryMiB, vCPUs: guest.cores, cameraLive: cameraLive) != .none {
                Label("Current memory selection has a graphics or app-closing risk.",
                      systemImage: "exclamationmark.triangle.fill")
                    .foregroundStyle(.orange)
                    .font(.footnote)
            }
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(.secondarySystemGroupedBackground), in: .rect(cornerRadius: 24))
    }

    @ViewBuilder private var presetButtons: some View {
        preset("Max quality",
               mib: RedMemoryChoices.qualityMiB(on: host, cores: guest.cores, cameraLive: cameraLive))
        preset("Graphics priority",
               mib: RedMemoryChoices.graphicsPriorityMiB(on: host, cores: guest.cores, cameraLive: cameraLive))
        preset("High RAM", mib: RedMemoryChoices.safeMiB(on: host, cores: guest.cores))
        preset("Device limit", mib: RedMemoryChoices.ceilingMiB(on: host, cores: guest.cores))
    }

    private func preset(_ title: String, mib: Int) -> some View {
        Button {
            guest.memoryMiB = mib
        } label: {
            VStack(spacing: 2) {
                Text(title).font(.footnote.weight(.semibold))
                Text(Formats.size(mib: mib)).font(.caption2).monospacedDigit()
            }
            .padding(.horizontal, 10)
            .padding(.vertical, 8)
            .frame(maxWidth: .infinity)
            .background(guest.memoryMiB == mib ? Color.accentColor.opacity(0.16) :
                        Color(.tertiarySystemGroupedBackground), in: .rect(cornerRadius: 12))
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier(
            title == "Max quality" ? "red-memory-quality" :
            title == "Graphics priority" ? "red-memory-graphics" :
            title == "High RAM" ? "red-memory-safe" : "red-memory-device-max")
    }
}
