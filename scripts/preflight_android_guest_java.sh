#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Fail quickly on invalid Andarium Red guest Java modules before AOSP sync.
# This is a source-level preflight, not a replacement for pinned Soong.
set -euo pipefail
sdk="$(printenv ANDROID_HOME || echo /usr/local/lib/android/sdk)"
test -d "$sdk/platforms" || { echo 'ERROR: hosted Android SDK platform directory missing' >&2; exit 2; }
jar="$(find "$sdk/platforms" -maxdepth 2 -name android.jar -type f | sort -V | tail -n 1)"
test -n "$jar" || { echo 'ERROR: no Android SDK stub jar found' >&2; exit 2; }
echo "PRECOMPILE_ANDROID_SDK=$jar"
javac -version
mkdir -p .build/guest-java/launcher .build/guest-java/clipboard
find launcher_src/java -type f -name '*.java' -print0 |
  xargs -0 javac -encoding UTF-8 -source 17 -target 17 -cp "$jar" \
    -d .build/guest-java/launcher
find guest_clipboard/java -type f -name '*.java' -print0 |
  xargs -0 javac -encoding UTF-8 -source 17 -target 17 -cp "$jar" \
    -d .build/guest-java/clipboard
python3 -B - <<'PY'
import xml.etree.ElementTree as ET
for path in ('launcher_src/AndroidManifest.xml', 'guest_clipboard/AndroidManifest.xml'):
    assert ET.parse(path).getroot().tag == 'manifest', path
    print('VALID_ANDROID_XML='+path)
PY
echo 'ANDARIUM_GUEST_JAVA_SOURCE_PREFLIGHT_PASS'
