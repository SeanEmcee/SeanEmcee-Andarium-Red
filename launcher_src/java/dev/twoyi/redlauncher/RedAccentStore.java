// SPDX-License-Identifier: Apache-2.0
package dev.twoyi.redlauncher;

import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;

/** Cosmetic guest accent handoff. This never asserts iOS privileges or guest root.
 * The real host integration must explicitly launch the guest with EXTRA_RGB;
 * the separately compiled iOS runtime adapter is not part of this package.
 */
final class RedAccentStore {
    static final String EXTRA_RGB = "dev.twoyi.redlauncher.NEXARIS_ACCENT_RGB";
    static final int DEFAULT_RGB = 0xF22B43;
    private static final String PREFS = "andarium_red_theme";
    private static final String KEY = "nexaris_accent_rgb";

    private RedAccentStore() {}

    static boolean validRGB(int rgb) { return rgb >= 0 && rgb <= 0xFFFFFF; }

    static int load(Context context) {
        int saved = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getInt(KEY, DEFAULT_RGB);
        return validRGB(saved) ? saved : DEFAULT_RGB;
    }

    static boolean acceptLaunchAccent(Context context, Intent intent) {
        if (intent == null || !intent.hasExtra(EXTRA_RGB)) return false;
        final int color = intent.getIntExtra(EXTRA_RGB, -1);
        return acceptRGB(context, color);
    }

    static boolean acceptRGB(Context context, int color) {
        if (context == null || !validRGB(color)) return false;
        // Do not acknowledge a theme change until it is durably saved.
        // commit() avoids losing the update if the guest shuts down immediately.
        SharedPreferences.Editor editor = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit();
        return editor.putInt(KEY, color).commit();
    }

    static int color(int rgb) {
        return Color.rgb((rgb >> 16) & 255, (rgb >> 8) & 255, rgb & 255);
    }
}
