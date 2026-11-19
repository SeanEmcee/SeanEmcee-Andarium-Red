// SPDX-License-Identifier: GPL-2.0-or-later
import AndariumCore

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
