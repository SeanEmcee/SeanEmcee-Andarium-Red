// SPDX-License-Identifier: Apache-2.0
package dev.twoyi.redlauncher.bridge;

import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.os.Handler;
import android.os.Looper;
import java.nio.charset.StandardCharsets;

/**
 * Guest-side component of a local-only, explicit host clipboard bridge.
 * Not active in the supplied IPA: Twoyi must expose a real in-process transport.
 *
 * Do not send clipboard contents over public HTTP, log them, or persist them.
 * Android 13 restricts background clipboard reads. The callback must run while
 * the guest launcher is foreground or as an authorized system service.
 */
public final class GuestClipboardReporter implements ClipboardManager.OnPrimaryClipChangedListener {
    public interface HostTransport {
        void guestCopiedText(byte[] utf8);
    }

    private static final int LIMIT_BYTES = 1024 * 1024;
    private final ClipboardManager clipboard;
    private final HostTransport transport;
    private boolean started;
    private String lastSent;

    public GuestClipboardReporter(Context context, HostTransport transport) {
        this.clipboard = (ClipboardManager) context.getSystemService(Context.CLIPBOARD_SERVICE);
        this.transport = transport;
    }

    public void start() {
        if (started) return;
        if (clipboard == null || transport == null) return;
        clipboard.addPrimaryClipChangedListener(this);
        started = true;
    }

    public void stop() {
        if (!started) return;
        clipboard.removePrimaryClipChangedListener(this);
        started = false;
    }

    @Override public void onPrimaryClipChanged() {
        if (!started || !clipboard.hasPrimaryClip()) return;
        ClipData data = clipboard.getPrimaryClip();
        if (data == null || data.getItemCount() == 0) return;
        // Avoid implicit URI / Intent conversion and unintentional data leakage.
        CharSequence text = data.getItemAt(0).getText();
        if (text == null) return;
        String value = text.toString();
        if (value.equals(lastSent)) return;
        byte[] bytes = value.getBytes(StandardCharsets.UTF_8);
        if (bytes.length > LIMIT_BYTES) return;
        lastSent = value;
        transport.guestCopiedText(bytes);
    }
}
