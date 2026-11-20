#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Checked extra swap exclusively for disposable GitHub-hosted Ubuntu builders.
# Never run on the iPhone or on a self-hosted runner.
set -euo pipefail
if [[ "$GITHUB_ACTIONS" != true || "$RUNNER_OS" != Linux ||
      "$(uname -m)" != x86_64 || "$RUNNER_ENVIRONMENT" != github-hosted ]]; then
  echo 'ERROR: swap setup permitted only on GitHub-hosted Linux x86_64' >&2
  exit 2
fi
mode="$1"
if [[ "$mode" == --probe ]]; then
  swap_gib=1
  swap_name=andarium-red-probe.swap
elif [[ "$mode" =~ ^[4-8]$ ]]; then
  swap_gib="$mode"
  swap_name=andarium-red-build.swap
else
  echo 'ERROR: use --probe or 4-8 GiB additional swap' >&2
  exit 2
fi
base=/mnt
[[ -d "$base" ]] || { echo 'ERROR: /mnt unavailable' >&2; exit 1; }
path="$base/$swap_name"
[[ ! -e "$path" && ! -L "$path" ]] || {
  echo 'ERROR: refusing to replace a preexisting swap file' >&2
  exit 1
}
available_kib="$(df -Pk "$base" | awk 'END{print $4}')"
required_kib=$(( (swap_gib + 8) * 1024 * 1024 ))
if [[ ! "$available_kib" =~ ^[0-9]+$ ]] || (( available_kib < required_kib )); then
  echo "ERROR: additional swap would leave less than 8 GiB host disk reserve" >&2
  exit 1
fi
echo "HOST_SWAP_BEFORE"; swapon --show || true
echo "HOST_DISK_BEFORE"; df -h "$base"
cleanup() {
  sudo swapoff "$path" >/dev/null 2>&1 || true
  sudo rm -f -- "$path"
}
if [[ "$mode" == --probe ]]; then trap cleanup EXIT INT TERM; fi
sudo fallocate -l "$swap_gib"G "$path"
sudo chmod 600 "$path"
sudo mkswap "$path" >/dev/null
if ! sudo swapon "$path"; then
  echo 'ERROR: swap activation failed; do not run memory-heavy Soong' >&2
  cleanup
  exit 1
fi
echo "ANDARIUM_EXTRA_SWAP_GIB=$swap_gib"
swapon --show
df -h "$base"
free -h
if [[ "$mode" == --probe ]]; then
  echo 'PASS: temporary 1 GiB host swap activation worked; removing probe file'
fi
