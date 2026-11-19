#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Compile the real Android RGB provider against local Java mocks.

Pure Java behavior checks. This is NOT an Android 17/Soong compile or an
iPhone clipboard/guest runtime test.
"""
from pathlib import Path
import subprocess
import tempfile

from accent_store_behavior_test import ROOT, SOURCES as ACCENT_SOURCES

SOURCES = dict(ACCENT_SOURCES)
SOURCES.update({
    'android/content/ContentProvider.java': '''package android.content;
      import android.net.Uri; import android.database.Cursor; import android.os.Bundle;
      public abstract class ContentProvider {
        public static Context attached;
        public Context getContext(){return attached;}
        public abstract boolean onCreate();
        public abstract Bundle call(String method,String arg,Bundle extras);
        public abstract Cursor query(Uri uri,String[] projection,String selection,String[] args,String sortOrder);
        public abstract String getType(Uri uri);
        public abstract Uri insert(Uri uri,ContentValues values);
        public abstract int delete(Uri uri,String selection,String[] args);
        public abstract int update(Uri uri,ContentValues values,String selection,String[] args);
      }''',
    'android/content/ContentValues.java': 'package android.content; public class ContentValues {}',
    'android/database/Cursor.java': 'package android.database; public interface Cursor {}',
    'android/net/Uri.java': 'package android.net; public class Uri {}',
    'android/os/Binder.java': '''package android.os;
      public class Binder {public static int uid=2000; public static int getCallingUid(){return uid;}}''',
    'android/os/Process.java': '''package android.os;
      public class Process {public static final int SHELL_UID=2000,ROOT_UID=0;}''',
    'android/os/Bundle.java': '''package android.os;
      import java.util.HashMap; import java.util.Map;
      public class Bundle {
        private final Map<String,Object> values=new HashMap<>();
        public void putString(String key,String value){values.put(key,value);}
        public void putInt(String key,int value){values.put(key,value);}
        public String getString(String key){Object v=values.get(key);return v instanceof String?(String)v:null;}
        public boolean containsKey(String key){return values.containsKey(key);}
        public int getInt(String key,int fallback){
          Object v=values.get(key);return v instanceof Integer?(Integer)v:fallback;
        }
      }''',
    'dev/twoyi/redlauncher/ThemeProviderHarness.java': r'''package dev.twoyi.redlauncher;
      import android.content.*;
      import android.os.*;
      public final class ThemeProviderHarness {
        private static int checks;
        private static void ok(boolean value,String why){
          if(!value)throw new AssertionError(why); checks++;
        }
        private static Bundle arg(int color){
          Bundle b=new Bundle();b.putInt("rgb",color);return b;
        }
        public static void main(String[] ignored){
          RedAccentStoreHarness.Ctx context=new RedAccentStoreHarness.Ctx();
          ContentProvider.attached=context;
          RedThemeProvider provider=new RedThemeProvider();
          Binder.uid=Process.SHELL_UID;
          ok(provider.onCreate(),"create");
          ok(provider.call("get",null,null).getString("rgb").equals("15870787"),"default");
          ok(provider.call("set",null,arg(0x12ABFE)).getString("status").equals("ok"),"write");
          ok(provider.call("get",null,null).getString("rgb").equals("1223678"),"readback");
          ok(provider.call("set",null,arg(-1)).getString("status").equals("invalid_input"),"negative");
          ok(provider.call("set",null,arg(0x1000000)).getString("status").equals("invalid_input"),"overflow");
          ok(provider.call("set",null,null).getString("status").equals("invalid_input"),"missing");
          Bundle wrong=new Bundle();wrong.putString("rgb","not an integer");
          ok(provider.call("set",null,wrong).getString("status").equals("invalid_input"),"type");
          ok(provider.call("get",null,null).getString("rgb").equals("1223678"),"invalid leaves original");
          ok(provider.call("noop",null,null).getString("status").equals("unknown_method"),"method");
          Binder.uid=12345;
          boolean blocked=false;
          try{provider.call("set",null,arg(0));}catch(SecurityException denied){blocked=true;}
          ok(blocked,"no unprivileged write");
          blocked=false;
          try{provider.call("get",null,null);}catch(SecurityException denied){blocked=true;}
          ok(blocked,"no unprivileged read");
          Binder.uid=Process.ROOT_UID;
          ok(provider.call("set",null,arg(0xFFFFFF)).getString("status").equals("ok"),"root set");
          ok(provider.call("get",null,null).getString("rgb").equals("16777215"),"root read");
          ContentProvider.attached=null;
          ok(provider.call("get",null,null).getString("status").equals("not_ready"),"absent context");
          System.out.println("RED_THEME_PROVIDER_"+checks+"_PASS (local stubs; not guest execution)");
        }
      }''',
})


def run():
    with tempfile.TemporaryDirectory(prefix="red-theme-provider-") as temp:
        folder = Path(temp)
        files = []
        for name, source in SOURCES.items():
            file = folder / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(source)
            files.append(file)
        files.extend([
            ROOT / 'launcher_src/java/dev/twoyi/redlauncher/RedAccentStore.java',
            ROOT / 'launcher_src/java/dev/twoyi/redlauncher/RedThemeProvider.java',
        ])
        compiled = subprocess.run(['javac', '-d', str(folder/'classes'), *map(str,files)],
                                  capture_output=True, text=True, timeout=45)
        if compiled.returncode:
            raise RuntimeError(compiled.stderr)
        tested = subprocess.run(['java', '-cp', str(folder/'classes'),
                                 'dev.twoyi.redlauncher.ThemeProviderHarness'],
                                capture_output=True, text=True, timeout=15)
        if tested.returncode:
            raise RuntimeError(tested.stdout + tested.stderr)
        print(tested.stdout.strip())


if __name__ == '__main__':
    run()
