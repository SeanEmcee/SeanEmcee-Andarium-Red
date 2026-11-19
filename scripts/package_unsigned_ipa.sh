#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Package an existing, genuinely compiled iPhoneOS .app as a standard IPA.
# Never re-sign, modify entitlements, or substitute a Simulator build.
set -euo pipefail

if (( $# != 3 )); then
  echo "Usage: bash scripts/package_unsigned_ipa.sh APP_PATH OUTPUT_DIR {preview|host}" >&2
  exit 2
fi
app="$1"
outdir="$2"
kind="$3"
case "$kind" in
  preview) expected="AndariumPreview.app"; label="AndariumRed-UI-Preview-Unsigned" ;;
  host) expected="Andarium.app"; label="AndariumRed-FullHost-Unsigned" ;;
  *) echo "ERROR: unknown app kind: $kind" >&2; exit 2 ;;
esac
if [[ ! -d "$app" || "$(basename "$app")" != "$expected" ]]; then
  echo "ERROR: expected compiled $expected at $app" >&2
  exit 1
fi
plist="$app/Info.plist"
if [[ ! -f "$plist" ]]; then
  echo "ERROR: compiled app is missing Info.plist" >&2; exit 1
fi
plisttool=/usr/libexec/PlistBuddy
bundle="$("$plisttool" -c 'Print :CFBundleIdentifier' "$plist")"
executable="$("$plisttool" -c 'Print :CFBundleExecutable' "$plist")"
platform="$("$plisttool" -c 'Print :CFBundleSupportedPlatforms:0' "$plist")"
version="$("$plisttool" -c 'Print :MinimumOSVersion' "$plist")"
if [[ -z "$bundle" || -z "$executable" || "$platform" != iPhoneOS ]]; then
  echo "ERROR: not an iPhoneOS app: bundle=$bundle platform=$platform" >&2; exit 1
fi
bin="$app/$executable"
if [[ ! -f "$bin" ]]; then echo "ERROR: app executable missing" >&2; exit 1; fi
if ! xcrun lipo -archs "$bin" | grep -Eq '(^|[[:space:]])arm64($|[[:space:]])'; then
  echo "ERROR: compiled app does not contain an arm64 slice" >&2; exit 1
fi
if ! xcrun vtool -show-build "$bin" | grep -Eq 'platform[[:space:]]+IOS$'; then
  echo "ERROR: Mach-O is not built for iPhoneOS (possibly a Simulator build)" >&2
  exit 1
fi
mkdir -p "$outdir"
outdir="$(cd "$outdir" && pwd)"
staging="$(mktemp -d)"
trap 'rm -rf "$staging"' EXIT
mkdir -p "$staging/Payload"
ditto "$app" "$staging/Payload/$expected"
(
  cd "$staging"
  ditto -c -k --sequesterRsrc --keepParent Payload "$outdir/$label.ipa"
)
unzip -tq "$outdir/$label.ipa" >/dev/null
if ! unzip -Z1 "$outdir/$label.ipa" | grep -Fxq "Payload/$expected/Info.plist"; then
  echo "ERROR: IPA must contain Payload/$expected/Info.plist" >&2; exit 1
fi
# This is intentionally not a signed distribution IPA.
{
  printf 'App: %s\n' "$expected"
  printf 'Bundle identifier: %s\n' "$bundle"
  printf 'Platform: %s\n' "$platform"
  printf 'Minimum iOS: %s\n' "$version"
  printf 'Signing: unsigned, no provisioning profile supplied\n'
  if [[ "$kind" == preview ]]; then
    printf 'Scope: UI-only preview; no Android guest runtime or Android 17 image\n'
  else
    printf 'Scope: compiled native host; Android guest functionality must be verified separately\n'
  fi
  shasum -a 256 "$outdir/$label.ipa"
} | tee "$outdir/$label.txt"
echo "IPA_PACKAGE_VERIFIED: $outdir/$label.ipa"
