#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Package ONLY the genuine compiled iPhoneOS Andarium Red host + Android 17
# guest. Refuse preview targets, upstream-only images and simulator binaries.
# Code signing remains LiveContainer's responsibility; this does not bypass it.
set -euo pipefail

if (( $# != 3 )); then
  echo "Usage: bash scripts/package_unsigned_ipa.sh APP_PATH OUTPUT_DIR MODIFIED_KERNARIUM_CHECKOUT" >&2
  exit 2
fi
app="$1"
outdir="$2"
checkout="$3"

if [[ ! -d "$app" || "$(basename "$app")" != "Andarium.app" ]]; then
  echo "ERROR: must supply the full modified Andarium.app, not AndariumPreview" >&2
  exit 1
fi
plist="$app/Info.plist"
if [[ ! -f "$plist" ]]; then
  echo "ERROR: compiled iPhoneOS app has no Info.plist" >&2
  exit 1
fi
plisttool=/usr/libexec/PlistBuddy
bundle="$("$plisttool" -c 'Print :CFBundleIdentifier' "$plist")"
executable="$("$plisttool" -c 'Print :CFBundleExecutable' "$plist")"
platform="$("$plisttool" -c 'Print :CFBundleSupportedPlatforms:0' "$plist")"
version="$("$plisttool" -c 'Print :MinimumOSVersion' "$plist")"
display="$("$plisttool" -c 'Print :CFBundleDisplayName' "$plist")"
if [[ "$bundle" != dev.andarium.red || "$display" != "Andarium Red" ]]; then
  echo "ERROR: the app has upstream/unknown branding (bundle=$bundle, name=$display), not modified Andarium Red" >&2
  exit 1
fi
if [[ -z "$bundle" || -z "$executable" || "$platform" != iPhoneOS ]]; then
  echo "ERROR: not a real iPhoneOS app: $bundle / $platform" >&2
  exit 1
fi
binary="$app/$executable"
if [[ ! -f "$binary" ]]; then
  echo "ERROR: missing compiled full-host executable" >&2
  exit 1
fi
if ! xcrun lipo -archs "$binary" | grep -Eq '(^|[[:space:]])arm64($|[[:space:]])'; then
  echo "ERROR: iPhoneOS executable does not contain arm64" >&2
  exit 1
fi
if ! xcrun vtool -show-build "$binary" | grep -Eq 'platform[[:space:]]+IOS$'; then
  echo "ERROR: Mach-O is not built for iPhoneOS" >&2
  exit 1
fi

# The guest must already be the real rebuilt Red Android 17 disk. In
# particular, do not relabel an upstream Andarium accepted image as Red.
python3 "$(cd "$(dirname "$0")" && pwd)/verify_red_android17_guest.py" \
  --app "$app" --kernarium "$checkout"

mkdir -p "$outdir"
outdir="$(cd "$outdir" && pwd)"
staging="$(mktemp -d)"
trap 'rm -rf "$staging"' EXIT
mkdir -p "$staging/Payload"
ditto "$app" "$staging/Payload/Andarium.app"
name="AndariumRed-Android17-FullHost-Unsigned"
(
  cd "$staging"
  ditto -c -k --sequesterRsrc --keepParent Payload "$outdir/$name.ipa"
)
unzip -tq "$outdir/$name.ipa" >/dev/null
for entry in \
  "Payload/Andarium.app/Info.plist" \
  "Payload/Andarium.app/andarium-system/release-manifest.json" \
  "Payload/Andarium.app/andarium-system/guest/system.img"; do
  if ! unzip -Z1 "$outdir/$name.ipa" | grep -Fxq "$entry"; then
    echo "ERROR: missing packaged Red payload: $entry" >&2
    exit 1
  fi
done
{
  echo "App: Andarium Red (modified full iPhoneOS host)"
  echo "Bundle identifier: $bundle"
  echo "Platform: $platform"
  echo "Minimum iOS: $version"
  echo "Guest: separately compiled Red Android 17 unsigned proof"
  echo "Signing: unsigned; LiveContainer must independently sign the guest IPA"
  echo "Device and LiveContainer boot: NOT VERIFIED"
  shasum -a 256 "$outdir/$name.ipa"
} | tee "$outdir/$name.txt"
echo "ANDARIUM_RED_IPA_PACKAGE_VERIFIED: $outdir/$name.ipa"
