# Andarium Red v17 — Android Home → native Nexaris apps

## User-facing design

Android 17 Home displays **Nexaris, URL OS, Rap Box, Rap Keys, Settings** together in a host-app row, alongside the Android guest's normal applications such as Magisk, Termux, F-Droid, App Manager, HeliBoard and the browser.

The Android 17 build now also contains five actual **LAUNCHER activity aliases** (HostNexaris, HostURLOS, HostRapBox, HostRapKeys, HostSettings), backed by a single checked `HostShortcutActivity`, with five separate XML vector icons in `launcher_src/res/drawable/`. These can appear in any Android launcher or activity picker that indexes LAUNCHER activities. They have no IPA or executable iOS code inside the guest.

These five icons are Android **launch controls**, not IPA packages or app compatibility emulation. Android makes a request to the already-running **native Nexaris host shell**. Only Nexaris owns and opens the native app views. Android stays booted; selecting a host app is not a new Android boot.

**Nexaris** returns to native **My Device** by default. The native Nexaris Andarium settings include **Return to previous tab**. The other four requests open their native destinations. The actual fade transition is implemented in the private Nexaris source, not by an Android animation or fake preview.

## Exactly permitted guest-to-host messages

The platform-built Android launcher includes `HostLaunchWire.java` and `HostLaunchBridgeProvider.java`, exposed at:

`content://dev.twoyi.redlauncher.host/launch`

- `enqueue`: called **only by the launcher's own Android UID**, with one of `nexaris`, `urlos`, `rapbox`, `rapkeys`, `settings`. One pending message maximum. Repeated taps do not replace the first.
- `next`: called only from the host's authenticated guest ADB shell (Android shell UID 2000 or root UID 0). `--arg 1000` makes the call wait up to one second; a new tap wakes it promptly, without busy polling.
- `ack`: called only from the authenticated shell with the message's exact 32-character hexadecimal ID. An incorrect or stale acknowledgement does not clear the request.

Message: `Result: Bundle[{event=v1:<32 lowercase hex>:nexaris}]` or `Result: Bundle[{event=~}]`.

Mailbox age limit: 120 seconds. No URLs, filenames, arbitrary app bundle identifiers, shell payloads, VPN actions, root operations or signing operations can be requested. This is a narrow routing API, **not** a general-purpose command channel. Magisk root can compromise guest integrity, so the native host MUST treat every guest message as untrusted and enforce the destination allowlist.

The provider is declared in the native Android launcher manifest and is compiled into the **rebuilt Android 17 image**. An upstream Andarium/Lineage image without these changes will not have the mailbox or the five icons.

## Native iOS integration point

`host/RedHostRouteRuntime.swift` is installed into `Andarium/Andarium/Live/` with the existing clipboard ADB bridge. It exposes:
- `LiveRuntime.redReadNativeHostLaunchMessage()`
- `LiveRuntime.redAcknowledgeNativeHostLaunchMessage(id:)`

A genuine Nexaris-embedded Andarium driver must implement `NexarisAndariumGuestRuntime.supportsHostLaunchRequests = true`, `readHostLaunchMessage()` and `acknowledgeHostLaunchMessage(id:)`, using these real runtime methods. **The Nexaris repository currently has no registered compiled Andarium driver. The message channel and fade source exist; on-device launch is not yet proven.** The registry explicitly refuses to claim support while the driver is absent.

The fade view uses the real Nexaris UI beneath the actual guest UIViewController. Route to the native host first, fade Android's overlay opacity to zero (~0.26 s), then relinquish the overlay. It must NOT call `UIApplication.open` to launch a second IPA.

## Development verification

- Exact committed `HostLaunchWire.java` + actual Java harness: **45/45 checks passed** on a Linux JDK. Byte-for-byte Git blob hashes matched the private GitHub repository.
- Exact committed `NexarisAndroidHostWire.swift`, including ADB shell closure and bounded-wait command, plus Swift harness: **25/25 checks passed** on Linux Swift. Byte-for-byte Git blob hashes matched. This does not typecheck the SwiftUI/iOS Nexaris view or claim Xcode success.
- `tools/host_route_provider_behavior_test.py` adds 24 Android-shaped Java behavior checks for UID gating, busy mailbox, acknowledgement, stale-event refusal and exact launcher-alias mappings. These run from the complete working tree's first-build gate.
- No Android image, signed Nexaris/Andarium IPA, or physical-iPhone fade/fps measurement was produced.

## Native-shell device acceptance

Build and boot the modified Android 17 image in the actual Nexaris/Andarium runtime. Confirm each of the five icons routes to the corresponding real host destination, Android is not rebooted, the same guest data remains intact, route replies are acknowledged exactly once, stale/foreign events are refused, and returning to Android does not cause a new guest boot. Verify the Nexaris return-tab setting in both modes. Record tap-to-host latency and the Android-to-native crossfade at 60/120 Hz, including no black frame or duplicate foreground UIWindow.

**Release gate: NO-GO until the compiled Nexaris Andarium adapter, real guest image, and on-device acceptance succeed.**

## Source packaging requirements

The launcher Soong `android_app` includes `srcs: ["java/**/*.java"]`, `asset_dirs: ["assets"]`, **`resource_dirs: ["res"]`**, and the modified Android manifest. Integration fails before writing the upstream tree if any of the five launcher aliases, their vector icon resources, the mailbox provider, or the alias activity source is missing. The host navigation transition remains in Nexaris; Android's launchers only send intent names.

A concrete but **not yet registered** `NexarisAndariumLiveRuntimeDriver` in Nexaris can bridge a real running Android 17 engine's start/stop/display/accent/authenticated ADB shell operations. It refuses mailbox reads unless the linked driver confirms boot completion. The actual engine and Android 17 guest image still must be compiled and linked.
