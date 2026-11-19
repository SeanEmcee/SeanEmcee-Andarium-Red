#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Typecheck RedPanelActivity against a small, explicit Android-API-shaped stub set.

NOT an Android SDK/Soong build, not a promise of runtime Android 17 compatibility.
"""
from __future__ import annotations
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUBS = {
'android/content/Context.java': '''package android.content; public class Context { public android.content.res.Resources getResources(){return null;} public android.content.pm.PackageManager getPackageManager(){return null;} public void startActivity(Intent i){} public static final int MODE_PRIVATE=0; public SharedPreferences getSharedPreferences(String n,int m){return null;} public ContentResolver getContentResolver(){return null;} }''',
'android/content/ContentValues.java': '''package android.content; public class ContentValues {}''',
'android/content/ContentResolver.java': '''package android.content; public class ContentResolver { public android.os.Bundle call(android.net.Uri uri,String method,String arg,android.os.Bundle extras){return null;} }''',
'android/content/ContentProvider.java': '''package android.content; public abstract class ContentProvider { public Context getContext(){return null;} public abstract boolean onCreate(); public android.os.Bundle call(String method,String arg,android.os.Bundle extras){return null;} public abstract android.database.Cursor query(android.net.Uri uri,String[] projection,String selection,String[] selectionArgs,String sortOrder); public abstract String getType(android.net.Uri uri); public abstract android.net.Uri insert(android.net.Uri uri,ContentValues values); public abstract int delete(android.net.Uri uri,String selection,String[] selectionArgs); public abstract int update(android.net.Uri uri,ContentValues values,String selection,String[] selectionArgs); }''',
'android/database/Cursor.java': '''package android.database; public interface Cursor {}''',
'android/os/Process.java': '''package android.os; public class Process {public static final int SHELL_UID=2000; public static int myUid(){return 10000;} }''',
'android/os/Binder.java': '''package android.os; public class Binder {public static int getCallingUid(){return 10000;} }''',
'android/content/Intent.java': '''package android.content; public class Intent { public static final String ACTION_VIEW=""; public Intent(String a){} public Intent(String a,android.net.Uri uri){} public Intent(Context c,Class<?> cls){} public Intent setPackage(String p){return this;} public String getStringExtra(String x){return null;} public int getIntExtra(String k,int d){return d;} public boolean hasExtra(String k){return false;} public Intent putExtra(String k,String v){return this;} }''',
'android/content/SharedPreferences.java': '''package android.content; public interface SharedPreferences {int getInt(String k,int v);String getString(String k,String v);Editor edit();interface Editor {Editor putInt(String k,int v);Editor putString(String k,String v);void apply();}}''',
'android/content/ActivityNotFoundException.java': '''package android.content; public class ActivityNotFoundException extends RuntimeException {}''',
'android/content/DialogInterface.java': '''package android.content; public interface DialogInterface { interface OnClickListener {void onClick(DialogInterface d,int which);} }''',
'android/content/pm/PackageManager.java': '''package android.content.pm; public class PackageManager { public Object getPackageInfo(String name,int flags) throws NameNotFoundException{return null;} public android.content.Intent getLaunchIntentForPackage(String p){return null;} public static class NameNotFoundException extends Exception{} }''',
'android/content/res/Resources.java': '''package android.content.res; public class Resources { public android.util.DisplayMetrics getDisplayMetrics(){return null;} }''',
'android/util/DisplayMetrics.java': '''package android.util; public class DisplayMetrics {public float density;}''',
'android/app/Activity.java': '''package android.app; public class Activity extends android.content.Context { protected void onCreate(android.os.Bundle b){} public android.view.Window getWindow(){return null;} public android.content.Intent getIntent(){return null;} public void setContentView(android.view.View v){} public void finish(){} public void runOnUiThread(Runnable r){} }''',
'android/app/AlertDialog.java': '''package android.app; public class AlertDialog { public static class Builder {public Builder(android.content.Context c){} public Builder setTitle(String s){return this;} public Builder setMessage(String s){return this;} public Builder setPositiveButton(String s,android.content.DialogInterface.OnClickListener l){return this;} public AlertDialog show(){return null;} } }''',
'android/graphics/Color.java': '''package android.graphics; public class Color { public static final int WHITE=0, BLACK=0;public static int rgb(int r,int g,int b){return 0;} }''',
'android/graphics/Typeface.java': '''package android.graphics; public class Typeface {public static final Typeface DEFAULT=new Typeface();public static final int BOLD=1,NORMAL=0;}''',
'android/net/Uri.java': '''package android.net; public class Uri {public static Uri parse(String a){return null;} public String getHost(){return null;} public String getScheme(){return null;} }''',
'android/os/Build.java': '''package android.os; public class Build {public static String DISPLAY=""; public static class VERSION {public static String RELEASE="",SECURITY_PATCH="";} }''',
'android/os/Bundle.java': '''package android.os; public class Bundle {public String getString(String k){return null;} public void putString(String k,String v){} }''',
'android/provider/Settings.java': '''package android.provider; public class Settings { public static final String ACTION_SETTINGS="",ACTION_WIRELESS_SETTINGS="",ACTION_APPLICATION_SETTINGS="", ACTION_NOTIFICATION_SETTINGS="", ACTION_DISPLAY_SETTINGS="", ACTION_INTERNAL_STORAGE_SETTINGS="",ACTION_PRIVACY_SETTINGS="",ACTION_SECURITY_SETTINGS="",ACTION_SYNC_SETTINGS="",ACTION_ACCESSIBILITY_SETTINGS="",ACTION_DEVICE_INFO_SETTINGS="",ACTION_APPLICATION_DEVELOPMENT_SETTINGS="",ACTION_INPUT_METHOD_SETTINGS="",ACTION_MANAGE_DEFAULT_APPS_SETTINGS=""; }''',
'android/text/InputType.java': '''package android.text; public class InputType {public static final int TYPE_CLASS_TEXT=1, TYPE_TEXT_VARIATION_URI=2;}''',
'android/view/Gravity.java': '''package android.view; public class Gravity {public static final int CENTER_VERTICAL=1;}''',
'android/view/View.java': '''package android.view; public class View {public View(android.content.Context c){} public interface OnClickListener {void onClick(View v);} public void setOnClickListener(OnClickListener c){} public void setPadding(int a,int b,int c,int d){} public void setClickable(boolean b){} public void setFocusable(boolean b){} public void setBackgroundColor(int c){} }''',
'android/view/Window.java': '''package android.view; public class Window {public void setStatusBarColor(int c){} public void setNavigationBarColor(int c){} public void setFlags(int a,int b){} }''',
'android/view/WindowManager.java': '''package android.view; public class WindowManager {public static class LayoutParams { public static final int FLAG_FULLSCREEN=4;} }''',
'android/widget/LinearLayout.java': '''package android.widget; public class LinearLayout extends android.view.View {public static final int VERTICAL=1;public LinearLayout(android.content.Context c){super(c);} public void setOrientation(int o){} public void addView(android.view.View v){} public void addView(android.view.View v, LayoutParams p){} public static class LayoutParams {public int bottomMargin; public LayoutParams(int a,int b){};} }''',
'android/widget/ScrollView.java': '''package android.widget; public class ScrollView extends android.view.View {public ScrollView(android.content.Context c){super(c);} public void setFillViewport(boolean f){} public void addView(android.view.View v){} }''',
'android/widget/TextView.java': '''package android.widget; public class TextView extends android.view.View {public TextView(android.content.Context c){super(c);} public void setText(String s){} public void setTextSize(int s){} public void setTextColor(int c){} public void setGravity(int g){} public void setTypeface(android.graphics.Typeface f,int style){} public void setHintTextColor(int c){} public void setHint(String c){} public CharSequence getText(){return "";} }''',
'android/widget/EditText.java': '''package android.widget; public class EditText extends TextView {public EditText(android.content.Context c){super(c);} public void setSingleLine(boolean b){} public void setInputType(int i){} }''',
'android/widget/Toast.java': '''package android.widget; public class Toast {public static final int LENGTH_SHORT=0; public static Toast makeText(android.content.Context c,String s,int t){return null;} public void show(){} }''',
}

def run() -> None:
    with tempfile.TemporaryDirectory(prefix='red-panel-compile-') as temp:
        path=Path(temp)
        for name, text in STUBS.items():
            f=path/name
            f.parent.mkdir(parents=True,exist_ok=True)
            f.write_text(text)
        sources=list(path.rglob('*.java')) + [ROOT/'launcher_src/java/dev/twoyi/redlauncher/PanelLinkPolicy.java',ROOT/'launcher_src/java/dev/twoyi/redlauncher/RedPanelActivity.java',ROOT/'launcher_src/java/dev/twoyi/redlauncher/RedAccentStore.java',ROOT/'launcher_src/java/dev/twoyi/redlauncher/RedRootProbe.java',ROOT/'launcher_src/java/dev/twoyi/redlauncher/RedHostTransportStatus.java',ROOT/'launcher_src/java/dev/twoyi/redlauncher/RedHostTransportProvider.java']
        result=subprocess.run(['javac','-d',str(path/'classes'),*[str(p) for p in sources]],capture_output=True,text=True)
        if result.returncode:
            raise SystemExit('RED PANEL STUB COMPILE FAILED: '+result.stderr)
        print('RED_PANEL_JAVA_STUB_COMPILE_PASS (NOT an Android build)')

if __name__=='__main__':run()
