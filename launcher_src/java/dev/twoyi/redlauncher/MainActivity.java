// SPDX-License-Identifier: Apache-2.0
package dev.twoyi.redlauncher;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageManager;
import android.content.pm.PackageInfo;
import android.content.res.Configuration;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.RectF;
import android.os.Bundle;
import android.os.Build;
import android.os.BatteryManager;
import android.content.IntentFilter;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.HashMap;
import java.util.Map;
import android.provider.Settings;
import android.text.InputType;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowManager;
import android.widget.EditText;
import android.widget.Toast;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;

/** An Android 17-targeted HOME activity that uses the supplied generated screens as
 *  pixel-reference skins. Tap targets launch actual installed apps or real Android settings.
 *  It DOES NOT implement Android 17, Magisk root, Chromium, or an iOS host bridge.
 */
public final class MainActivity extends Activity {
    private static final int HOME = 0, SETTINGS = 1, BROWSER_PREVIEW = 2;
    private int screen = HOME;
    private static final String HOME_STYLE_PREFS = "andarium.red.home.style";
    private static final String HOME_STYLE_KEY = "reference";
    private boolean rootCheckRunning = false;
    private String rootStatusText = "Root: not checked";
    private Bitmap[] designs;
    private SkinView skin;
    private RedNativeDashboard dashboard;
    // Root remains unverified until a live privileged host/guest diagnostic establishes it.
    private boolean rootVerified = false;
    private final Map<String, Boolean> installedCache = new HashMap<>();
    private static final String[] DISPLAY_PACKAGES = {
        "io.github.jqssun.helium", "com.android.vending", "org.fdroid.fdroid", "com.topjohnwu.magisk",
        "com.termux", "com.android.documentsui", "com.android.settings", "io.github.muntashirakon.AppManager",
        "helium314.keyboard"
    };
    private String androidVersion = "unknown";
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG | Paint.FILTER_BITMAP_FLAG);

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        RedAccentStore.acceptLaunchAccent(this, getIntent());
        getWindow().setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN, WindowManager.LayoutParams.FLAG_FULLSCREEN);
        getWindow().setNavigationBarColor(Color.BLACK);
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_HIDE_NAVIGATION | View.SYSTEM_UI_FLAG_FULLSCREEN |
                View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY);
        androidVersion = Build.VERSION.RELEASE;
        // Do not decode multi-megabyte concept artwork during a native HOME startup.
        // Load each reference image only if the user explicitly opens that preview.
        designs = new Bitmap[3];
        // Reference-matched interactive layout is the first-run choice.
        // The accessible lightweight native UI remains a persisted option.
        setHomeStyle(getSharedPreferences(HOME_STYLE_PREFS, MODE_PRIVATE)
                     .getInt(HOME_STYLE_KEY, 1) == 1, false);
        // Do not execute `su` automatically: that can trigger a superuser prompt.
        // Root status remains unverified until a root permission provider is wired in.
    }

    @Override protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        if (RedAccentStore.acceptLaunchAccent(this, intent) && dashboard != null) dashboard.refresh();
    }

    @Override protected void onResume() {
        super.onResume();
        refreshInstalledApps();
        if (skin != null) skin.invalidate();
        if (dashboard != null) dashboard.refresh();
    }

    private void refreshInstalledApps() {
        for (String name : DISPLAY_PACKAGES) installedCache.put(name, packageInstalled(name));
    }

    private boolean cachedInstalled(int slot) {
        Boolean present = installedCache.get(DISPLAY_PACKAGES[slot]);
        return present != null && present;
    }

    private int batteryLevel() {
        Intent state = registerReceiver(null, new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
        if (state == null) return -1;
        int level = state.getIntExtra(BatteryManager.EXTRA_LEVEL, -1);
        int scale = state.getIntExtra(BatteryManager.EXTRA_SCALE, -1);
        if (level < 0 || scale <= 0) return -1;
        return Math.max(0, Math.min(100, Math.round(level * 100f / scale)));
    }

    private Bitmap readAsset(String name) throws Exception {
        try (InputStream stream = getAssets().open(name)) { return BitmapFactory.decodeStream(stream); }
    }

    private Bitmap designForPreview(int index) {
        if (index < 0 || index >= designs.length) return null;
        if (designs[index] == null) {
            String file = index == HOME ? "home.png" : index == SETTINGS ? "settings.png" : "browser.png";
            try { designs[index] = readAsset(file); }
            catch (Exception failure) { toast("Reference preview unavailable: " + failure.getMessage()); }
        }
        return designs[index];
    }

    @Override public void onBackPressed() {
        if (screen != HOME && skin != null) { screen = HOME; skin.invalidate(); }
        else super.onBackPressed();
    }

    @Override public void onConfigurationChanged(Configuration c) {
        super.onConfigurationChanged(c);
        if (skin != null) skin.invalidate();
    }

    private final class SkinView extends View {
        private final RectF dest = new RectF();
        SkinView() { super(MainActivity.this);  }
        @Override protected void onDraw(Canvas canvas) {
            canvas.drawColor(Color.BLACK);
            Bitmap src = designForPreview(screen);
            if (src == null) return;
            // Preserve the generated reference aspect ratio while filling modern
            // iPhone-shaped guest viewports; avoid visible letterboxing on small
            // (<6%) aspect-ratio differences. Extreme screens use contain.
            float viewAspect=getWidth()/(float)getHeight();
            float artAspect=src.getWidth()/(float)src.getHeight();
            float xscale=getWidth()/(float)src.getWidth();
            float yscale=getHeight()/(float)src.getHeight();
            float scale = Math.abs(viewAspect/artAspect-1f) < 0.06f
                ? Math.max(xscale,yscale) : Math.min(xscale,yscale);
            float x = (getWidth() - src.getWidth() * scale) / 2f;
            float y = (getHeight() - src.getHeight() * scale) / 2f;
            dest.set(x, y, x + src.getWidth()*scale, y + src.getHeight()*scale);
            canvas.drawBitmap(src, null, dest, paint);
            if (screen == HOME) {
                drawRealDeviceStatus(canvas, x, y, scale);
                drawInstalledState(canvas, x, y, scale);
                drawHostAppRail(canvas, x, y, scale);
            }
            // The source mockups show root and Android 17 as active. Mask those claims until verified.
            if (!rootVerified || !"17".equals(androidVersion)) {
                float sx = scale, sy = scale;
                Paint bg = new Paint(Paint.ANTI_ALIAS_FLAG);
                bg.setColor(Color.rgb(12,12,14));
                // 863x1822 reference-coordinate pill in the main artwork.
                // Each reference image has a different badge position. Never cover
                // unrelated browser controls with a fake root-status patch.
                float bx = x + 251*sx;
                float by = y + (screen == HOME ? 521 : screen == SETTINGS ? 269 : 538)*sy;
                canvas.drawRoundRect(new RectF(bx,by,bx+330*sx,by+68*sy), 20*sx,20*sy,bg);
                bg.setColor(Color.rgb(248,80,91));
                bg.setTextSize(21*sx);
                bg.setFakeBoldText(true);
                canvas.drawText(screen == BROWSER_PREVIEW ? "Browser preview only" : rootStatusText, bx + 10*sx, by + 37*sy, bg);
                bg.setColor(Color.rgb(12,12,14));
                // Cover top rooted badge until native guest root is actually verified.
                bg.setColor(Color.rgb(12,12,14));
                canvas.drawRoundRect(new RectF(x+435*sx,y+118*sy,x+566*sx,y+174*sy), 15*sx,15*sy,bg);
                bg.setColor(Color.rgb(248,80,91));bg.setTextSize(19*sx);
                canvas.drawText("No root", x+452*sx,y+148*sy,bg);
                // Correct the top guest-version claim in both launcher and settings references.
                canvas.drawRoundRect(new RectF(x+134*sx,y+111*sy,x+421*sx,y+164*sy), 9*sx,9*sy,bg);
                bg.setColor(Color.WHITE); bg.setTextSize(29*sx);
                canvas.drawText("Android " + androidVersion + " guest", x+144*sx,y+145*sy,bg);
                if (screen == HOME) {
                    bg.setColor(Color.BLACK);
                    canvas.drawRoundRect(new RectF(x+214*sx,y+391*sy,x+658*sx,y+520*sy),18*sx,18*sy,bg);
                    bg.setColor(Color.WHITE);bg.setTextSize(43*sx);
                    canvas.drawText("Android " + androidVersion, x+265*sx,y+464*sy,bg);
                    bg.setColor(Color.rgb(248,80,91));bg.setTextSize(20*sx);
                    canvas.drawText("TW O Y I  G U E S T", x+293*sx,y+499*sy,bg);
                }
            }
            // Mockups contain literal enabled bridge badges. Cover those claims:
            // an iOS permission can only be queried and granted in the host app.
            if (screen == SETTINGS) {
                Paint cover = new Paint(Paint.ANTI_ALIAS_FLAG);
                cover.setTextSize(14*scale);
                for (int row=0;row<6;row++) {
                    float cy = y+(1354 + row*55)*scale;
                    cover.setColor(Color.rgb(13,14,16));
                    canvas.drawRoundRect(new RectF(x+609*scale,cy-21*scale,x+755*scale,cy+17*scale),
                            9*scale,9*scale,cover);
                    cover.setColor(Color.rgb(255,89,100));
                    canvas.drawText("Not connected",x+620*scale,cy+5*scale,cover);
                }
            }
            // Browser reference is a visual preview only, not the real browser UI.
            if (screen == BROWSER_PREVIEW) {
                Paint bg = new Paint(Paint.ANTI_ALIAS_FLAG);bg.setColor(Color.BLACK);
                canvas.drawRect(x+50*scale, y+1138*scale, x+799*scale,y+1190*scale,bg);
                bg.setColor(Color.rgb(255,100,110));bg.setTextSize(20*scale);
                canvas.drawText("Concept preview — extension support not verified", x+61*scale,y+1170*scale,bg);
            }
        }
        /** The screenshot contains a frozen clock, battery, and icons. Cover
         * those examples and render actual Android data instead of claiming
         * a battery level or app installation that was never observed. */
        private void drawRealDeviceStatus(Canvas canvas, float x, float y, float scale) {
            Paint overlay = new Paint(Paint.ANTI_ALIAS_FLAG);
            overlay.setColor(Color.BLACK);
            canvas.drawRect(x + 10*scale, y + 197*scale,
                    x + 849*scale, y + 270*scale, overlay);
            overlay.setColor(Color.WHITE);
            overlay.setTextSize(28*scale);
            String time = new SimpleDateFormat("HH:mm", Locale.getDefault()).format(new Date());
            canvas.drawText(time, x + 35*scale, y + 242*scale, overlay);
            String battery = HomeStatusFormat.battery(batteryLevel());
            canvas.drawText(battery, x + 700*scale, y + 242*scale, overlay);
            // A refresh once a minute changes only the small status strip.
            postInvalidateDelayed(60_000);
        }

        private void drawInstalledState(Canvas canvas, float x, float y, float scale) {
            Paint shade = new Paint(Paint.ANTI_ALIAS_FLAG);
            Paint words = new Paint(Paint.ANTI_ALIAS_FLAG);
            words.setTextSize(16*scale);
            words.setFakeBoldText(true);
            words.setColor(Color.rgb(255, 110, 119));
            // Indices correspond to the nine visible tiles on the supplied artwork.
            final int[] left = {40,255,455,650,55,255,455,650,55};
            final int[] top = {785,785,785,785,1060,1060,1060,1060,1270};
            for (int slot=0;slot<DISPLAY_PACKAGES.length;slot++) {
                if (cachedInstalled(slot)) continue;
                shade.setColor(Color.argb(195, 0, 0, 0));
                float bx = x + left[slot]*scale;
                float by = y + top[slot]*scale;
                canvas.drawRoundRect(new RectF(bx, by, bx + 160*scale, by + 153*scale),
                        20*scale, 20*scale, shade);
                canvas.drawText("Not installed", bx + 13*scale, by + 79*scale, words);
            }
        }

        /** Actual tap targets drawn over the reference skin, not fake IPA icons.
         * The Android 17 environment sends a named request to the Nexaris host.
         */
        private void drawHostAppRail(Canvas canvas, float x, float y, float scale) {
            final String[] names = {"Nexaris", "URL OS", "Rap Box", "Rap Keys", "Settings"};
            final String[] symbols = {"N", "◎", "◇", "⌨", "⚙"};
            Paint p = new Paint(Paint.ANTI_ALIAS_FLAG);
            p.setColor(Color.rgb(6, 6, 9));
            canvas.drawRoundRect(new RectF(x+18*scale, y+1452*scale,
                x+845*scale, y+1574*scale), 19*scale, 19*scale, p);
            p.setTextAlign(Paint.Align.CENTER);
            p.setFakeBoldText(true);
            for (int i=0; i<names.length; i++) {
                float cx = x + (i + 0.5f) * 863f / 5f * scale;
                p.setColor(Color.rgb(242, 43, 67));
                p.setTextSize(37*scale);
                canvas.drawText(symbols[i], cx, y+1510*scale, p);
                p.setColor(Color.WHITE);
                p.setTextSize(18*scale);
                canvas.drawText(names[i], cx, y+1545*scale, p);
            }
        }

        @Override public boolean onTouchEvent(MotionEvent e) {
            if(e.getAction() != MotionEvent.ACTION_UP || !dest.contains(e.getX(),e.getY())) return true;
            float xx=(e.getX()-dest.left)*863/dest.width();
            float yy=(e.getY()-dest.top)*1822/dest.height();
            if(screen==HOME) homeTap(xx,yy);
            else if(screen==SETTINGS) settingsTap(xx,yy);
            else browserTap(xx,yy);
            return true;
        }
    }

    /** The host executes these native apps; Android never installs or runs an IPA. */
    void requestHostApp(String route) {
        if (!HostLaunchWire.allowed(route)) return;
        try {
            boolean queued = HostLaunchBridgeProvider.request(this, route);
            toast(queued ? "Requesting Nexaris host app…" :
                "A host request is already pending. Open Nexaris to complete it.");
        } catch (RuntimeException unavailable) {
            toast("Nexaris host bridge is unavailable in this guest image.");
        }
    }

    private void openNativePanel(String panel) {
        Intent intent = new Intent(this, RedPanelActivity.class);
        intent.putExtra(RedPanelActivity.EXTRA_PANEL, panel);
        startActivity(intent);
    }

    private void homeTap(float x,float y) {
        if (y < 185 && x > 670) { menu();return; }
        if (y < 185) { showRuntimeStatus(); return; }
        if (x > 235 && x < 590 && y >= 515 && y < 615) {
            checkRootOnUserTap();
            return;
        }
        if (y>=1452 && y<1574) {
            int index = Math.min(HostLaunchWire.ROUTES.length-1,
                                 Math.max(0, (int)(x * 5f / 863f)));
            requestHostApp(HostLaunchWire.ROUTES[index]);
            return;
        }
        if (y>625 && y<735) { searchApps();return; }
        if (y>785 && y<1055) {
            if(x<220) launchAny("Titanium", "Chrome", "Browser");
            else if(x<430) launchAny("Play Store");
            else if(x<650) launchAny("F-Droid");
            else launchAny("Magisk");
        } else if(y>1060 && y<1255) {
            if(x<220) launchAny("Termux");
            else if(x<430) openDocuments();
            else if(x<650) {
                if (skin != null) { screen = SETTINGS; skin.invalidate(); }
                else openNativePanel(RedPanelActivity.SETTINGS_PANEL);
            }
            else launchAny("App Manager");
        } else if (y>1270 && y<1455 && x<220) launchAny("Heli Keyboard", "Heli");
        else if (y>1580 && y<1780) {
            if (x>345&&x<510) showAppDrawer("");
            else if(x>670) openDocuments();
            else if (x<160) launchAny("Phone");
            else toast("Install an app to use this dock shortcut");
        }
    }

    private void settingsTap(float x,float y) {
        if (y<170 && x>690) { screen=HOME;skin.invalidate();return; }
        if (y<414 && y>338) { safeAction(Settings.ACTION_SETTINGS);return; }
        if (y>=426 && y<=1200) {
            String[] actions = {
                Settings.ACTION_WIRELESS_SETTINGS, Settings.ACTION_APPLICATION_SETTINGS,
                Settings.ACTION_NOTIFICATION_SETTINGS, Settings.ACTION_DISPLAY_SETTINGS,
                Settings.ACTION_INTERNAL_STORAGE_SETTINGS, Settings.ACTION_PRIVACY_SETTINGS,
                Settings.ACTION_SECURITY_SETTINGS, Settings.ACTION_SYNC_SETTINGS,
                Settings.ACTION_ACCESSIBILITY_SETTINGS, Settings.ACTION_SETTINGS,
                Settings.ACTION_DEVICE_INFO_SETTINGS, Settings.ACTION_APPLICATION_DEVELOPMENT_SETTINGS
            };
            int index=Math.min(actions.length-1, (int)((y-426)/64));
            safeAction(actions[index]); return;
        }
        if (y>1240) {
            new AlertDialog.Builder(this).setTitle("iOS Bridge Status")
              .setMessage("The mockup shows enabled iOS bridges. This Android launcher cannot grant iOS permissions or synchronize the iOS clipboard without a native Twoyi host integration. Guest Android permissions remain controlled by Android Settings.")
              .setPositiveButton("Android Settings", (d,w)->safeAction(Settings.ACTION_SETTINGS))
              .setNegativeButton("Close",null).show();
        }
    }

    private void browserTap(float x,float y) {
        if (y<180 && x>680) { screen=HOME;skin.invalidate();return; }
        if (y<520 || (y>720 && y<1110)) launchAny("Titanium", "Chrome", "Browser");
        else toast("Preview only. Open Titanium for actual extension management.");
    }

    /** Uses Android's live PackageManager. Neither the artwork nor a package
     *  name in our source list is proof an app was installed in this guest. */
    private List<LauncherCatalog.App> launchableApps() {
        PackageManager pm = getPackageManager();
        List<LauncherCatalog.App> apps = new ArrayList<>();
        for (ApplicationInfo info : pm.getInstalledApplications(0)) {
            if (getPackageName().equals(info.packageName)) continue;
            if (pm.getLaunchIntentForPackage(info.packageName) == null) continue;
            apps.add(new LauncherCatalog.App(pm.getApplicationLabel(info).toString(), info.packageName));
        }
        return apps;
    }

    private void openPackage(String packageName) {
        Intent launch = getPackageManager().getLaunchIntentForPackage(packageName);
        if (launch == null) { toast("This app is not installed or cannot be launched"); return; }
        try { startActivity(launch); }
        catch (ActivityNotFoundException error) { toast("Android could not open that app"); }
    }

    /** Real app drawer; shows only installed, launchable Android applications. */
    private void showAppDrawer(String query) {
        final List<LauncherCatalog.App> apps = LauncherCatalog.filter(launchableApps(), query);
        if (apps.isEmpty()) { toast("No installed Android apps match that search"); return; }
        String[] names = new String[apps.size()];
        for (int i=0;i<apps.size();i++) names[i] = apps.get(i).label;
        new AlertDialog.Builder(this)
                .setTitle(query.isEmpty() ? "Installed Android apps" : "Apps matching: " + query)
                .setItems(names, (dialog, selected) -> openPackage(apps.get(selected).packageName))
                .setNegativeButton("Close", null)
                .show();
    }

    private void searchApps() {
        EditText box=new EditText(this);
        box.setSingleLine();
        box.setHint("Search installed Android apps");
        box.setInputType(InputType.TYPE_CLASS_TEXT);
        new AlertDialog.Builder(this).setTitle("Search Android apps")
                .setView(box)
                .setPositiveButton("Search", (dialog, which) -> showAppDrawer(box.getText().toString().trim()))
                .setNeutralButton("All apps", (dialog, which) -> showAppDrawer(""))
                .setNegativeButton("Cancel", null).show();
    }

    private boolean packageInstalled(String name) {
        try { getPackageManager().getPackageInfo(name, 0); return true; }
        catch (PackageManager.NameNotFoundException notInstalled) { return false; }
    }

    void openRedAppDrawer() { showAppDrawer(""); }
    void openRedSearch() { searchApps(); }
    void openRedStatus() { showRuntimeStatus(); }
    void openRedMenu() { menu(); }

    private void showRuntimeStatus() {
        String status = LauncherCatalog.guestStatus(androidVersion, packageInstalled("com.topjohnwu.magisk"));
        String text = status + "\nAndroid API " + Build.VERSION.SDK_INT
                + "\nSecurity patch " + Build.VERSION.SECURITY_PATCH
                + "\nTitanium: " + (hasLaunchableLabel("Titanium") ? "available" : "not found")
                + "\nClipboard: controlled from iOS host, not verified in this launcher"
                + "\nDisplay: " + getResources().getDisplayMetrics().widthPixels + " × "
                + getResources().getDisplayMetrics().heightPixels
                + "\n\nManager installed does not imply root access.";
        new AlertDialog.Builder(this).setTitle("Android guest diagnostics")
                .setMessage(text).setPositiveButton("OK", null).show();
    }

    private boolean hasLaunchableLabel(String hint) {
        String needle = hint.toLowerCase(Locale.ROOT);
        for (LauncherCatalog.App app : launchableApps()) {
            if (app.label.toLowerCase(Locale.ROOT).contains(needle)) return true;
        }
        return false;
    }

    private void menu() {
        String[] opts={"Red Android Settings", "Titanium Browser (if installed)", "Browser hub (functional)", "Original Android home selector", "Runtime status", "All installed apps", "Use exact-reference layout", "Use lightweight native layout", "Check Magisk root (may request permission)"};
        new AlertDialog.Builder(this).setTitle("Twoyi Red")
          .setItems(opts,(d,i)->{
              if(i==0) openNativePanel(RedPanelActivity.SETTINGS_PANEL);
              if(i==1) launchAny("Titanium");
              if(i==2) openNativePanel(RedPanelActivity.BROWSER_PANEL);
              if(i==3) safeAction(Settings.ACTION_HOME_SETTINGS);
              if(i==4) showRuntimeStatus();
              if(i==5) showAppDrawer("");
              if(i==6) setHomeStyle(true, true);
              if(i==7) setHomeStyle(false, true);
               if(i==8) checkRootOnUserTap();
          }).show();
    }

    /** Saved UI selection, independent of root/Magisk or the guest image. */
    private void setHomeStyle(boolean reference, boolean persist) {
        if (persist) {
            getSharedPreferences(HOME_STYLE_PREFS, MODE_PRIVATE).edit()
                .putInt(HOME_STYLE_KEY, reference ? 1 : 0).apply();
        }
        if (reference) {
            dashboard = null;
            screen = HOME;
            skin = new SkinView();
            setContentView(skin);
        } else {
            skin = null;
            dashboard = new RedNativeDashboard(this);
            setContentView(dashboard);
        }
    }

    /** Never claim root from an installed manager. Test only after a tap. */
    private void checkRootOnUserTap() {
        if (rootCheckRunning) return;
        rootCheckRunning = true;
        rootStatusText = "Checking root…";
        if (skin != null) skin.invalidate();
        Thread worker = new Thread(() -> {
            RedRootProbe.Result result = RedRootProbe.check(RedRootProbe.PROCESS_RUNNER);
            runOnUiThread(() -> {
                rootCheckRunning = false;
                rootVerified = result.root && result.magisk;
                rootStatusText = rootVerified ? "Magisk root verified" :
                    result.root ? "UID 0; Magisk not verified" : "Root not granted";
                if (skin != null) skin.invalidate();
                new AlertDialog.Builder(this)
                    .setTitle("Guest root verification")
                    .setMessage(result.label())
                    .setPositiveButton("OK", null)
                    .show();
            });
        }, "red-design-root-check");
        worker.start();
    }

    private void launchAny(String... hints) {
        PackageManager pm = getPackageManager();
        List<LauncherCatalog.App> all = launchableApps();
        List<LauncherCatalog.App> matches = new ArrayList<>();
        for (LauncherCatalog.App app : all) {
            for (String hint : hints) {
                if (hint != null && !hint.trim().isEmpty() &&
                        app.label.toLowerCase(Locale.ROOT).contains(hint.trim().toLowerCase(Locale.ROOT))) {
                    matches.add(app);
                    break;
                }
            }
        }
        if (matches.isEmpty()) { toast("App not installed in the Android guest"); return; }
        if (matches.size() == 1) { openPackage(matches.get(0).packageName); return; }
        String[] names = new String[matches.size()];
        for (int i=0;i<matches.size();i++) names[i] = matches.get(i).label;
        new AlertDialog.Builder(this).setTitle("Open installed app")
                .setItems(names, (dialog,index) -> openPackage(matches.get(index).packageName))
                .setNegativeButton("Cancel", null).show();
    }
    private void openDocuments() {
        try { Intent i = new Intent(Intent.ACTION_OPEN_DOCUMENT); i.setType("*/*");
              i.addCategory(Intent.CATEGORY_OPENABLE); startActivity(i); }
        catch(ActivityNotFoundException ex) { toast("Guest file picker unavailable"); }
    }
    private void safeAction(String action) {
        try { Intent i=new Intent(action);
            startActivity(i);
        } catch(ActivityNotFoundException ex) { safeActionFallback(); }
    }
    private void safeActionFallback() {
        try {startActivity(new Intent(Settings.ACTION_SETTINGS));}
        catch(Exception ex) {toast("Setting unavailable in this Android guest");}
    }
    private void toast(String message){ Toast.makeText(this,message,Toast.LENGTH_SHORT).show(); }
}
