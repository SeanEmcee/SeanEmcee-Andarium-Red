// SPDX-License-Identifier: Apache-2.0
package dev.twoyi.redlauncher;

import java.util.Locale;
import java.util.UUID;

/** Wire contract shared by Android HOME and the native Nexaris host.
 * Strict finite destination list: never host URLs, file paths, commands,
 * process launch arguments, or untrusted names. No IPA executes in Android.
 */
public final class HostLaunchWire {
    public static final String AUTHORITY = "dev.twoyi.redlauncher.host";
    public static final String[] ROUTES = {
        "nexaris", "urlos", "rapbox", "rapkeys", "settings"
    };

    public static boolean allowed(String name) {
        if (name == null) return false;
        for (String valid : ROUTES) if (valid.equals(name)) return true;
        return false;
    }

    public static String event(String route) {
        if (!allowed(route)) throw new IllegalArgumentException("Invalid host app");
        return "v1:" + UUID.randomUUID().toString().replace("-", "") + ":" + route;
    }

    public static String eventId(String event) {
        if (event == null || !event.matches(
                "v1:[0-9a-f]{32}:(nexaris|urlos|rapbox|rapkeys|settings)")) {
            return null;
        }
        return event.substring(3, 35);
    }

    public static String eventRoute(String event) {
        if (eventId(event) == null) return null;
        return event.substring(36);
    }

    public static boolean matchesAck(String event, String id) {
        return id != null && id.equals(eventId(event));
    }

    private HostLaunchWire() {}
}
