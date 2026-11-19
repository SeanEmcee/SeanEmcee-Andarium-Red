#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Read-only runtime acceptance: actual Android 17, root UID, and Magisk status.
# Run only against a guest the user owns and has explicitly started.
# No automatic elevation, rooting, patching, or arbitrary command execution.
set -euo pipefail
if (( $# != 1 )) || [[ ! "$1" =~ ^[A-Za-z0-9_.:-]{1,128}$ ]]; then
  echo "Usage: bash scripts/check_red_root_runtime.sh ADB_GUEST_SERIAL" >&2
  exit 2
fi
serial="$1"
if ! command -v adb >/dev/null; then
  echo "ROOT_ACCEPTANCE_BLOCKED: adb unavailable" >&2
  exit 2
fi
if [[ "$(adb -s "$serial" get-state 2>/dev/null)" != device ]]; then
  echo "ROOT_ACCEPTANCE_BLOCKED: selected Android guest is not connected" >&2
  exit 2
fi
android="$(adb -s "$serial" shell getprop ro.build.version.release | tr -d '\r\n')"
if [[ "$android" != 17 ]]; then
  echo "ROOT_ACCEPTANCE_FAILED: expected booted Android 17, got $android" >&2
  exit 1
fi
if ! adb -s "$serial" shell pm path dev.twoyi.redlauncher 2>/dev/null | grep -q '^package:'; then
  echo "ROOT_ACCEPTANCE_FAILED: actual Red launcher not installed" >&2
  exit 1
fi
echo "ANDROID17_GUEST_BOOTED_AND_RED_LAUNCHER_INSTALLED"
# The userdebug image may offer adb root (shell privilege); this does not
# establish app-facing Magisk su, so only the following consented su path counts.
uid="$(adb -s "$serial" shell su -c 'id -u' 2>/dev/null | tr -d '\r\n' || true)"
if [[ "$uid" != 0 ]]; then
  echo "ROOT_ACCEPTANCE_FAILED: app-style su cannot prove UID 0" >&2
  exit 1
fi
echo "GUEST_SU_UID0_CONFIRMED"
magisk="$(adb -s "$serial" shell su -c 'magisk -v' 2>/dev/null | tr -d '\r\n' || true)"
if [[ ! "$magisk" =~ ^[A-Za-z0-9._+()\ -]{1,96}$ ]]; then
  echo "MAGISK_ACCEPTANCE_NOT_MET: UID 0 works, but no legitimate Magisk daemon/version verified" >&2
  exit 1
fi
echo "MAGISK_DAEMON_VERSION_CONFIRMED=$magisk"
echo "GUEST_ROOT_RUNTIME_CHECK_PASS"
echo "NOTE: test app-level consent, SELinux, persistence, and LiveContainer separately."
