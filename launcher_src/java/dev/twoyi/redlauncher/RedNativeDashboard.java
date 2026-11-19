// SPDX-License-Identifier: Apache-2.0
package dev.twoyi.redlauncher;

import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.Drawable;
import android.graphics.drawable.GradientDrawable;
import android.os.BatteryManager;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.View;
import android.widget.GridLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

/** Actual Android launcher widgets; no rasterized controls, static app-state badges,
 *  claimed root access, or fictitious version information. The existing original
 *  screenshots are retained only as artwork references in the source bundle.
 *  All touch targets are Android views with accessibility labels.
 */
final class RedNativeDashboard extends ScrollView {
    private static final int BLACK = Color.rgb(0, 0, 0);
    private int accent;
    private static final int CARD = Color.rgb(17, 17, 20);
    private static final int MUTED = Color.rgb(175, 175, 185);
    private final MainActivity owner;
    private final LinearLayout content;
    private final Handler ticker = new Handler(Looper.getMainLooper());
    private TextView timeView;
    private TextView batteryView;
    private TextView rootView;
    private String rootLabel = "Root access: Not checked";
    private boolean rootProbeRunning;
    private final Runnable updateStatus = new Runnable() {
        @Override public void run() {
            if (timeView != null) timeView.setText(new SimpleDateFormat("HH:mm", Locale.getDefault()).format(new Date()));
            if (batteryView != null) batteryView.setText(readBattery());
            ticker.postDelayed(this, 30_000);
        }
    };

    private static final class Tile {
        final String label, packageName, fallback;
        Tile(String label, String packageName, String fallback) {
            this.label = label; this.packageName = packageName; this.fallback = fallback;
        }
    }

    private static final Tile[] APPS = {
        new Tile("Titanium Browser", "io.github.jqssun.helium", "T"),
        new Tile("Play Store", "com.android.vending", "▶"),
        new Tile("F-Droid", "org.fdroid.fdroid", "F"),
        new Tile("Magisk", "com.topjohnwu.magisk", "M"),
        new Tile("Termux", "com.termux", ">_"),
        new Tile("Files", "com.android.documentsui", "▣"),
        new Tile("Settings", "com.android.settings", "⚙"),
        new Tile("App Manager", "io.github.muntashirakon.AppManager", "◇"),
        new Tile("HeliBoard", "helium314.keyboard", "⌨")
    };

    RedNativeDashboard(MainActivity activity) {
        super(activity);
        owner = activity;
        setFillViewport(true);
        setBackgroundColor(BLACK);
        content = new LinearLayout(activity);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(dp(15), dp(18), dp(15), dp(26));
        addView(content);
        render();
    }

    private int dp(float size) { return (int) (size * getResources().getDisplayMetrics().density + .5f); }

    private GradientDrawable background(int base, int stroke, int corner) {
        GradientDrawable drawable = new GradientDrawable();
        drawable.setColor(base);
        drawable.setCornerRadius(dp(corner));
        drawable.setStroke(dp(1), stroke);
        return drawable;
    }

    private TextView label(String value, int size, int color, boolean bold) {
        TextView text = new TextView(owner);
        text.setText(value);
        text.setTextColor(color);
        text.setTextSize(size);
        text.setGravity(Gravity.CENTER_VERTICAL);
        text.setTypeface(Typeface.DEFAULT, bold ? Typeface.BOLD : Typeface.NORMAL);
        return text;
    }

    void refresh() { render(); }

