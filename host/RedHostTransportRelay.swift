// SPDX-License-Identifier: GPL-2.0-or-later
import Foundation
import Network

/// The ACTIVE path iOS actually selected for the Andarium host process.
/// This is not an iOS Wi-Fi radio switch or a nearby SSID scanner.
enum RedHostTransportRoute: String, Sendable {
    case wifi, cellular, wired, other, offline

    static func active(_ path: NWPath) -> Self {
        guard path.status == .satisfied else { return .offline }
        if path.usesInterfaceType(.wifi) { return .wifi }
        if path.usesInterfaceType(.cellular) { return .cellular }
        if path.usesInterfaceType(.wiredEthernet) { return .wired }
        return .other
    }
}

/// Watches only while an Android session has booted. A route change replaces
/// the pending status; the guest is never given an arbitrary shell command.
/// Kernarium's existing libslirp handles the REAL host path migration.
/// VirtWifi is retained as the guest-side transport underlay, not passed off
/// as the phone's physical Wi-Fi connection.
@MainActor
final class RedHostTransportRelay {
    private let send: @MainActor (RedHostTransportRoute) async -> Bool
    private let queue = DispatchQueue(label: "dev.andarium.red.host-network", qos: .utility)
    private var monitor: NWPathMonitor?
    private var generation: UInt64 = 0
    private var pending: RedHostTransportRoute?
    private var published: RedHostTransportRoute?
    private var worker: Task<Void, Never>?

    init(send: @escaping @MainActor (RedHostTransportRoute) async -> Bool) {
        self.send = send
    }

    func start() {
        guard monitor == nil else { return }
        generation &+= 1
        let current = generation
        let watcher = NWPathMonitor()
        monitor = watcher
        watcher.pathUpdateHandler = { [weak self] path in
            let route = RedHostTransportRoute.active(path)
            Task { @MainActor [weak self] in
                guard let self, self.monitor != nil, self.generation == current else { return }
                self.enqueue(route)
            }
        }
        watcher.start(queue: queue)
    }

    func stop() {
        generation &+= 1
        monitor?.cancel()
        monitor = nil
        worker?.cancel()
        worker = nil
        pending = nil
        published = nil
    }

    private func enqueue(_ route: RedHostTransportRoute) {
        if route == published && pending == nil { return }
        pending = route
        if worker == nil {
            worker = Task { [weak self] in await self?.drain() }
        }
    }

    private func drain() async {
        let started = generation
        while !Task.isCancelled && generation == started, let route = pending {
            pending = nil
            var succeeded = false
            // sys.boot_completed may precede the host's ADB/provisioning
            // readiness. Retry a few times without a permanent polling loop.
            for attempt in 0..<5 {
                if Task.isCancelled || generation != started || pending != nil { break }
                if await send(route) { succeeded = true; break }
                if attempt < 4 { try? await Task.sleep(for: .seconds(1)) }
            }
            if succeeded && pending == nil { published = route }
        }
        if generation == started { worker = nil }
    }
}
