#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Run locally on a Mac / configured build host; never uses GitHub Actions.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/first_build.sh /absolute/path/to/Kernarium [--build]
Default: preflight, integrate Andarium Red v15 into pinned checkout, and test.
--build: also stage the accepted Android image/runtime and attempt an UNSIGNED
Xcode smoke build. Neither signs nor installs an IPA. Modified Android guest
modules require a separately rebuilt Android 17 proof image.
EOF
}
if (( $# < 1 || $# > 2 )); then usage; exit 2; fi
KERNARIUM="$1"
BUILD=""
if (( $# == 2 )); then BUILD="$2"; fi
if [[ -n "$BUILD" && "$BUILD" != "--build" ]]; then usage; exit 2; fi
SOURCE="$(cd "$(dirname "$0")/.." && pwd)"
KERNARIUM="$(cd "$KERNARIUM" && pwd)"

if [[ ! -f "$KERNARIUM/Andarium/Andarium.xcodeproj/project.xcproj" ]]; then
  echo "ERROR: Not a complete Kernarium Xcode checkout." >&2
  exit 1
fi
echo "Checking source integration without mutation..."
python3 "$SOURCE/integrate_andarium.py" \
  --kernarium "$KERNARIUM" --source "$SOURCE" --dry-run
echo "Applying source changes..."
python3 "$SOURCE/integrate_andarium.py" \
  --kernarium "$KERNARIUM" --source "$SOURCE"
echo "Running first-build source gates..."
python3 "$SOURCE/tools/first_build_gate.py" \
  --kernarium "$KERNARIUM" --source "$SOURCE"

if [[ "$BUILD" != "--build" ]]; then
  echo "Source checks completed. Use --build on macOS after configuring dependencies."
  exit 0
fi
if [[ "$(uname -s)" != Darwin ]] || ! command -v xcodebuild >/dev/null; then
  echo "ERROR: --build requires macOS and Xcode 27; no build attempted." >&2
  exit 1
fi

cd "$KERNARIUM"
echo "Packaging Kernarium iOS Android runtime..."
cmake --preset kernarium-ios-device-android
cmake --build --preset kernarium-ios-device-android
Kernarium/scripts/package-ios-frameworks.sh --runtimes android

echo "Staging the accepted guest image..."
echo "NOTE: an older accepted upstream image does NOT contain the new Red guest launcher/modules."
echo "To test custom Android guest code, rebuild an Android 17 unsigned proof first."
Andarium/scripts/stage-system-image.py

echo "Checking prepared artifacts..."
python3 "$SOURCE/tools/first_build_gate.py" \
  --kernarium "$KERNARIUM" --source "$SOURCE" --require-artifacts

echo "Attempting non-signed first Xcode compiler build..."
xcodebuild -project Andarium/Andarium.xcodeproj -scheme Andarium \
  -configuration Release -destination 'generic/platform=iOS' \
  CODE_SIGNING_ALLOWED=NO build
echo "Unsigned compile completed. Signing, entitlements and device run are separate release gates."
