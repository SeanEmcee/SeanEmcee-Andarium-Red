#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Add compressed RAM swap on disposable free GitHub-hosted x86_64 Linux only.
# No preallocated RAM. Disk swap remains as an emergency overflow mechanism.
set -euo pipefail
if [[ "$GITHUB_ACTIONS" != true || "$RUNNER_OS" != Linux ||
      "$RUNNER_ENVIRONMENT" != github-hosted || "$(uname -m)" != x86_64 ]]; then
  echo "ERROR: extra ZRAM is restricted to disposable GitHub-hosted Ubuntu x86_64" >&2
  exit 2
fi
gib="$1"
if [[ "$gib" != 6 && "$gib" != 1 ]]; then
  echo "ERROR: supported verified sizes are 1 GiB probe or 6 GiB hosted build" >&2
  exit 2
fi
if [[ ! -e /sys/class/zram-control/hot_add ]]; then
  echo "ERROR: runner kernel does not support separate ZRAM devices" >&2
  exit 1
fi
sudo modprobe zram
device_no="$(sudo cat /sys/class/zram-control/hot_add)"
if [[ ! "$device_no" =~ ^[0-9]+$ ]] || [[ "$device_no" == 0 ]]; then
  echo "ERROR: unsafe or non-new ZRAM device number" >&2
  exit 1
fi
device="/dev/zram$device_no"
sys="/sys/block/zram$device_no"
if [[ ! -b "$device" || ! -f "$sys/disksize" ]]; then
  echo "ERROR: newly allocated ZRAM block device unavailable" >&2
  exit 1
fi
reset_on_fail() {
  sudo swapoff "$device" >/dev/null 2>&1 || true
  echo 1 | sudo tee "$sys/reset" >/dev/null 2>&1 || true
}
trap reset_on_fail ERR
# LZ4 is generally preferable to disk I/O for compressible Soong heap pages.
if grep -qw lz4 "$sys/comp_algorithm"; then
  echo lz4 | sudo tee "$sys/comp_algorithm" >/dev/null
fi
sudo sh -c 'echo "$1" > "$2"' _ "$((gib * 1024 * 1024 * 1024))" "$sys/disksize"
sudo mkswap "$device" >/dev/null
sudo swapon -p 100 "$device"
trap - ERR
if ! swapon --show=NAME --noheadings | grep -Fxq "$device"; then
  echo "ERROR: additional ZRAM is not active" >&2
  reset_on_fail
  exit 1
fi
echo "ANDARIUM_ADDITIONAL_ZRAM_DEVICE=$device"
echo "ANDARIUM_ADDITIONAL_ZRAM_SWAP_GIB=$gib"
echo "ANDARIUM_ADDITIONAL_ZRAM_COMPRESSION=$(cat "$sys/comp_algorithm")"
free -h
swapon --show
