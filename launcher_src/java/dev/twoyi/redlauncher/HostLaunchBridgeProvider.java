// SPDX-License-Identifier: Apache-2.0
package dev.twoyi.redlauncher;

import android.content.ContentProvider;
import android.content.ContentResolver;
import android.content.ContentValues;
import android.content.Context;
import android.content.SharedPreferences;
import android.database.Cursor;
import android.net.Uri;
import android.os.Binder;
import android.os.Bundle;
import android.os.Process;

/** Guest-to-host route mailbox. The launcher enqueues only built-in host apps;
 * an authenticated ADB shell reader fetches and acknowledges the request.
 *
 * The host MUST verify the exact event wire format and only dispatch when
 * Andarium is the active, registered Nexaris guest. No arbitrary Android app
 * or web URL gets authority to execute anything in iOS.
 */
public final class HostLaunchBridgeProvider extends ContentProvider {
    public static final Uri URI = Uri.parse("content://" + HostLaunchWire.AUTHORITY + "/launch");
    private static final String STORE = "andarium.red.host.launch.v1";
    private static final String PENDING = "event";
    private static final String TIME = "at";
    private static final long EXPIRATION_MS = 120000L;
    private final Object gate = new Object();

    private static Bundle field(String key, String value) {
        Bundle response = new Bundle();
        response.putString(key, value);
        return response;
    }

    public static boolean request(Context app, String route) {
        if (!HostLaunchWire.allowed(route)) return false;
        Bundle result = app.getContentResolver().call(URI, "enqueue", route, null);
        return result != null && "ok".equals(result.getString("status"));
    }

    private boolean shellOnly() {
        int caller = Binder.getCallingUid();
        return caller == Process.SHELL_UID || caller == Process.ROOT_UID;
    }

    private SharedPreferences store() {
        return getContext().getSharedPreferences(STORE, Context.MODE_PRIVATE);
    }

    private String pending(SharedPreferences prefs) {
        String event = prefs.getString(PENDING, null);
        if (event == null) return null;
        long when = prefs.getLong(TIME, 0L);
        long elapsed = System.currentTimeMillis() - when;
        if (HostLaunchWire.eventId(event) == null ||
                when < 1L || elapsed < 0L || elapsed > EXPIRATION_MS) {
            prefs.edit().remove(PENDING).remove(TIME).commit();
            return null;
        }
        return event;
    }

    @Override public Bundle call(String method, String arg, Bundle extras) {
        synchronized (gate) {
            if ("enqueue".equals(method)) {
                if (Binder.getCallingUid() != Process.myUid())
                    return field("status", "permission_denied");
                if (!HostLaunchWire.allowed(arg)) return field("status", "invalid_route");
                SharedPreferences prefs = store();
                if (pending(prefs) != null) return field("status", "busy");
                String event = HostLaunchWire.event(arg);
                boolean saved = prefs.edit().putString(PENDING, event)
                    .putLong(TIME, System.currentTimeMillis()).commit();
                if (saved) gate.notifyAll();
                return field("status", saved ? "ok" : "storage_error");
            }
            if ("next".equals(method)) {
                if (!shellOnly()) return field("status", "permission_denied");
                String event = pending(store());
                // A short bounded Binder wait prevents repeated ADB shell
                // traffic while Android is idle. Enqueue wakes immediately.
                long waitMs = 0;
                if (arg != null && arg.matches("[0-9]{1,4}")) {
                    waitMs = Math.min(Long.parseLong(arg), 1000L);
                }
                if (event == null && waitMs > 0) {
                    try { gate.wait(waitMs); }
                    catch (InterruptedException interrupted) {
                        Thread.currentThread().interrupt();
                    }
                    event = pending(store());
                }
                return field("event", event == null ? "~" : event);
            }
            if ("ack".equals(method)) {
                if (!shellOnly()) return field("status", "permission_denied");
                SharedPreferences prefs = store();
                String event = pending(prefs);
                if (!HostLaunchWire.matchesAck(event, arg))
                    return field("status", "stale");
                return field("status", prefs.edit().remove(PENDING)
                    .remove(TIME).commit() ? "ok" : "storage_error");
            }
            return field("status", "unknown_method");
        }
    }

    @Override public boolean onCreate() { return true; }
    @Override public Cursor query(Uri uri, String[] projection, String selection,
                                  String[] args, String sortOrder) { return null; }
    @Override public String getType(Uri uri) { return null; }
    @Override public Uri insert(Uri uri, ContentValues values) { return null; }
    @Override public int delete(Uri uri, String where, String[] args) { return 0; }
    @Override public int update(Uri uri, ContentValues values, String where,
                                String[] args) { return 0; }
}
