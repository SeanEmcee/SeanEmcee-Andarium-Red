// SPDX-License-Identifier: Apache-2.0
package dev.twoyi.redlauncher;

import android.app.Activity;
import android.content.ComponentName;
import android.os.Bundle;
import android.widget.Toast;

/** Native-looking Android launcher aliases. Each is a redirect to Nexaris's
 * actual iOS host UI; it NEVER attempts to install or execute an IPA.
 *
 * The alias component is the only accepted routing input: extras, intent data,
 * incoming URLs and third-party-provided action strings are ignored.
 */
public final class HostShortcutActivity extends Activity {
    static String routeForAlias(String component) {
        if (component == null) return null;
        switch (component) {
            case "dev.twoyi.redlauncher.HostNexaris": return "nexaris";
            case "dev.twoyi.redlauncher.HostURLOS": return "urlos";
            case "dev.twoyi.redlauncher.HostRapBox": return "rapbox";
            case "dev.twoyi.redlauncher.HostRapKeys": return "rapkeys";
            case "dev.twoyi.redlauncher.HostSettings": return "settings";
            default: return null;
        }
    }

    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        ComponentName component = getIntent() == null ? null : getIntent().getComponent();
        String route = routeForAlias(component == null ? null : component.getClassName());
        if (route == null) {
            finish();
            return;
        }
        try {
            boolean accepted = HostLaunchBridgeProvider.request(this, route);
            if (!accepted) {
                Toast.makeText(this, "Nexaris host request pending or unavailable",
                               Toast.LENGTH_LONG).show();
            }
        } catch (RuntimeException unavailable) {
            Toast.makeText(this, "Nexaris host integration is unavailable",
                           Toast.LENGTH_LONG).show();
        } finally {
            finish();
        }
    }
}
