#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Experimental source workspace compression for CircleCI's 150 GB Linux VM.
# Does not change the pinned manifest, source revisions or Android verification.
set -euo pipefail

workspace="${1:?usage: $0 /ABS/AOSP_WORKSPACE}"
[[ "$workspace" = /* ]] || { echo 'ERROR: workspace path must be absolute' >&2; exit 2; }
[[ "$(uname -s)" = Linux && "$(uname -m)" = x86_64 ]] || {
  echo 'ERROR: compressed workspace requires Linux x86_64' >&2; exit 1;
}
[[ ! -e "$workspace/.repo" ]] || {
  echo 'ERROR: refusing to cover an initialized Android Repo workspace' >&2; exit 1;
}
command -v mkfs.btrfs >/dev/null || { echo 'ERROR: install btrfs-progs first' >&2; exit 1; }
command -v fallocate >/dev/null || exit 1
command -v mountpoint >/dev/null || exit 1

# Fully allocated image prevents the backing filesystem running out of space
# underneath a larger sparse loop device (potential Btrfs metadata corruption).
# Default reserve 18 GiB for host files, tools and proof artifacts.
# On a disposable GitHub-hosted runner, 16 GiB may be explicitly selected.
# Never accept less than 16 GiB or a fractional/malformed override.
backing="${ANDARIUM_COMPRESSED_IMAGE:-$HOME/andarium-red-aosp17-compressed.btrfs}"
[[ "$backing" = /* ]] || { echo 'ERROR: backing image must be an absolute path' >&2; exit 2; }
[[ ! -e "$backing" && ! -L "$backing" ]] || {
  echo 'ERROR: refusing to overwrite an existing compressed workspace image' >&2; exit 1;
}
mkdir -p "$workspace"
mountpoint -q "$workspace" && { echo 'ERROR: workspace is already a mount point' >&2; exit 1; }

available_kib="$(df -Pk "$(dirname "$backing")" | awk 'END{print $4}')"
[[ "$available_kib" =~ ^[0-9]+$ ]] || exit 1
reserve_gib="${ANDARIUM_COMPRESSED_HOST_RESERVE_GIB:-18}"
if [[ ! "$reserve_gib" =~ ^(1[6-9]|2[0-9]|3[0-2])$ ]]; then
  echo 'ERROR: host disk reserve must be a whole 16–32 GiB' >&2
  exit 2
fi
reserve_kib=$((reserve_gib * 1024 * 1024))
echo "ANDARIUM_COMPRESSED_HOST_RESERVE_GIB=$reserve_gib"
min_image_kib=$((104 * 1024 * 1024))
if ((available_kib < min_image_kib + reserve_kib)); then
  echo "ERROR: requires at least $((min_image_kib / 1024 / 1024)) GiB for image and $((reserve_kib / 1024 / 1024)) GiB host reserve, has $((available_kib / 1024 / 1024)) GiB" >&2
  exit 1
fi
image_kib=$((available_kib - reserve_kib))
max_image_kib=$((115 * 1024 * 1024))
((image_kib <= max_image_kib)) || image_kib="$max_image_kib"
echo "ANDARIUM_COMPRESSED_SOURCE_WORKSPACE_GIB=$((image_kib / 1024 / 1024))"
echo 'Filesystem: Btrfs zstd:3, pinned source and kernel verification unchanged'
fallocate -l "${image_kib}K" "$backing"
mkfs.btrfs -f -L andarium-red-aosp17 "$backing"
sudo mount -t btrfs -o loop,noatime,compress=zstd:3 "$backing" "$workspace"
sudo chown "$(id -u):$(id -g)" "$workspace"
mountpoint -q "$workspace" || { echo 'ERROR: AOSP workspace was not mounted' >&2; exit 1; }
test "$(stat -f -c %T "$workspace")" = btrfs || {
  echo 'ERROR: mounted AOSP filesystem is not Btrfs' >&2; exit 1;
}
mount | grep -F " on $workspace " || exit 1
df -h "$workspace" "$(dirname "$backing")"
