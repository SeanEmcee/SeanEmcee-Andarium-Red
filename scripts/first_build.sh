#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Run locally on a Mac / configured build host; never uses GitHub Actions.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: bash scripts/first_build.sh /path/to/Kernarium [options]
  --preview                Unsigned settings UI compile (no Android image needed)
  --build                  Unsigned full host build with runtime & Android image
  --with-apps              Fetch and SHA-256 validate the six pinned official
                           Android apps, then stage for ADB first-boot install
  --guest-proof DIRECTORY  Stage a separately built Android 17 unsigned proof
                           (only with --build)
The command uses no GitHub Actions, signing or silent Google Play downloads.
EOF
}
if (( $# < 1 )); then usage; exit 2; fi
if [[ "$1" == "-h" || "$1" == "--help" ]]; then usage; exit 0; fi
KERNARIUM="$1"
shift
BUILD=""
WITH_APPS=0
GUEST_PROOF=""
while (( $# )); do
  case "$1" in
    --preview|--build) BUILD="$1" ;;
    --with-apps) WITH_APPS=1 ;;
    --guest-proof)
      if (( $# < 2 )); then echo "ERROR: --guest-proof needs directory" >&2; exit 2; fi
      GUEST_PROOF="$2"; shift ;;
    *) echo "ERROR: unknown option: $1" >&2; usage; exit 2 ;;
  esac
  shift
done
if [[ -n "$GUEST_PROOF" && "$BUILD" != "--build" ]]; then
  echo "ERROR: --guest-proof requires --build" >&2; exit 2
fi
SOURCE="$(cd "$(dirname "$0")/.." && pwd)"
KERNARIUM="$(cd "$KERNARIUM" && pwd)"

if [[ ! -f "$KERNARIUM/Andarium/Andarium.xcodeproj/project.xcproj" ]]; then
  echo "ERROR: Not a complete Kernarium Xcode checkout." >&2
  exit 1
fi
FLAGS=()
if (( WITH_APPS )); then
  APKS="$SOURCE/.build/verified-official-apks"
  python3 "$SOURCE/tools/fetch_official_apks.py" --out "$APKS" \
    --only magisk titanium appmanager termux fdroid heliboard
  FLAGS=(
    --magisk-apk "$APKS/Magisk-v31.1.apk"
    --titanium-apk "$APKS/Titanium-v157.apk"
    --appmanager-apk "$APKS/AppManager-v4.1.1.apk"
    --termux-apk "$APKS/Termux-v0.118.3-arm64.apk"
    --fdroid-apk "$APKS/FDroid-v2.0.1.apk"
    --heliboard-apk "$APKS/HeliBoard-v4.2-release.apk"
  )
fi
echo "Checking source integration without mutation..."
python3 "$SOURCE/integrate_andarium.py" \
  --kernarium "$KERNARIUM" --source "$SOURCE" "${FLAGS[@]}" --dry-run
echo "Applying source changes..."
python3 "$SOURCE/integrate_andarium.py" \
  --kernarium "$KERNARIUM" --source "$SOURCE" "${FLAGS[@]}"
echo "Running first-build source gates..."
python3 "$SOURCE/tools/first_build_gate.py" \
  --kernarium "$KERNARIUM" --source "$SOURCE"
if (( WITH_APPS )); then
  echo "Auditing all bundled APK resources and signed publisher asset pins ..."
  python3 "$SOURCE/tools/audit_staged_apks.py" --kernarium "$KERNARIUM"
fi

if [[ -z "$BUILD" ]]; then
  echo "Source checks completed. Use --preview for a UI smoke build or --build for the full app."
  exit 0
fi
if [[ "$(uname -s)" != Darwin ]] || ! command -v xcodebuild >/dev/null; then
  echo "ERROR: first build requires macOS and Xcode 27; no build attempted." >&2
  exit 1
fi

cd "$KERNARIUM"
if [[ "$BUILD" == "--preview" ]]; then
  echo "Attempting unsigned AndariumPreview UI compilation (no Android image needed)..."
  xcodebuild -project Andarium/Andarium.xcodeproj -scheme AndariumPreview \
    -configuration Debug -destination 'generic/platform=iOS Simulator' \
    CODE_SIGNING_ALLOWED=NO build
  echo "Preview UI compiled. This does not prove Android runtime behavior."
  exit 0
fi

echo "Packaging Kernarium iOS Android runtime..."
cmake --preset kernarium-ios-device-android
cmake --build --preset kernarium-ios-device-android
Kernarium/scripts/package-ios-frameworks.sh --runtimes android

if [[ -n "$GUEST_PROOF" ]]; then
  if [[ ! -d "$GUEST_PROOF" ]]; then echo "ERROR: guest proof directory missing" >&2; exit 1; fi
  echo "Staging the rebuilt Android 17 unsigned proof image..."
  Andarium/scripts/stage-system-image.py --release "$GUEST_PROOF" --unsigned-proof
else
  echo "Staging upstream accepted image for host compiler smoke only."
  echo "This upstream image does not contain the Red native launcher or clipboard provider."
  Andarium/scripts/stage-system-image.py
fi

echo "Checking prepared artifacts..."
python3 "$SOURCE/tools/first_build_gate.py" \
  --kernarium "$KERNARIUM" --source "$SOURCE" --require-artifacts

echo "Attempting non-signed first Xcode compiler build..."
xcodebuild -project Andarium/Andarium.xcodeproj -scheme Andarium \
  -configuration Release -destination 'generic/platform=iOS' \
  CODE_SIGNING_ALLOWED=NO build
echo "Unsigned compile completed. Signing, entitlements and device run are separate release gates."
