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

    static func safeMiB(on host: HostDevice, cores: Int) -> Int {
        host.memory.safeMemoryMiB(vCPUs: cores)
    }

    static func ceilingMiB(on host: HostDevice, cores: Int) -> Int {
        host.memory.maximumMiB(vCPUs: cores)
    }

    static func fresh(on host: HostDevice) -> Guest {
        var guest = Guest.fresh(on: host)
        guest.memoryMiB = qualityMiB(on: host, cores: guest.cores)
        return guest
    }
}


/// Presets are truthful about the difference between a safe GPU/host budget
/// and the device's theoretical allocatable RAM ceiling.
struct RedMemoryPresetRow: View {
    @Binding var guest: Guest
    let host: HostDevice
    var cameraLive = false

    var body: some View {
        VStack(alignment: .leading, spacing: 9) {
            Text("Memory profiles").font(.subheadline.weight(.semibold))
            ViewThatFits(in: .horizontal) {
                HStack(spacing: 8) { presetButtons }
                VStack(alignment: .leading, spacing: 8) { presetButtons }
            }
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
        .accessibilityIdentifier(title == "Max quality" ? "red-memory-quality" :
                                 title == "High RAM" ? "red-memory-safe" : "red-memory-device-max")
    }
}
