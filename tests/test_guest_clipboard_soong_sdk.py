#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Regression: vendor/product Java modules use an explicit stable SDK.

This is a small source-contract test, NOT a substitute for Soong compilation.
The pinned Soong source enforces Java's checkSdkVersions and checkPlatformAPI.
"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
clipboard = (ROOT / "guest_clipboard/Android.bp").read_text(encoding="utf-8")
assert re.search(r'(?m)^android_app\s*\{', clipboard)
def property(name):
    m = re.search(r"(?m)^\s*" + re.escape(name) + r"\s*:\s*([^,\n]+)", clipboard)
    return m.group(1).strip() if m else None

assert property("name") == '"TwoyiRedClipboard"'
assert property("sdk_version") == '"system_current"', "product modules require a stable SDK declaration"
assert property("platform_apis") in (None, "false"), "SDK and platform_apis=true conflict in pinned Soong"
assert property("product_specific") == "true", "do not move clipboard bridge into a different partition"
assert property("privileged") == "true", "preserve existing privileged-install policy"
assert property("certificate") == '"platform"', "preserve platform certificate policy"
assert property("manifest") == '"AndroidManifest.xml"'
assert property("srcs") is not None

from importlib.util import spec_from_file_location, module_from_spec
spec = spec_from_file_location("overlay", ROOT / "install_source_overlay.py")
overlay = module_from_spec(spec)
sys.modules[spec.name] = overlay
spec.loader.exec_module(overlay)
assert overlay.CLIPBOARD_MODULE == "TwoyiRedClipboard"
assert overlay.APP_MODULE == "TwoyiRedLauncher"
assert 'sdk_version: "current"' in overlay.LAUNCHER_BP
assert "mods.append(CLIPBOARD_MODULE)" in (ROOT / "install_source_overlay.py").read_text()
assert "shutil.copytree(clip_src, clip_dest)" in (ROOT / "install_source_overlay.py").read_text()
provider = (ROOT / "guest_clipboard/java/dev/twoyi/redclipboard/ClipboardBridgeProvider.java").read_text()
for required in ("android.content.ClipboardManager", "android.content.ContentProvider",
                 "android.os.Binder", "android.os.Process"):
    assert required in provider
manifest = (ROOT / "guest_clipboard/AndroidManifest.xml").read_text()
assert "android.permission.READ_CLIPBOARD_IN_BACKGROUND" in manifest
print("PASS: Android17 product-app stable system SDK, no conflicting platform APIs, privileges preserved")