    private void render() {
        accent = RedAccentStore.color(RedAccentStore.load(owner));
        content.removeAllViews();
        LinearLayout toolbar = new LinearLayout(owner);
        toolbar.setGravity(Gravity.CENTER_VERTICAL);
        TextView brand = label("∕∕  Andarium Red", 25, Color.WHITE, true);
        toolbar.addView(brand, new LinearLayout.LayoutParams(0, dp(46), 1));
        TextView options = label("⋮", 30, Color.WHITE, true);
        options.setGravity(Gravity.CENTER);
        options.setContentDescription("Launcher menu");
        options.setOnClickListener(v -> owner.openRedMenu());
        toolbar.addView(options, new LinearLayout.LayoutParams(dp(42), dp(46)));
        content.addView(toolbar);
        View topAccent = new View(owner); topAccent.setBackgroundColor(accent);
        LinearLayout.LayoutParams a = new LinearLayout.LayoutParams(dp(44), dp(3));
        a.bottomMargin = dp(17);
        content.addView(topAccent, a);

        TextView system = label("◉  Android " + Build.VERSION.RELEASE + "    ·    Guest system", 19, Color.WHITE, true);
        system.setPadding(dp(13), dp(8), dp(13), dp(8));
        system.setBackground(background(CARD, accent, 17));
        system.setOnClickListener(v -> owner.openRedStatus());
        system.setContentDescription("Android guest status and diagnostics");
        content.addView(system, new LinearLayout.LayoutParams(-1, dp(62)));

        LinearLayout status = new LinearLayout(owner);
        status.setPadding(dp(7), dp(15), dp(7), dp(4));
        timeView = label("", 17, Color.WHITE, true);
        batteryView = label("", 16, Color.WHITE, false);
        batteryView.setGravity(Gravity.END | Gravity.CENTER_VERTICAL);
        status.addView(timeView, new LinearLayout.LayoutParams(0, dp(30), 1));
        status.addView(batteryView, new LinearLayout.LayoutParams(0, dp(30), 1));
        content.addView(status);

        TextView robot = label("◖●◗", 50, accent, true);
        robot.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams robotSize = new LinearLayout.LayoutParams(-1, dp(69));
        robotSize.topMargin = dp(23);
        content.addView(robot, robotSize);
        TextView title = label("Android " + Build.VERSION.RELEASE, 40, Color.WHITE, true);
        title.setGravity(Gravity.CENTER);
        content.addView(title);
        TextView environment = label("A N D A R I U M   E N V I R O N M E N T", 11, MUTED, false);
        environment.setGravity(Gravity.CENTER);
        content.addView(environment);
        TextView root = label(rootLabel, 14, accent, true);
        rootView = root;
        root.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams r = new LinearLayout.LayoutParams(-1, dp(40));
        r.topMargin = dp(14);
        root.setBackground(background(CARD, accent, 18));
        root.setContentDescription("Tap to check Android guest root; may request superuser access");
        root.setOnClickListener(v -> checkRootOnUserTap());
        content.addView(root, r);

        TextView search = label("⌕   Search installed Android apps", 17, MUTED, false);
        search.setPadding(dp(17), 0, dp(10), 0);
        search.setBackground(background(CARD, accent, 22));
        search.setOnClickListener(v -> owner.openRedSearch());
        search.setContentDescription("Search installed Android applications");
        LinearLayout.LayoutParams sp = new LinearLayout.LayoutParams(-1, dp(53));
        sp.topMargin = dp(24);
        sp.bottomMargin = dp(21);
        content.addView(search, sp);

        GridLayout grid = new GridLayout(owner);
        grid.setColumnCount(4);
        // Each cell uses the actual screen width; the GridLayout is not a bitmap.
        int width = getResources().getDisplayMetrics().widthPixels;
        int cell = Math.max(dp(65), (width - dp(30)) / 4);
        for (Tile tile : APPS) {
            LinearLayout card = new LinearLayout(owner);
            card.setOrientation(LinearLayout.VERTICAL);
            card.setGravity(Gravity.TOP | Gravity.CENTER_HORIZONTAL);
            card.setPadding(dp(3), dp(8), dp(3), dp(5));
            card.setContentDescription(tile.label);
            ImageView icon = new ImageView(owner);
            icon.setScaleType(ImageView.ScaleType.FIT_CENTER);
            boolean available = appAvailable(tile.packageName);
            Drawable drawable = null;
            if (available) {
                try { drawable = owner.getPackageManager().getApplicationIcon(tile.packageName); }
                catch (PackageManager.NameNotFoundException | SecurityException ignored) { available = false; }
            }
            if (drawable != null) icon.setImageDrawable(drawable);
            else {
                TextView fallback = label(tile.fallback, 26, accent, true);
                fallback.setGravity(Gravity.CENTER);
                fallback.setBackground(background(CARD, Color.rgb(69, 69, 76), 15));
                // Missing packages are shown as missing, never as functioning apps.
                card.addView(fallback, new LinearLayout.LayoutParams(dp(57), dp(57)));
            }
            if (drawable != null) card.addView(icon, new LinearLayout.LayoutParams(dp(57), dp(57)));
            TextView name = label(tile.label, 11, Color.WHITE, false);
            name.setGravity(Gravity.TOP | Gravity.CENTER_HORIZONTAL);
            name.setMaxLines(2);
            LinearLayout.LayoutParams n = new LinearLayout.LayoutParams(-1, dp(32));
            n.topMargin = dp(7);
            card.addView(name, n);
            if (!available) {
                TextView absent = label("Not installed", 10, accent, false);
                absent.setGravity(Gravity.CENTER);
                card.addView(absent, new LinearLayout.LayoutParams(-1, dp(18)));
            }
            card.setOnClickListener(v -> openPackage(tile.packageName, tile.label));
            GridLayout.LayoutParams lp = new GridLayout.LayoutParams();
            lp.width = cell;
            lp.height = dp(125);
            grid.addView(card, lp);
        }
        content.addView(grid);

        TextView drawer = label("●  ●  ●     All installed apps     ●  ●  ●", 16, accent, true);
        drawer.setGravity(Gravity.CENTER);
        drawer.setBackground(background(CARD, Color.rgb(80, 35, 40), 22));
        drawer.setOnClickListener(v -> owner.openRedAppDrawer());
        LinearLayout.LayoutParams dock = new LinearLayout.LayoutParams(-1, dp(55));
        dock.topMargin = dp(23);
        content.addView(drawer, dock);
        ticker.removeCallbacks(updateStatus);
        updateStatus.run();
    }

