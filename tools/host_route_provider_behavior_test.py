#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Compile and exercise the actual host mailbox provider with Android API stubs.

Runs normal Java provider logic, including UID gating and ack/retry persistence.
This is NOT a device/iOS run, Android SDK compile, or proof of actual ADB latency.
"""
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JAVA = ROOT / "launcher_src/java/dev/twoyi/redlauncher"

STUBS = {
"android/content/Context.java": """package android.content;
public class Context {
 public static final int MODE_PRIVATE=0;
 private static final SharedPreferences prefs = new SharedPreferences();
 public SharedPreferences getSharedPreferences(String n,int mode){return prefs;}
 public ContentResolver getContentResolver(){return new ContentResolver();}
}""",
"android/content/SharedPreferences.java": """package android.content;
import java.util.*;
public class SharedPreferences {
 private final Map<String,Object> data=new HashMap<>();
 public String getString(String k,String fallback){Object v=data.get(k);return v instanceof String?(String)v:fallback;}
 public long getLong(String k,long fallback){Object v=data.get(k);return v instanceof Long?(Long)v:fallback;}
 public Editor edit(){return new Editor();}
 public final class Editor {
  private final Map<String,Object> changes=new HashMap<>();
  private final Set<String> removes=new HashSet<>();
  public Editor putString(String k,String v){changes.put(k,v);return this;}
  public Editor putLong(String k,long v){changes.put(k,v);return this;}
  public Editor remove(String k){removes.add(k);return this;}
  public boolean commit(){for(String k:removes)data.remove(k);data.putAll(changes);return true;}
 }
}""",
"android/content/ContentProvider.java": """package android.content;
import android.database.Cursor;import android.net.Uri;import android.os.Bundle;
public abstract class ContentProvider {
 private final Context context=new Context();
 public Context getContext(){return context;}
 public Bundle call(String method,String arg,Bundle extras){return null;}
 public abstract boolean onCreate();
 public abstract Cursor query(Uri uri,String[] projection,String selection,String[] args,String sortOrder);
 public abstract String getType(Uri uri);
 public abstract Uri insert(Uri uri,ContentValues values);
 public abstract int delete(Uri uri,String where,String[] args);
 public abstract int update(Uri uri,ContentValues values,String where,String[] args);
}""",
"android/content/ContentResolver.java": """package android.content;
import android.net.Uri;import android.os.Bundle;
public class ContentResolver {
 public Bundle call(Uri uri,String method,String arg,Bundle extras){
  return new dev.twoyi.redlauncher.HostLaunchBridgeProvider().call(method,arg,extras);
 }
}""",
"android/content/ContentValues.java": "package android.content; public class ContentValues {}",
"android/database/Cursor.java": "package android.database; public interface Cursor {}",
"android/net/Uri.java": """package android.net;
public class Uri {public static Uri parse(String input){return new Uri();}}""",
"android/os/Binder.java": """package android.os;
public class Binder {private static int uid=10000;
 public static void setUid(int n){uid=n;}
 public static int getCallingUid(){return uid;}
}""",
"android/os/Bundle.java": """package android.os;import java.util.*;
public class Bundle {
 private final Map<String,String> fields=new HashMap<>();
 public void putString(String k,String v){fields.put(k,v);}
 public String getString(String k){return fields.get(k);}
}""",
"android/os/Process.java": """package android.os;
public class Process {public static final int SHELL_UID=2000,ROOT_UID=0;
 public static int myUid(){return 10000;}}""",
"dev/twoyi/redlauncher/HostLaunchProviderHarness.java": """package dev.twoyi.redlauncher;
import android.os.Binder;
import android.os.Bundle;
public final class HostLaunchProviderHarness {
 private static int checks;
 private static void ok(boolean condition,String message){
  if(!condition)throw new AssertionError(message);checks++;
 }
 private static String field(HostLaunchBridgeProvider p,String method,String arg,String key){
  Bundle r=p.call(method,arg,null);return r.getString(key);
 }
 public static void main(String[] args){
  HostLaunchBridgeProvider p=new HostLaunchBridgeProvider();
  Binder.setUid(34567);
  ok("permission_denied".equals(field(p,"enqueue","nexaris","status")),"foreign app denied");
  ok("permission_denied".equals(field(p,"next",null,"status")),"foreign app cannot read");
  ok("permission_denied".equals(field(p,"ack","bad","status")),"foreign app cannot ack");
  Binder.setUid(10000);
  ok("invalid_route".equals(field(p,"enqueue","shell","status")),"arbitrary host action");
  ok("ok".equals(field(p,"enqueue","nexaris","status")),"enqueue Nexaris");
  ok("busy".equals(field(p,"enqueue","rapkeys","status")),"first request retained");
  ok("permission_denied".equals(field(p,"next",null,"status")),"app cannot impersonate shell");
  Binder.setUid(2000);
  String event=field(p,"next",null,"event");
  String id=HostLaunchWire.eventId(event);
  ok(id!=null,"next emits well formed id");
  ok("nexaris".equals(HostLaunchWire.eventRoute(event)),"route preserved");
  ok("stale".equals(field(p,"ack","00000000000000000000000000000000","status")),"wrong ack");
  ok(event.equals(field(p,"next",null,"event")),"unacked request retained");
  ok("ok".equals(field(p,"ack",id,"status")),"ack clears correct request");
  ok("~".equals(field(p,"next",null,"event")),"empty mailbox");
  ok("stale".equals(field(p,"ack",id,"status")),"replay prevented");
  Binder.setUid(10000);
  ok("ok".equals(field(p,"enqueue","urlos","status")),"second route accepted");
  Binder.setUid(0);
  ok("urlos".equals(HostLaunchWire.eventRoute(field(p,"next",null,"event"))),
     "root ADB reader can inspect");
  ok("unknown_method".equals(field(p,"other",null,"status")),"unknown operation rejected");
  System.out.println("HOST_LAUNCH_PROVIDER_"+checks+"_PASS");
 }
}""",
}


def run():
    with tempfile.TemporaryDirectory(prefix="android-host-mailbox-") as d:
        root=Path(d)
        for name, text in STUBS.items():
            dest=root/name;dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_text(text)
        sources=[*root.rglob("*.java"),
                 JAVA/"HostLaunchWire.java", JAVA/"HostLaunchBridgeProvider.java"]
        p=subprocess.run(["javac","-d",str(root/"classes"),
                          *(str(s) for s in sources)],capture_output=True,text=True)
        if p.returncode:
            raise RuntimeError("Android host mailbox source compile failed: "+p.stderr)
        p=subprocess.run(["java","-cp",str(root/"classes"),
                          "dev.twoyi.redlauncher.HostLaunchProviderHarness"],
                         capture_output=True,text=True)
        if p.returncode:
            raise RuntimeError("Android host mailbox behavior failed: "+p.stdout+p.stderr)
        print(p.stdout.strip())


if __name__=="__main__":
    run()
