// SPDX-License-Identifier: Apache-2.0
package dev.twoyi.redlauncher;

/** The Android UI reports what the iOS host actually selected, not a fake SSID.
 * Kept Android-SDK-free so the wire policy can be unit tested on any JDK. */
final class HostNetworkState {
    static final String WIFI = "wifi";
    static final String CELLULAR = "cellular";
    static final String OFFLINE = "offline";
    static final String OTHER = "other";
    static final String UNKNOWN = "unknown";

    static boolean valid(String value) {
        return WIFI.equals(value) || CELLULAR.equals(value) ||
            OFFLINE.equals(value) || OTHER.equals(value);
    }

    static String description(String state) {
        if (WIFI.equals(state)) return "Connected over iPhone Wi-Fi";
        if (CELLULAR.equals(state)) return "Wi-Fi inactive; iPhone cellular data active";
        if (OFFLINE.equals(state)) return "iPhone network offline";
        if (OTHER.equals(state)) return "iPhone uses another network path (e.g. wired or tunnel)";
        return "iPhone network status not available";
    }

    private HostNetworkState() {}
}
