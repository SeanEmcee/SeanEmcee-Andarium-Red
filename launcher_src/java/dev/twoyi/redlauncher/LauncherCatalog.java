// SPDX-License-Identifier: Apache-2.0
package dev.twoyi.redlauncher;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;

/** Deterministic, Android-SDK-independent app ordering and filtering.
 * Actual presence and launchability must come from PackageManager; this class
 * never invents applications or interprets an installed Magisk manager as root.
 */
public final class LauncherCatalog {
    private LauncherCatalog() {}

    public static final class App {
        public final String label;
        public final String packageName;
        public App(String label, String packageName) {
            this.label = label == null ? "" : label;
            this.packageName = packageName == null ? "" : packageName;
        }
    }

    public static List<App> filter(List<App> installedAndLaunchable, String query) {
        String needle = query == null ? "" : query.trim().toLowerCase(Locale.ROOT);
        ArrayList<App> matches = new ArrayList<>();
        for (App app : installedAndLaunchable) {
            String label = app.label.toLowerCase(Locale.ROOT);
            String name = app.packageName.toLowerCase(Locale.ROOT);
            if (needle.isEmpty() || label.contains(needle) || name.contains(needle)) {
                matches.add(app);
            }
        }
        matches.sort(Comparator.comparing((App a) -> a.label.toLowerCase(Locale.ROOT))
                .thenComparing(a -> a.packageName));
        return Collections.unmodifiableList(matches);
    }

    public static String guestStatus(String androidVersion, boolean managerInstalled) {
        // "Rooted" is NOT inferred from presence of the Magisk manager.
        String version = androidVersion == null || androidVersion.isEmpty() ? "unknown" : androidVersion;
        return "Android " + version + " | Magisk manager: "
                + (managerInstalled ? "installed" : "not installed") + " | Root: not verified";
    }
}
