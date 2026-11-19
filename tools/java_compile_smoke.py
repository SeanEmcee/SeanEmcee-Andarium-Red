#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Syntax-check the Android provider with tiny local API stubs.

This checks Java source compilation only. Actual Android 17 / Soong compilation
must still be performed using the upstream AOSP build environment.
"""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
STUBS = {
  'android/content/Context.java': 'package android.content; public class Context {public static final String CLIPBOARD_SERVICE="clipboard"; public Object getSystemService(String name){return null;}}',
  'android/content/ClipData.java': 'package android.content; public class ClipData {public static ClipData newPlainText(String label, String text){return null;} public int getItemCount(){return 0;} public Item getItemAt(int n){return null;} public static class Item {public CharSequence getText(){return null;}}}',
  'android/content/ClipboardManager.java': 'package android.content; public class ClipboardManager {public ClipData getPrimaryClip(){return null;} public void setPrimaryClip(ClipData clip){}}',
  'android/content/ContentValues.java': 'package android.content; public class ContentValues {}',
  'android/content/ContentProvider.java': '''package android.content; import android.os.Bundle; import android.net.Uri; import android.database.Cursor; public abstract class ContentProvider {public abstract boolean onCreate(); public Bundle call(String method,String arg,Bundle extras){return null;} public Context getContext(){return null;} public abstract Cursor query(Uri uri,String[] p,String selection,String[] args,String order); public abstract String getType(Uri uri); public abstract Uri insert(Uri uri,ContentValues v); public abstract int delete(Uri uri,String s,String[] a); public abstract int update(Uri uri,ContentValues v,String s,String[] a);}''',
  'android/database/Cursor.java': 'package android.database; public interface Cursor {}',
  'android/net/Uri.java': 'package android.net; public class Uri {}',
  'android/os/Binder.java': 'package android.os; public class Binder { public static int getCallingUid(){return 2000;} }',
  'android/os/Bundle.java': 'package android.os; public class Bundle { public void putString(String k,String v){} public String getString(String k){return "";} }',
  'android/os/Process.java': 'package android.os; public class Process {public static final int SHELL_UID=2000, ROOT_UID=0;}',
  'android/util/Base64.java': 'package android.util; public class Base64 {public static final int URL_SAFE=8,NO_WRAP=2,NO_PADDING=1; public static String encodeToString(byte[] d,int flags){return "";} public static byte[] decode(String s,int flags){return new byte[0];}}',
}


def main():
    with tempfile.TemporaryDirectory() as td:
        temp = Path(td)
        for rel, source in STUBS.items():
            target = temp / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(source)
        apk_source = ROOT/'guest_clipboard/java/dev/twoyi/redclipboard/ClipboardBridgeProvider.java'
        args = ['javac','-Xlint:all','-d',str(temp/'classes'),*map(str,temp.glob('android/**/*.java')),str(apk_source)]
        subprocess.run(args,check=True,capture_output=True,text=True)
        print('JAVA_PROVIDER_SYNTAX_PASS (local API stubs; not Android build)')

if __name__=='__main__':main()
