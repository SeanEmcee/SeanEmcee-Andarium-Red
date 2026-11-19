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

/** Authenticated host-to-guest status bridge. It reports the iPhone's
 * currently usable Network.framework path, not an Android physical radio.
 * The virtual NIC remains active to transport packets over Wi-Fi or cellular.
 */
public final class HostNetworkBridgeProvider extends ContentProvider {
    private static final Uri URI =
        Uri.parse("content://dev.twoyi.redlauncher.network/status");
    private static final String STORE = "andarium.red.host.network.v1";
    private static final String KEY_STATE = "state";
    private static final String KEY_TIME = "time";
    private static final long FRESHNESS_MS = 90000L;
    private final Object gate = new Object();

    private static Bundle field(String key, String value) {
        Bundle response = new Bundle();
        response.putString(key, value);
        return response;
    }

    private boolean authenticatedHost() {
        int caller = Binder.getCallingUid();
        return caller == Process.SHELL_UID || caller == Process.ROOT_UID;
    }

    private boolean ownLauncher() {
        return Binder.getCallingUid() == Process.myUid();
    }

    private SharedPreferences stateStore() {
        return getContext().getSharedPreferences(STORE, Context.MODE_PRIVATE);
    }

    private String currentState() {
        SharedPreferences prefs = stateStore();
        long at = prefs.getLong(KEY_TIME, 0L);
        long age = System.currentTimeMillis() - at;
        String state = prefs.getString(KEY_STATE, HostNetworkState.UNKNOWN);
        if (at < 1 || age < 0 || age > FRESHNESS_MS ||
                !HostNetworkState.valid(state)) return HostNetworkState.UNKNOWN;
        return state;
    }

    public static String state(Context app) {
        try {
            Bundle result = app.getContentResolver().call(URI, "get", null, null);
            String state = result == null ? null : result.getString("state");
            return HostNetworkState.valid(state) ? state : HostNetworkState.UNKNOWN;
        } catch (RuntimeException unavailable) {
            return HostNetworkState.UNKNOWN;
        }
    }

    @Override public Bundle call(String method, String arg, Bundle extras) {
        synchronized (gate) {
            if ("set".equals(method)) {
                if (!authenticatedHost()) return field("status", "permission_denied");
                if (!HostNetworkState.valid(arg))
                    return field("status", "invalid_state");
                boolean saved = stateStore().edit()
                    .putString(KEY_STATE, arg)
                    .putLong(KEY_TIME, System.currentTimeMillis()).commit();
                return field("status", saved ? "ok" : "storage_error");
            }
            if ("get".equals(method)) {
                if (!ownLauncher() && !authenticatedHost())
                    return field("status", "permission_denied");
                return field("state", currentState());
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
