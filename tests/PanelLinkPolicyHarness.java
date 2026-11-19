// SPDX-License-Identifier: Apache-2.0
import dev.twoyi.redlauncher.PanelLinkPolicy;
public final class PanelLinkPolicyHarness {
    private static int count=0;
    private static void equal(String a,String b) { if (!a.equals(b))throw new AssertionError(a+" != "+b);count++; }
    private static void reject(String s) { try { PanelLinkPolicy.normalized(s); throw new AssertionError("accepted "+s); }
        catch (IllegalArgumentException expected) { count++; }}
    public static void main(String[] args) {
        equal(PanelLinkPolicy.normalized("example.org"),"https://example.org");
        equal(PanelLinkPolicy.normalized("https://example.org/path?q=1"),"https://example.org/path?q=1");
        equal(PanelLinkPolicy.normalized("http://localhost:8080"),"http://localhost:8080");
        reject("javascript:alert(1)"); reject("file:///etc/passwd"); reject("https://user:pass@example.org");
        reject("https://example.org\\attacker"); reject("example.org\ninvalid"); reject("  ");
        reject("https://"); reject("data:text/html,payload"); reject("https://example.org:99999");
        System.out.println(count+"/"+count+" PanelLinkPolicy checks passed");
    }
}
