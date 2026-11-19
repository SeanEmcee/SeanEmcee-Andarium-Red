// SPDX-License-Identifier: Apache-2.0
package dev.twoyi.redlauncher;

/** Pure Java formatting for live guest status; no invented battery values. */
public final class HomeStatusFormat {
    private HomeStatusFormat() {}
    public static String battery(int level) {
        return level >= 0 && level <= 100 ? level + "%" : "Battery —";
    }
}
