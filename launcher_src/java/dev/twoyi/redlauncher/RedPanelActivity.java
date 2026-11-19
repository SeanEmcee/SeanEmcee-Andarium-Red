// SPDX-License-Identifier: Apache-2.0
package dev.twoyi.redlauncher;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.Typeface;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.Settings;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.view.WindowManager;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

/** Real Android controls instead of screenshot-only Settings or browser areas.
 *  Runs only in the Android guest; no pretend iOS permission or Magisk root state.
 */
public final class RedPanelActivity extends Activity {
    public static final String EXTRA_PANEL = "dev.twoyi.redlauncher.PANEL";
    public static final String SETTINGS_PANEL = "settings";
    public static final String BROWSER_PANEL = "browser";
    private static final int BG = Color.rgb(1, 1, 2);
    private static final int CARD = Color.rgb(15, 15, 18);
    private int accent;
    private static final int SECONDARY = Color.rgb(172, 172, 180);
    private static final String TITANIUM_PACKAGE = "io.github.jqssun.helium";

    private LinearLayout content;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        accent = RedAccentStore.color(RedAccentStore.load(this));
        getWindow().setStatusBarColor(BG);
        getWindow().setNavigationBarColor(BG);
        getWindow().setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN, WindowManager.LayoutParams.FLAG_FULLSCREEN);
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.setBackgroundColor(BG);
        content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(dp(18), dp(24), dp(18), dp(38));
        scroll.addView(content);
        setContentView(scroll);
        if (BROWSER_PANEL.equals(getIntent().getStringExtra(EXTRA_PANEL))) buildBrowser();
        else buildSettings();
    }

    private int dp(float value) { return (int) (getResources().getDisplayMetrics().density * value + 0.5f); }

    private TextView text(String s, int sp, int color, boolean bold) {
        TextView t = new TextView(this);
        t.setText(s);
        t.setTextSize(sp);
        t.setTextColor(color);
        t.setGravity(Gravity.CENTER_VERTICAL);
        t.setTypeface(Typeface.DEFAULT, bold ? Typeface.BOLD : Typeface.NORMAL);
        return t;
    }

    private void top(String title, String detail) {
        TextView back = text("‹    ANDARIUM RED", 16, accent, true);
        back.setPadding(0, dp(8), 0, dp(18));
        back.setOnClickListener(v -> finish());
        content.addView(back);
        TextView name = text(title, 34, Color.WHITE, true);
        content.addView(name);
        TextView subtitle = text(detail, 13, SECONDARY, false);
        subtitle.setPadding(0, dp(6), 0, dp(22));
        content.addView(subtitle);
    }

    private void heading(String name) {
        TextView t = text(name.toUpperCase(), 12, accent, true);
        t.setPadding(dp(3), dp(18), 0, dp(8));
        content.addView(t);
    }

    private void row(String name, String description, View.OnClickListener action) {
        LinearLayout group = new LinearLayout(this);
        group.setOrientation(LinearLayout.VERTICAL);
        group.setPadding(dp(16), dp(13), dp(16), dp(13));
        group.setBackgroundColor(CARD);
        LinearLayout.LayoutParams groupParams = new LinearLayout.LayoutParams(-1, -2);
        groupParams.bottomMargin = dp(2);
        content.addView(group, groupParams);
        TextView title = text(name + "   ›", 16, Color.WHITE, true);
        group.addView(title);
        TextView detail = text(description, 12, SECONDARY, false);
        detail.setPadding(0, dp(4), 0, 0);
        group.addView(detail);
        if (action != null) {
            group.setOnClickListener(action);
            group.setClickable(true);
            group.setFocusable(true);
        }
    }

    private void setting(String name, String description, String action) {
        row(name, description, v -> openSetting(action));
    }

    private void openSetting(String action) {
        try { startActivity(new Intent(action)); }
        catch (ActivityNotFoundException e) {
            try { startActivity(new Intent(Settings.ACTION_SETTINGS)); }
            catch (ActivityNotFoundException ignored) { toast("Setting unavailable on this guest"); }
        }
    }

    private boolean isInstalled(String packageName) {
        try { getPackageManager().getPackageInfo(packageName, 0); return true; }
        catch (PackageManager.NameNotFoundException absent) { return false; }
    }

    private void openApp(String packageName) {
        Intent intent = getPackageManager().getLaunchIntentForPackage(packageName);
        if (intent == null) { toast("Install this app inside Android first"); return; }
        try { startActivity(intent); }
        catch (ActivityNotFoundException e) { toast("This Android app could not be opened"); }
    }

    private void buildSettings() {
        top("Settings", "ANDROID " + Build.VERSION.RELEASE + "  •  Native Android controls");
        row("Guest status", "Build: " + Build.DISPLAY + "  •  Security patch: " + Build.VERSION.SECURITY_PATCH
            + "  •  Root not verified", v -> rootInfo());
        heading("Android Settings");
        setting("Network & internet", "Virtual network and connections", Settings.ACTION_WIRELESS_SETTINGS);
        setting("Apps", "Installed apps, defaults and permissions", Settings.ACTION_APPLICATION_SETTINGS);
        setting("Notifications", "App alerts and notifications", Settings.ACTION_NOTIFICATION_SETTINGS);
        setting("Display", "Display resolution, brightness and theme", Settings.ACTION_DISPLAY_SETTINGS);
        setting("Storage", "Guest filesystem and free space", Settings.ACTION_INTERNAL_STORAGE_SETTINGS);
        setting("Privacy", "Android app permissions", Settings.ACTION_PRIVACY_SETTINGS);
        setting("Security", "Android security settings", Settings.ACTION_SECURITY_SETTINGS);
        setting("Accounts", "Guest accounts", Settings.ACTION_SYNC_SETTINGS);
        setting("Accessibility", "TalkBack and interface settings", Settings.ACTION_ACCESSIBILITY_SETTINGS);
        setting("System", "Languages, gestures and time", Settings.ACTION_SETTINGS);
        setting("About Android", "Android guest version and build", Settings.ACTION_DEVICE_INFO_SETTINGS);
        setting("Developer options", "Guest debugging tools", Settings.ACTION_APPLICATION_DEVELOPMENT_SETTINGS);
        heading("Apps and integrations");
        row("Magisk manager", isInstalled("com.topjohnwu.magisk") ? "Installed; root NOT assumed" : "Not installed", v -> openApp("com.topjohnwu.magisk"));
        row("Titanium Browser", isInstalled(TITANIUM_PACKAGE) ? "Open Chromium browser" : "Not installed", v -> openApp(TITANIUM_PACKAGE));
        row("HeliBoard keyboard", isInstalled("helium314.keyboard") ? "Manage installed input method" : "Not installed; set up after installation",
            v -> openSetting(Settings.ACTION_INPUT_METHOD_SETTINGS));
        row("iOS clipboard bridge", "Not an Android permission. Use the iOS host's explicit Copy/Paste controls.",
            v -> new AlertDialog.Builder(this).setTitle("Clipboard bridge")
                .setMessage("iOS clipboard access must be initiated in the Andarium host. Android cannot grant iOS permissions. This screen does not pretend the bridge is enabled.")
                .setPositiveButton("OK", null).show());
    }

    private void rootInfo() {
        new AlertDialog.Builder(this).setTitle("Guest root")
            .setMessage("Magisk Manager being installed does not mean Android has root. A userdebug guest may contain su, while Magisk-managed root requires a separately verified compatible boot image. No root command is executed automatically.")
            .setPositiveButton("OK", null).show();
    }

    private void buildBrowser() {
        top("Titanium Browser", "Real Chromium tabs and extensions live in Titanium, not in a screenshot.");
        EditText address = new EditText(this);
        address.setSingleLine(true);
        address.setTextColor(Color.WHITE);
        address.setHintTextColor(SECONDARY);
        address.setHint("https://example.org");
        address.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        address.setPadding(dp(14), dp(12), dp(14), dp(12));
        address.setBackgroundColor(CARD);
        content.addView(address, new LinearLayout.LayoutParams(-1, dp(56)));
        heading("Browser actions");
        row("Go to website", "Open a real http(s) page in the installed browser", v -> openWebsite(address.getText().toString()));
        row("Open Titanium", isInstalled(TITANIUM_PACKAGE) ? "Open browser tabs" : "Titanium isn't installed", v -> openApp(TITANIUM_PACKAGE));
        row("Extensions", "Open Titanium; extension support must be checked inside the browser", v -> openApp(TITANIUM_PACKAGE));
        row("Android default browser", "Choose Android's preferred web browser", v -> openSetting(Settings.ACTION_MANAGE_DEFAULT_APPS_SETTINGS));
    }

    private void openWebsite(String raw) {
        final Uri uri;
        try { uri = Uri.parse(PanelLinkPolicy.normalized(raw)); }
        catch (IllegalArgumentException invalid) { toast(invalid.getMessage()); return; }
        Intent view = new Intent(Intent.ACTION_VIEW, uri);
        if (isInstalled(TITANIUM_PACKAGE)) view.setPackage(TITANIUM_PACKAGE);
        try { startActivity(view); }
        catch (ActivityNotFoundException e) {
            view.setPackage(null);
            try { startActivity(view); }
            catch (ActivityNotFoundException ignored) { toast("No browser in this guest can open the URL"); }
        }
    }

    private void toast(String msg) { Toast.makeText(this, msg, Toast.LENGTH_SHORT).show(); }
}
