// SPDX-License-Identifier: Apache-2.0
package dev.twoyi.redlauncher;

/** Lightweight, deterministic responsive layout sizing.
 * Unit-free arithmetic; actual pixels come from Android display metrics.
 */
final class DashboardGridPolicy {
    private DashboardGridPolicy() {}

    static int columns(int availablePixels, int desiredCellPixels) {
        if (availablePixels <= 0 || desiredCellPixels <= 0) return 1;
        return Math.max(1, Math.min(4, availablePixels / desiredCellPixels));
    }

    static int cellWidth(int availablePixels, int desiredCellPixels) {
        int safeWidth = Math.max(1, availablePixels);
        return Math.max(1, safeWidth / columns(safeWidth, desiredCellPixels));
    }
}
