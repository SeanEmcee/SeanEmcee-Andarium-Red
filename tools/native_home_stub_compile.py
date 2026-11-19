#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Compile the new native HOME widget against minimal local Android API stubs.

This is NOT a real Android SDK or Soong build. It detects misspelled Java APIs
and source mistakes before the official Android 17 build is attempted.
"""
from __future__ import annotations
import subprocess
import tempfile
from pathlib import Path
from android_panel_stub_compile import STUBS as base

ROOT = Path(__file__).resolve().parents[1]
STUBS = dict(base)
STUBS.update({
'dev/twoyi/redlauncher/MainActivity.java': '''package dev.twoyi.redlauncher; public class MainActivity extends android.app.Activity {public void openRedMenu(){} public void openRedStatus(){} public void openRedSearch(){} public void openRedAppDrawer(){} public void runOnUiThread(Runnable r){r.run();} }''',
'android/content/Context.java': '''package android.content; public class Context {public android.content.res.Resources getResources(){return null;} public android.content.pm.PackageManager getPackageManager(){return null;} public void startActivity(Intent i){} public static final int MODE_PRIVATE=0; public SharedPreferences getSharedPreferences(String n,int m){return null;} public Intent registerReceiver(Object r,IntentFilter f){return null;}}''',
'android/content/Intent.java': '''package android.content; public class Intent {public static final String ACTION_VIEW="",ACTION_BATTERY_CHANGED=""; public Intent(String a){} public Intent(String a,android.net.Uri uri){} public Intent(Context c,Class<?> cls){} public String getStringExtra(String x){return null;} public int getIntExtra(String k,int d){return d;} public boolean hasExtra(String k){return false;} }''',
'android/content/SharedPreferences.java': '''package android.content; public interface SharedPreferences {int getInt(String k,int v);Editor edit();interface Editor {Editor putInt(String k,int v);void apply();boolean commit();}}''',
'android/content/IntentFilter.java': '''package android.content; public class IntentFilter {public IntentFilter(String s){} }''',
'android/content/pm/PackageManager.java': '''package android.content.pm; public class PackageManager {public Object getPackageInfo(String name,int flags) throws NameNotFoundException{return null;} public android.content.Intent getLaunchIntentForPackage(String p){return null;} public android.graphics.drawable.Drawable getApplicationIcon(String p) throws NameNotFoundException{return null;} public static class NameNotFoundException extends Exception{} }''',
'android/util/DisplayMetrics.java': '''package android.util; public class DisplayMetrics {public float density; public int widthPixels;}''',
'android/graphics/drawable/Drawable.java': '''package android.graphics.drawable; public class Drawable {}''',
'android/graphics/drawable/GradientDrawable.java': '''package android.graphics.drawable; public class GradientDrawable extends Drawable {public void setColor(int c){} public void setCornerRadius(float c){} public void setStroke(int a,int b){} }''',
'android/os/BatteryManager.java': '''package android.os; public class BatteryManager {public static final String EXTRA_LEVEL="", EXTRA_SCALE="";}''',
'android/os/Handler.java': '''package android.os; public class Handler {public Handler(Looper l){} public void postDelayed(Runnable r,long ms){} public void removeCallbacks(Runnable r){} }''',
'android/os/Looper.java': '''package android.os; public class Looper {public static Looper getMainLooper(){return null;} }''',
'android/view/Gravity.java': '''package android.view; public class Gravity {public static final int CENTER_VERTICAL=1,CENTER=2,END=4,TOP=8,CENTER_HORIZONTAL=16;}''',
'android/view/View.java': '''package android.view; public class View {public View(android.content.Context c){} public interface OnClickListener {void onClick(View v);} public void setOnClickListener(OnClickListener c){} public void setPadding(int a,int b,int c,int d){} public void setClickable(boolean b){} public void setFocusable(boolean b){} public void setBackgroundColor(int c){} public void setBackground(android.graphics.drawable.Drawable d){} public void setContentDescription(CharSequence a){} public android.content.res.Resources getResources(){return null;} }''',
'android/widget/LinearLayout.java': '''package android.widget; public class LinearLayout extends android.view.View {public static final int VERTICAL=1;public LinearLayout(android.content.Context c){super(c);} public void setOrientation(int o){} public void setGravity(int a){} public void removeAllViews(){} public void addView(android.view.View v){} public void addView(android.view.View v,LayoutParams p){} public static class LayoutParams {public int bottomMargin,topMargin;public LayoutParams(int a,int b){} public LayoutParams(int a,int b,float weight){} } }''',
'android/widget/ScrollView.java': '''package android.widget; public class ScrollView extends android.view.View {public ScrollView(android.content.Context c){super(c);} public void setFillViewport(boolean f){} public void addView(android.view.View v){} protected void onDetachedFromWindow(){} }''',
'android/widget/GridLayout.java': '''package android.widget; public class GridLayout extends android.view.View {public GridLayout(android.content.Context c){super(c);} public void setColumnCount(int c){} public void addView(android.view.View v, LayoutParams p){} public static class LayoutParams {public int width,height;} }''',
'android/widget/ImageView.java': '''package android.widget; public class ImageView extends android.view.View {public ImageView(android.content.Context c){super(c);} public static enum ScaleType {FIT_CENTER} public void setScaleType(ScaleType t){} public void setImageDrawable(android.graphics.drawable.Drawable d){} }''',
'android/widget/TextView.java': '''package android.widget; public class TextView extends android.view.View {public TextView(android.content.Context c){super(c);} public void setText(String s){} public void setTextSize(int s){} public void setTextColor(int c){} public void setGravity(int g){} public void setTypeface(android.graphics.Typeface f,int style){} public void setMaxLines(int n){} }''',
})

def run() -> None:
    with tempfile.TemporaryDirectory(prefix='red-home-compile-') as td:
        tmp=Path(td)
        for name,src in STUBS.items():
            f=tmp/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(src)
        java=ROOT/'launcher_src/java/dev/twoyi/redlauncher/RedNativeDashboard.java'
        files=[*tmp.rglob('*.java'),java,ROOT/'launcher_src/java/dev/twoyi/redlauncher/RedRootProbe.java', ROOT/'launcher_src/java/dev/twoyi/redlauncher/RedAccentStore.java', ROOT/'launcher_src/java/dev/twoyi/redlauncher/DashboardGridPolicy.java']
        p=subprocess.run(['javac','-d',str(tmp/'classes'),*(str(f) for f in files)],capture_output=True,text=True)
        if p.returncode:raise SystemExit('NATIVE HOME JAVA STUB COMPILE FAILED: '+p.stderr)
        print('NATIVE_HOME_JAVA_STUB_COMPILE_PASS (NOT an Android SDK build)')

if __name__=='__main__':run()
