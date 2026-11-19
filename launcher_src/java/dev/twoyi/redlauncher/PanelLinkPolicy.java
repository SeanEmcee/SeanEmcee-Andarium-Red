// SPDX-License-Identifier: Apache-2.0
package dev.twoyi.redlauncher;

import java.net.URI;
import java.net.URISyntaxException;
import java.util.Locale;

/** Fail-closed URL validation before handing a navigation to the actual Android browser. */
public final class PanelLinkPolicy {
    private PanelLinkPolicy() {}

    public static String normalized(String raw) {
        if (raw == null) throw new IllegalArgumentException("Missing website address");
        String candidate = raw.trim();
        if (candidate.isEmpty() || candidate.length() > 2048 || candidate.contains("\\") ||
                candidate.indexOf('\n') >= 0 || candidate.indexOf('\r') >= 0 ||
                candidate.indexOf('\t') >= 0) {
            throw new IllegalArgumentException("Invalid website address");
        }
        if (!candidate.contains("://")) candidate = "https://" + candidate;
        try {
            URI uri = new URI(candidate);
            String scheme = uri.getScheme();
            if (scheme == null || (!"http".equalsIgnoreCase(scheme) && !"https".equalsIgnoreCase(scheme))) {
                throw new IllegalArgumentException("Only http(s) websites are supported");
            }
            if (uri.getHost() == null || uri.getHost().isEmpty() || uri.getUserInfo() != null) {
                throw new IllegalArgumentException("Invalid website host");
            }
            if (uri.getPort() > 65535) throw new IllegalArgumentException("Invalid website port");
            return uri.toASCIIString();
        } catch (URISyntaxException err) {
            throw new IllegalArgumentException("Invalid website address", err);
        }
    }
}