    /** User-initiated, off-main-thread root/Magisk verification. Never probe on boot. */
    private void checkRootOnUserTap() {
        if (rootProbeRunning) return;
        rootProbeRunning = true;
        rootLabel = "Checking root (permission may be requested)…";
        if (rootView != null) rootView.setText(rootLabel);
        Thread thread = new Thread(() -> {
            RedRootProbe.Result result = RedRootProbe.check(RedRootProbe.PROCESS_RUNNER);
            owner.runOnUiThread(() -> {
                rootProbeRunning = false;
                rootLabel = result.label();
                if (rootView != null) rootView.setText(rootLabel);
            });
        }, "red-root-check");
        thread.start();
    }

    private boolean appAvailable(String packageName) {
        try { owner.getPackageManager().getPackageInfo(packageName, 0); return true; }
        catch (PackageManager.NameNotFoundException | SecurityException absent) { return false; }
    }

    private String readBattery() {
        Intent battery = owner.registerReceiver(null, new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
        if (battery == null) return "Battery —";
        int raw = battery.getIntExtra(BatteryManager.EXTRA_LEVEL, -1);
        int scale = battery.getIntExtra(BatteryManager.EXTRA_SCALE, -1);
        if (raw < 0 || scale <= 0) return "Battery —";
        return "Battery " + Math.round(raw * 100.0f / scale) + "%";
    }

    private void openPackage(String packageName, String label) {
        try {
            Intent launch = owner.getPackageManager().getLaunchIntentForPackage(packageName);
            if (launch == null) {
                Toast.makeText(owner, label + " is not installed or cannot be launched", Toast.LENGTH_SHORT).show();
                return;
            }
            owner.startActivity(launch);
        } catch (ActivityNotFoundException | SecurityException denied) {
            Toast.makeText(owner, label + " cannot be opened under guest permissions", Toast.LENGTH_SHORT).show();
        }
    }

    @Override protected void onDetachedFromWindow() {
        ticker.removeCallbacks(updateStatus);
        super.onDetachedFromWindow();
    }
}
