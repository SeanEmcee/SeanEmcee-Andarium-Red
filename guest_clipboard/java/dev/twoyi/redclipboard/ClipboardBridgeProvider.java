// SPDX-License-Identifier: Apache-2.0
package dev.twoyi.redclipboard;

import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.ContentProvider;
import android.content.ContentValues;
import android.database.Cursor;
import android.net.Uri;
import android.os.Binder;
import android.os.Bundle;
import android.os.Process;
import android.util.Base64;
import java.nio.charset.StandardCharsets;
import java.nio.ByteBuffer;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.CharacterCodingException;

/** Explicit text-only bridge, callable through authenticated host ADB shell.
 *  Reads are NEVER automatic; the host only requests a read after a user taps Copy.
 *  No network socket, telemetry, persistent storage or clipboard listeners.
 */
public final class ClipboardBridgeProvider extends ContentProvider {
    public static final int MAX_BYTES = 32768;
    private static final int BASE64_FLAGS = Base64.URL_SAFE | Base64.NO_WRAP | Base64.NO_PADDING;

    @Override public boolean onCreate() { return true; }

    @Override public Bundle call(String method, String arg, Bundle extras) {
        int uid = Binder.getCallingUid();
        if (uid != Process.SHELL_UID && uid != Process.ROOT_UID) {
            throw new SecurityException("Clipboard bridge is restricted to local shell callers");
        }
        Bundle reply = new Bundle();
        if (getContext() == null) {
            reply.putString("status", "not_ready");
            return reply;
        }
        ClipboardManager clipboard = (ClipboardManager)
                getContext().getSystemService(android.content.Context.CLIPBOARD_SERVICE);
        if (clipboard == null) {
            reply.putString("status", "not_ready");
            return reply;
        }
        if ("read".equals(method)) {
            try {
                ClipData clip = clipboard.getPrimaryClip();
                if (clip == null || clip.getItemCount() == 0 || clip.getItemAt(0).getText() == null) {
                    reply.putString("b64", "~");
                    return reply;
                }
                byte[] data = clip.getItemAt(0).getText().toString().getBytes(StandardCharsets.UTF_8);
                if (data.length > MAX_BYTES) {
                    reply.putString("status", "too_large");
                    return reply;
                }
                reply.putString("b64", Base64.encodeToString(data, BASE64_FLAGS));
            } catch (SecurityException unavailable) {
                reply.putString("status", "permission_denied");
            }
            return reply;
        }
        if ("write".equals(method)) {
            String encoded = extras == null ? null : extras.getString("b64");
            if (encoded == null || encoded.length() > (MAX_BYTES * 4 / 3 + 8)) {
                reply.putString("status", "too_large");
                return reply;
            }
            // Accept canonical, unpadded URL-safe Base64 only. Android's decoder
            // is intentionally permissive; the wire protocol must not be.
            if (!encoded.matches("[A-Za-z0-9_-]*")) {
                reply.putString("status", "invalid_input");
                return reply;
            }
            try {
                byte[] data = Base64.decode(encoded, BASE64_FLAGS);
                // Android's decoder permits some final base64 sextets with
                // non-zero unused bits (e.g. AB for a zero byte). Re-encode
                // to guarantee the caller sent exactly one canonical form.
                if (!Base64.encodeToString(data, BASE64_FLAGS).equals(encoded)) {
                    reply.putString("status", "invalid_input");
                    return reply;
                }
                if (data.length > MAX_BYTES) {
                    reply.putString("status", "too_large");
                    return reply;
                }
                String text = StandardCharsets.UTF_8.newDecoder()
                        .onMalformedInput(CodingErrorAction.REPORT)
                        .onUnmappableCharacter(CodingErrorAction.REPORT)
                        .decode(ByteBuffer.wrap(data)).toString();
                clipboard.setPrimaryClip(ClipData.newPlainText("From iOS", text));
                reply.putString("status", "ok");
            } catch (IllegalArgumentException | CharacterCodingException invalid) {
                reply.putString("status", "invalid_input");
            } catch (SecurityException denied) {
                reply.putString("status", "permission_denied");
            }
            return reply;
        }
        reply.putString("status", "unknown_method");
        return reply;
    }

    @Override public Cursor query(Uri uri, String[] projection, String selection, String[] selectionArgs,
                                  String sortOrder) { throw new UnsupportedOperationException(); }
    @Override public String getType(Uri uri) { return null; }
    @Override public Uri insert(Uri uri, ContentValues values) { throw new UnsupportedOperationException(); }
    @Override public int delete(Uri uri, String selection, String[] selectionArgs) { throw new UnsupportedOperationException(); }
    @Override public int update(Uri uri, ContentValues values, String selection, String[] selectionArgs) {
        throw new UnsupportedOperationException();
    }
}
