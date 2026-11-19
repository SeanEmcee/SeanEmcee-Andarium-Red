// SPDX-License-Identifier: Apache-2.0
package dev.twoyi.redlauncher;

public final class RedHostTransportStatusHarness {
    private static int assertions = 0;
    private static void check(boolean expression, String message) {
        if (!expression) throw new AssertionError(message);
        assertions++;
    }

    public static void main(String[] unused) {
        for (String valid : new String[]{"wifi","cellular","wired","other","offline"}) {
            check(RedHostTransportStatus.isHostValue(valid), valid + " rejected");
        }
        for (String invalid : new String[]{null, "", "unknown", "VirtWifi", "wifi;reboot", "lte", "WiFi"}) {
            check(!RedHostTransportStatus.isHostValue(invalid), "Untrusted value accepted");
        }
        check(RedHostTransportStatus.title("wifi").contains("Wi-Fi"), "Wi-Fi label inaccurate");
        check(RedHostTransportStatus.title("cellular").contains("cellular"), "Cellular label inaccurate");
        check(RedHostTransportStatus.detail("cellular").contains("not carrying"), "Cellular disclosure missing");
        check(RedHostTransportStatus.title("offline").contains("unavailable"), "No-path label inaccurate");
        check(RedHostTransportStatus.title("unknown").contains("pending"), "Unknown label inaccurate");
        System.out.println("RED_HOST_TRANSPORT_" + assertions + "_PASS");
    }
}
