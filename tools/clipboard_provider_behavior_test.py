#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exercise real ClipboardBridgeProvider Java behavior against local Android-shaped stubs.

This uses the provider's unmodified source, not a mock of its logic. It does NOT
prove Android 17 platform permission, signature or end-to-end iOS bridging.
"""
from __future__ import annotations
import subprocess
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FILES={
'android/content/Context.java':'''package android.content;
public class Context { public static final String CLIPBOARD_SERVICE="clipboard";
  public static final ClipboardManager manager=new ClipboardManager();
  public Object getSystemService(String name){return manager;}}
''',
'android/content/ClipData.java':'''package android.content;
public class ClipData {
  private final Item item;
  private ClipData(String s) {item=new Item(s);}
  public static ClipData newPlainText(String label,String content){return new ClipData(content);}
  public int getItemCount(){return 1;}
  public Item getItemAt(int n){return item;}
  public static class Item {private final String s; Item(String s){this.s=s;} public CharSequence getText(){return s;}}
}''',
'android/content/ClipboardManager.java':'''package android.content;
public class ClipboardManager {
  private ClipData value;
  public ClipData getPrimaryClip(){return value;}
  public void setPrimaryClip(ClipData d){value=d;}
}''',
'android/content/ContentValues.java':'package android.content;public class ContentValues {}',
'android/content/ContentProvider.java':'''package android.content;
import android.os.Bundle;import android.net.Uri;import android.database.Cursor;
public abstract class ContentProvider {
 public abstract boolean onCreate();public Bundle call(String method,String arg,Bundle extras){return null;}
 public Context getContext(){return new Context();}
 public abstract Cursor query(Uri u,String[] p,String s,String[] a,String o);
 public abstract String getType(Uri u);
 public abstract Uri insert(Uri u,ContentValues v);
 public abstract int delete(Uri u,String s,String[] a);
 public abstract int update(Uri u,ContentValues v,String s,String[] a);
}''',
'android/database/Cursor.java':'package android.database;public interface Cursor {}',
'android/net/Uri.java':'package android.net;public class Uri {}',
'android/os/Binder.java':'package android.os;public class Binder {public static int uid=2000;public static int getCallingUid(){return uid;}}',
'android/os/Bundle.java':'''package android.os;
public class Bundle {private final java.util.HashMap<String,String> map=new java.util.HashMap<>();
public void putString(String k,String v){map.put(k,v);}public String getString(String k){return map.get(k);}}''',
'android/os/Process.java':'package android.os;public class Process {public static final int SHELL_UID=2000,ROOT_UID=0;}',
'android/util/Base64.java':'''package android.util;
public class Base64 {
 public static final int URL_SAFE=8,NO_WRAP=2,NO_PADDING=1;
 public static String encodeToString(byte[] bytes,int flags){return java.util.Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);}
 public static byte[] decode(String text,int flags){return java.util.Base64.getUrlDecoder().decode(text);}
}''',
'RedClipboardBehaviorHarness.java':'''import dev.twoyi.redclipboard.ClipboardBridgeProvider;
import android.os.Binder;import android.os.Bundle;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
public class RedClipboardBehaviorHarness {
 static void ok(boolean yes,String why) {if(!yes)throw new AssertionError(why);}
 public static void main(String[] args) {
   ClipboardBridgeProvider provider = new ClipboardBridgeProvider();
   ok(provider.onCreate(),"onCreate");
   String content="A☀️\\nAndroid17 red clipboard";
   String b64=Base64.getUrlEncoder().withoutPadding().encodeToString(content.getBytes(StandardCharsets.UTF_8));
   Bundle input=new Bundle();input.putString("b64",b64);
   ok("ok".equals(provider.call("write",null,input).getString("status")),"write rejected");
   ok(b64.equals(provider.call("read",null,null).getString("b64")),"read mismatch");
   Binder.uid=10001;
   boolean denied=false;
   try{provider.call("read",null,null);}catch(SecurityException blocked){denied=true;}
   ok(denied,"untrusted app could access provider");
   Binder.uid=0;
   ok(b64.equals(provider.call("read",null,null).getString("b64")),"root caller rejected");
   Binder.uid=2000;
   Bundle invalid=new Bundle();invalid.putString("b64","###");
   ok("invalid_input".equals(provider.call("write",null,invalid).getString("status")),"invalid Base64 accepted");
   Bundle huge=new Bundle();huge.putString("b64","A".repeat(50000));
   ok("too_large".equals(provider.call("write",null,huge).getString("status")),"too-large input accepted");
   Bundle brokenUTF8=new Bundle();
   brokenUTF8.putString("b64",Base64.getUrlEncoder().withoutPadding().encodeToString(new byte[]{(byte)0xc3,(byte)0x28}));
   ok("invalid_input".equals(provider.call("write",null,brokenUTF8).getString("status")),"malformed UTF-8 accepted");
   Bundle noncanonical=new Bundle();noncanonical.putString("b64",b64+"=");
   ok("invalid_input".equals(provider.call("write",null,noncanonical).getString("status")),"padded base64 accepted");
   Bundle nonzeroPadBits=new Bundle();nonzeroPadBits.putString("b64","AB");
   ok("invalid_input".equals(provider.call("write",null,nonzeroPadBits).getString("status")),"nonzero unused base64 bits accepted");
   ok("unknown_method".equals(provider.call("erase",null,null).getString("status")),"unknown method accepted");
   ok(b64.equals(provider.call("read",null,null).getString("b64")),"tests destroyed clipboard state");
   System.out.println("CLIPBOARD_PROVIDER_BEHAVIOR_PASS (10 assertions; local Android stubs)");
 }
}'''
}

def run():
    with tempfile.TemporaryDirectory(prefix='clipboard-behavior-') as td:
        root=Path(td)
        for rel,body in FILES.items():
            path=root/rel;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(body)
        provider=ROOT/'guest_clipboard/java/dev/twoyi/redclipboard/ClipboardBridgeProvider.java'
        sources=[*root.rglob('*.java'),provider]
        comp=subprocess.run(['javac','-d',str(root/'classes'),*(str(s) for s in sources)],capture_output=True,text=True)
        if comp.returncode:raise RuntimeError('Provider behavior compile failed: '+comp.stderr)
        result=subprocess.run(['java','-cp',str(root/'classes'),'RedClipboardBehaviorHarness'],capture_output=True,text=True)
        if result.returncode:raise RuntimeError('Provider behavior failed: '+result.stderr)
        print(result.stdout.strip())

if __name__=='__main__':run()
