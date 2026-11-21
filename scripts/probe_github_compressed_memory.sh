#!/usr/bin/env bash
# Probe disposable GitHub-hosted Ubuntu kernel compression support.
set -euo pipefail
[[ "$GITHUB_ACTIONS" == true && "$RUNNER_ENVIRONMENT" == github-hosted && "$RUNNER_OS" == Linux ]] || exit 2
echo "KERNEL=$(uname -r)"
echo "RAM_SWAP_BEFORE"; free -h; swapon --show
if [[ -e /sys/module/zswap/parameters/enabled ]]; then
  echo "ZSWAP_AVAILABLE=yes"
  echo "ZSWAP_ENABLED=$(cat /sys/module/zswap/parameters/enabled)"
  if sudo sh -c 'echo Y > /sys/module/zswap/parameters/enabled' 2>/dev/null; then
    echo "ZSWAP_RUNTIME_ENABLE=success"
    echo "ZSWAP_COMPRESSOR=$(cat /sys/module/zswap/parameters/compressor 2>/dev/null || true)"
  else
    echo "ZSWAP_RUNTIME_ENABLE=denied"
  fi
else
  echo "ZSWAP_AVAILABLE=no"
fi
if ! sudo modprobe zram >/dev/null 2>&1; then
  echo "ZRAM_MODULE=unavailable"
  exit 0
fi
if [[ ! -e /sys/class/zram-control/hot_add && ! -e /sys/block/zram0/disksize ]]; then
  echo "ZRAM_DEVICE=unavailable"
  exit 0
fi
if [[ -e /sys/class/zram-control/hot_add ]]; then
  devnum="$(cat /sys/class/zram-control/hot_add)"
  dev="/dev/zram$devnum"
else
  dev=/dev/zram0
fi
if [[ ! -b "$dev" ]]; then
  echo "ZRAM_DEVICE_NOT_BLOCK=$dev"
  exit 0
fi
cleanup() {
  sudo swapoff "$dev" >/dev/null 2>&1 || true
  if [[ -e "/sys/block/$(basename "$dev")/reset" ]]; then
    echo 1 | sudo tee "/sys/block/$(basename "$dev")/reset" >/dev/null || true
  fi
}
trap cleanup EXIT
echo lz4 | sudo tee "/sys/block/$(basename "$dev")/comp_algorithm" >/dev/null 2>&1 || true
echo 1073741824 | sudo tee "/sys/block/$(basename "$dev")/disksize" >/dev/null
sudo mkswap "$dev" >/dev/null
if sudo swapon -p 100 "$dev"; then
  echo "ZRAM_SWAP_TEST=success"
  swapon --show
  free -h
else
  echo "ZRAM_SWAP_TEST=failed"
fi
