import dev.twoyi.redlauncher.LauncherCatalog;
import java.util.Arrays;
import java.util.List;

public final class LauncherCatalogHarness {
    private static void check(boolean ok, String why) {
        if (!ok) throw new AssertionError(why);
    }
    public static void main(String[] args) {
        List<LauncherCatalog.App> installed = Arrays.asList(
            new LauncherCatalog.App("Titanium Browser", "org.example.titanium"),
            new LauncherCatalog.App("Android Settings", "com.android.settings"),
            new LauncherCatalog.App("Magisk", "com.topjohnwu.magisk"));
        check(LauncherCatalog.filter(installed, "").size()==3, "all launchable apps");
        check(LauncherCatalog.filter(installed, "MAGISK").get(0).label.equals("Magisk"), "case-independent search");
        check(LauncherCatalog.filter(installed, "com.android").get(0).label.equals("Android Settings"), "package name lookup");
        check(LauncherCatalog.filter(installed, "Firefox").isEmpty(), "never list missing app");
        check(LauncherCatalog.filter(installed, null).get(0).label.equals("Android Settings"), "deterministic sort");
        check(LauncherCatalog.guestStatus("17", true).contains("Root: not verified"), "no false root claim");
        check(LauncherCatalog.guestStatus("17", false).contains("not installed"), "missing manager not claimed");
        System.out.println("LauncherCatalog: 7/7 assertions passed");
    }
}
