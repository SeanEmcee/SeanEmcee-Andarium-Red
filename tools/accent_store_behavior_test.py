#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Run the real RedAccentStore against tiny Java stubs (not Android SDK)."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    'android/content/Context.java': '''package android.content;
        public class Context { public static final int MODE_PRIVATE=0;
          public SharedPreferences getSharedPreferences(String key,int flags){return null;} }''',
    'android/content/SharedPreferences.java': '''package android.content;
        public interface SharedPreferences { int getInt(String key,int fallback); Editor edit();
          interface Editor {Editor putInt(String key,int value); void apply(); boolean commit();}}''',
    'android/content/Intent.java': '''package android.content;
        public class Intent {public boolean hasExtra(String name){return false;}
          public int getIntExtra(String name,int fallback){return fallback;}}''',
    'android/graphics/Color.java': '''package android.graphics;
        public class Color {public static int rgb(int r,int g,int b){return 0xFF000000 | r<<16 | g<<8 | b;}}''',
    'dev/twoyi/redlauncher/RedAccentStoreHarness.java': r'''package dev.twoyi.redlauncher;
        import android.content.*;
        import java.util.*;
        public class RedAccentStoreHarness {
          static class Prefs implements SharedPreferences, SharedPreferences.Editor {
            Map<String,Integer> saved=new HashMap<>();
            public int getInt(String k,int fallback){return saved.getOrDefault(k,fallback);}
            public SharedPreferences.Editor edit(){return this;}
            public SharedPreferences.Editor putInt(String k,int v){saved.put(k,v);return this;}
            public void apply(){}\n            public boolean commit(){return true;}
          }
          static class Ctx extends Context {
            Prefs prefs = new Prefs();
            @Override public SharedPreferences getSharedPreferences(String k,int m){return prefs;}
          }
          static class Launch extends Intent {
            boolean present; int rgb;
            Launch(boolean present,int rgb){this.present=present;this.rgb=rgb;}
            @Override public boolean hasExtra(String key){return present && key.equals(RedAccentStore.EXTRA_RGB);}
            @Override public int getIntExtra(String key,int fallback){return rgb;}
          }
          static void eq(boolean ok,String msg){if(!ok)throw new AssertionError(msg);}
          public static void main(String[] args){
            Ctx c=new Ctx();
            eq(RedAccentStore.load(c)==0xF22B43,"default");
            eq(!RedAccentStore.acceptLaunchAccent(c,null),"null");
            eq(!RedAccentStore.acceptLaunchAccent(c,new Launch(false,0)),"absent");
            eq(RedAccentStore.load(c)==0xF22B43,"unchanged");
            eq(RedAccentStore.acceptLaunchAccent(c,new Launch(true,0x12ABFE)),"accept");
            eq(RedAccentStore.load(c)==0x12ABFE,"persisted");
            eq(RedAccentStore.color(0x12ABFE)==0xFF12ABFE,"argb");
            eq(!RedAccentStore.acceptLaunchAccent(c,new Launch(true,-1)),"negative");
            eq(!RedAccentStore.acceptLaunchAccent(c,new Launch(true,0x1000000)),"overflow");
            eq(RedAccentStore.load(c)==0x12ABFE,"invalid unchanged");
            eq(RedAccentStore.acceptLaunchAccent(c,new Launch(true,0x0)),"black");
            eq(RedAccentStore.load(c)==0x0,"black persisted");
            c.prefs.saved.put("nexaris_accent_rgb", -5);
            eq(RedAccentStore.load(c)==0xF22B43,"corrupt fallback");
            System.out.println("ACCENT_STORE_13_PASS (local Java stubs; not guest boot)");
          }
        }'''
}

def run():
    with tempfile.TemporaryDirectory(prefix='accent-java-') as d:
        d=Path(d)
        sources=[]
        for name, source in SOURCES.items():
            p=d/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(source)
            sources.append(p)
        sources.append(ROOT/'launcher_src/java/dev/twoyi/redlauncher/RedAccentStore.java')
        compile=subprocess.run(['javac','-d',str(d/'classes'),*[str(p) for p in sources]],capture_output=True,text=True)
        if compile.returncode:raise RuntimeError(compile.stderr)
        result=subprocess.run(['java','-cp',str(d/'classes'),'dev.twoyi.redlauncher.RedAccentStoreHarness'],capture_output=True,text=True)
        if result.returncode:raise RuntimeError(result.stdout+result.stderr)
        print(result.stdout.strip())

if __name__=='__main__':run()
