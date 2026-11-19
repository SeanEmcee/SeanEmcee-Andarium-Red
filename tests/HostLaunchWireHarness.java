// SPDX-License-Identifier: Apache-2.0
package dev.twoyi.redlauncher;

final class HostLaunchWireHarness {
    private static int checks;
    private static void check(boolean valid, String message) {
        if (!valid) throw new AssertionError(message);
        checks++;
    }
    public static void main(String[] args) {
        check(HostLaunchWire.ROUTES.length == 5, "five built-in host apps");
        for (String route : HostLaunchWire.ROUTES) {
            check(HostLaunchWire.allowed(route), "route allowed: " + route);
            String msg = HostLaunchWire.event(route);
            check(msg.startsWith("v1:"), "canonical wire prefix");
            check(route.equals(HostLaunchWire.eventRoute(msg)), "route roundtrip");
            String id = HostLaunchWire.eventId(msg);
            check(id != null && id.matches("[0-9a-f]{32}"), "random id");
            check(HostLaunchWire.matchesAck(msg, id), "valid ack");
            check(!HostLaunchWire.matchesAck(msg, "00000000000000000000000000000000"),
                  "wrong id cannot acknowledge event");
        }
        for (String route : new String[]{"shell", "openurl", "guest", "com.apple.settings",
                "../settings", "NEXARIS", "nexaris;rm", ""}) {
            check(!HostLaunchWire.allowed(route), "reject arbitrary target");
        }
        check(!HostLaunchWire.allowed(null), "reject null");
        check(HostLaunchWire.eventId("v1:bad:nexaris") == null, "bad id");
        check(HostLaunchWire.eventId("v2:00000000000000000000000000000000:nexaris")
                == null, "unsupported version");
        check(HostLaunchWire.eventId("v1:00000000000000000000000000000000:evil")
                == null, "unknown route");
        check(HostLaunchWire.eventId("v1:00000000000000000000000000000000:nexaris:evil")
                == null, "extra field");
        boolean rejected = false;
        try { HostLaunchWire.event("arbitrary"); }
        catch (IllegalArgumentException expected) { rejected = true; }
        check(rejected, "cannot encode arbitrary host destination");
        System.out.println("HOST_LAUNCH_WIRE_" + checks + "_PASS");
    }
}
