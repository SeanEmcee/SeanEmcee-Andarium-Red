// SPDX-License-Identifier: GPL-2.0-or-later
import Foundation
import Network

/// Observes the iPhone's *usable* Network.framework path. The ADB relay
/// reports Wi-Fi/cellular/offline to the Red Android settings provider.
/// It deliberately does not shut down the virtual NIC: that is the guest's
/// underlying transport for BOTH Wi-Fi and cellular on iOS.
@MainActor
final class RedHostNetworkBridge {
    private let deliver: @MainActor (String) async -> Void
    private let queue = DispatchQueue(label: "andarium.red.host-network", qos: .utility)
    private var monitor: NWPathMonitor?
    private var heartbeat: Task<Void, Never>?
    private var currentStatus: String?

    init(deliver: @escaping @MainActor (String) async -> Void) {
        self.deliver = deliver
    }

    nonisolated static func status(for path: NWPath) -> String {
        guard path.status == .satisfied else { return "offline" }
        // Interface type describes a usable route, including when an iOS VPN
        // tunnels through the radio. It cannot reveal Wi-Fi SSID, availability
        // of other hotspots, or iOS's physical radio power-toggle state.
        if path.usesInterfaceType(.wifi) { return "wifi" }
        if path.usesInterfaceType(.cellular) { return "cellular" }
        return "other"
    }

    func start() {
        stop()
        let newMonitor = NWPathMonitor()
        newMonitor.pathUpdateHandler = { [weak self] path in
            let newStatus = Self.status(for: path)
            Task { @MainActor [weak self] in
                self?.update(newStatus)
            }
        }
        monitor = newMonitor
        newMonitor.start(queue: queue)
    }

    private func update(_ status: String) {
        guard monitor != nil, currentStatus != status else { return }
        currentStatus = status
        heartbeat?.cancel()
        // 25-second renewals prevent a stopped iOS host from leaving a
        // permanently stale "Wi-Fi connected" badge in the Android guest.
        heartbeat = Task { [weak self] in
            while !Task.isCancelled {
                guard let self else { break }
                await self.deliver(status)
                do { try await Task.sleep(for: .seconds(25)) }
                catch { break }
            }
        }
    }

    func stop() {
        monitor?.cancel()
        monitor = nil
        heartbeat?.cancel()
        heartbeat = nil
        currentStatus = nil
    }
}
