import dev.twoyi.redlauncher.HomeStatusFormat;
public final class HomeStatusHarness {
    private static int passed = 0;
    private static void check(boolean yes) { if (!yes) throw new AssertionError("status formatter failed"); passed++; }
    public static void main(String[] args) {
        check(HomeStatusFormat.battery(0).equals("0%"));
        check(HomeStatusFormat.battery(74).equals("74%"));
        check(HomeStatusFormat.battery(100).equals("100%"));
        check(HomeStatusFormat.battery(-1).equals("Battery —"));
        check(HomeStatusFormat.battery(101).equals("Battery —"));
        System.out.println(passed + "/5 live-status tests PASS");
    }
}
