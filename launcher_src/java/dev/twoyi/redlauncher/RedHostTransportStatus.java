// SPDX-License-Identifier: Apache-2.0
package dev.twoyi.redlauncher;

/** Only facts reported by the iOS host's active network path.
 * The guest's VirtWifi underlay is never a physical iPhone radio.
 */
final class RedHostTransportStatus {
    static final String UNKNOWN = "unknown";
    static final String WIFI = "wifi";
    static final String CELLULAR = "cellular";
    static final String WIRED = "wired";
    static final String OTHER = "other";
    static final String OFFLINE = "offline";

    static boolean isHostValue(String value) {
        return WIFI.equals(value) || CELLULAR.equals(value)
            || WIRED.equals(value) || OTHER.equals(value) || OFFLINE.equals(value);
    }

    static String title(String value) {
        if (WIFI.equals(value)) return "iPhone Wi-Fi connected";
        if (CELLULAR.equals(value)) return "iPhone cellular data";
        if (WIRED.equals(value)) return "iPhone wired network";
        if (OTHER.equals(value)) return "iPhone network (other route)";
        if (OFFLINE.equals(value)) return "iPhone network unavailable";
        return "iPhone network status pending";
    }

    static String detail(String value) {
        if (WIFI.equals(value)) return "Android internet uses the host's active Wi-Fi path.";
        if (CELLULAR.equals(value)) return "Host Wi-Fi is not carrying this path. Android internet uses the iPhone's cellular path.";
        if (WIRED.equals(value)) return "Android internet uses the iPhone's active wired path.";
        if (OTHER.equals(value)) return "A host connection is active, but its underlying interface is not identified.";
        if (OFFLINE.equals(value)) return "No usable iPhone network path. Android internet may be unavailable.";
        return "Waiting for the iPhone to report its active network connection.";
    }

    private RedHostTransportStatus() {}
}
