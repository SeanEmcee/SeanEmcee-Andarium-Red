// SPDX-License-Identifier: Apache-2.0
package dev.twoyi.redlauncher;

import android.content.ContentProvider;
import android.content.ContentValues;
import android.database.Cursor;
import android.net.Uri;
import android.os.Binder;
import android.os.Bundle;
import android.os.Process;

/**
 * Local-only theme transport for the authenticated iOS host's guest ADB shell.
 *
 * ADB's shell UID can read/set a checked 24-bit color without changing the
 * foreground Activity or restarting Android. No sockets, web access, or
 * background clipboard access are involved. The manifest additionally
 * requires android.permission.DUMP on the exported provider.
 */
public final class RedThemeProvider extends ContentProvider {
    public static final String AUTHORITY = "dev.twoyi.redlauncher.theme";

    @Override public boolean onCreate() { return true; }

    @Override public Bundle call(String method, String arg, Bundle extras) {
        int caller = Binder.getCallingUid();
        if (caller != Process.SHELL_UID && caller != Process.ROOT_UID) {
            throw new SecurityException("Andarium theme bridge is shell-only");
        }
        Bundle answer = new Bundle();
        if (getContext() == null) {
            answer.putString("status", "not_ready");
            return answer;
        }
        if ("get".equals(method)) {
            answer.putString("rgb", Integer.toString(RedAccentStore.load(getContext())));
            return answer;
        }
        if (!"set".equals(method)) {
            answer.putString("status", "unknown_method");
            return answer;
        }
        if (extras == null || !extras.containsKey("rgb")) {
            answer.putString("status", "invalid_input");
            return answer;
        }
        int rgb = extras.getInt("rgb", -1);
        if (!RedAccentStore.validRGB(rgb)) {
            answer.putString("status", "invalid_input");
            return answer;
        }
        answer.putString("status",
            RedAccentStore.acceptRGB(getContext(), rgb) ? "ok" : "persistence_failed");
        return answer;
    }

    @Override public Cursor query(Uri uri, String[] projection, String selection,
                                  String[] args, String sortOrder) {
        throw new UnsupportedOperationException();
    }
    @Override public String getType(Uri uri) { return null; }
    @Override public Uri insert(Uri uri, ContentValues values) {
        throw new UnsupportedOperationException();
    }
    @Override public int delete(Uri uri, String selection, String[] args) {
        throw new UnsupportedOperationException();
    }
    @Override public int update(Uri uri, ContentValues values, String selection,
                                String[] args) {
        throw new UnsupportedOperationException();
    }
}
