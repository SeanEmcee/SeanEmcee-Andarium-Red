package dev.twoyi.redlauncher;

public final class DashboardGridPolicyHarness {
    private static int checks;
    private static void check(boolean valid, String message) {
        if (!valid) throw new AssertionError(message);
        checks++;
    }

    public static void main(String[] args) {
        check(DashboardGridPolicy.columns(320, 80) == 4, "regular four columns");
        check(DashboardGridPolicy.columns(239, 80) == 2, "narrow two columns");
        check(DashboardGridPolicy.columns(160, 80) == 2, "minimum two columns");
        check(DashboardGridPolicy.columns(79, 80) == 1, "single column on tiny view");
        check(DashboardGridPolicy.columns(800, 80) == 4, "four column cap");
        check(DashboardGridPolicy.columns(0, 80) == 1, "zero size handled");
        check(DashboardGridPolicy.columns(320, 0) == 1, "invalid preference handled");
        for (int width = 1; width < 2000; width++) {
            int n = DashboardGridPolicy.columns(width, 80);
            int cell = DashboardGridPolicy.cellWidth(width, 80);
            check(n >= 1 && n <= 4 && n * cell <= width, "grid fits width="+width);
        }
        System.out.println("DASHBOARD_GRID_" + checks + "_PASS");
    }
}
