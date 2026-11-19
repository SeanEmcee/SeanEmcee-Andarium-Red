// SPDX-License-Identifier: Apache-2.0
package dev.twoyi.redlauncher;

import android.content.ContentProvider;
import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.net.Uri;
import android.os.Binder;
import android.os.Bundle;
import android.os.Process;

/** Host-to-guest network path receipt, not a virtual Wi-Fi HAL replacement.
 * ADB shell may set only a fixed, enumerated status. Guest launcher UID may read.
 * No external application can submit an invented iOS connection.
 */
public final class RedHostTransportProvider extends ContentProvider {
    static final String AUTHORITY = "dev.twoyi.redlauncher.hostnetwork";
    private static final String PREFS = "red_host_transport";
    private static final String KEY = "route";

    @Override public boolean onCreate() { return true; }

    @Override public Bundle call(String method, String arg, Bundle extras) {
        int uid = Binder.getCallingUid();
        Context context = getContext();
        if (context == null) throw new IllegalStateException("Context unavailable");
        if ("set".equals(method)) {
            if (uid != Process.SHELL_UID) throw new SecurityException("Only authenticated ADB shell may update host route");
            if (!RedHostTransportStatus.isHostValue(arg))
                throw new IllegalArgumentException("Invalid host transport status");
            context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putString(KEY, arg).apply();
            Bundle reply = new Bundle();
            reply.putString("transport", arg);
            return reply;
        }
        if ("get".equals(method)) {
            if (uid != Process.SHELL_UID && uid != Process.myUid())
                throw new SecurityException("Host route is visible only to the launcher UID");
            String value = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                .getString(KEY, RedHostTransportStatus.UNKNOWN);
            Bundle reply = new Bundle();
            reply.putString("transport", value);
            return reply;
        }
        throw new IllegalArgumentException("Unknown network-status method");
    }

    @Override public Cursor query(Uri uri, String[] projection, String selection,
                                  String[] selectionArgs, String sortOrder) {
        throw new UnsupportedOperationException("Read host network status with get only");
    }
    @Override public String getType(Uri uri) { return null; }
    @Override public Uri insert(Uri uri, ContentValues values) {
        throw new UnsupportedOperationException("Not a network-setting API");
    }
    @Override public int delete(Uri uri, String selection, String[] selectionArgs) {
        throw new UnsupportedOperationException("Not a network-setting API");
    }
    @Override public int update(Uri uri, ContentValues values, String selection,
                                String[] selectionArgs) {
        throw new UnsupportedOperationException("Not a network-setting API");
    }
}
