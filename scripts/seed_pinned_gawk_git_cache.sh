#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Work around a transient Savannah HTTPS outage without changing a single
# pinned source identity or Kernarium's provenance policy.
# Called only after the canonical Savannah fetch failed with HTTP 502/503/504.
set -euo pipefail
if (( $# != 1 )); then
  echo "Usage: bash scripts/seed_pinned_gawk_git_cache.sh KERNARIUM_PATH" >&2
  exit 2
fi
kernarium="$(cd "$1" && pwd -P)"
manifest="$kernarium/dependencies/manifest.tsv"
expected_repo='https://git.savannah.gnu.org/git/gawk.git'
expected_commit='52af7f12758da12db0ddbdb117a84e0685cd2f72'
# This GitHub mirror was checked to contain the identical full Git object.
# Fetching an identical 160-bit Git commit changes transport, not source.
mirror='https://github.com/GitMirroring/gawk.git'
read -r original pinned < <(
  awk -F '\t' '$1 == "gawk" { print $4, $5; count++ }
  END { if (count != 1) exit 1 }' "$manifest"
)
if [[ "$original" != "$expected_repo" || "$pinned" != "$expected_commit" ]]; then
  echo "ERROR: refuse Gawk transport fallback for an unexpected source pin" >&2
  exit 1
fi
cache_root="$kernarium/.build/dependency-cache/git"
destination="$cache_root/gawk"
mkdir -p "$cache_root"
if [[ -e "$destination" || -L "$destination" ]]; then
  # A preexisting object must be validated by Kernarium's own source loader.
  # Never overwrite potentially untrusted or concurrently produced caches.
  echo "ERROR: existing Gawk cache requires normal provenance inspection" >&2
  exit 1
fi
staging="$(mktemp -d "$cache_root/.gawk-pinned.XXXXXXXX")"
cleanup() { if [[ -d "$staging" ]]; then rm -rf -- "$staging"; fi; }
trap cleanup EXIT
git -C "$staging" init --quiet
git -C "$staging" remote add origin "$expected_repo"
git -C "$staging" -c protocol.version=2 fetch --no-tags --depth 1 \
  "$mirror" "$expected_commit"
actual="$(git -C "$staging" rev-parse 'FETCH_HEAD^{commit}')"
if [[ "$actual" != "$expected_commit" ]]; then
  echo "ERROR: mirror provided a different Git commit identity" >&2
  exit 1
fi
git -C "$staging" update-ref refs/heads/uml-pin "$expected_commit"
git -C "$staging" fsck --connectivity-only --no-reflogs
[[ "$(git -C "$staging" remote get-url origin)" == "$expected_repo" ]]
tree="$(git -C "$staging" rev-parse 'HEAD^{tree}' 2>/dev/null || git -C "$staging" rev-parse "$expected_commit^{tree}")"
echo "GAWK_FALLBACK_PINNED_COMMIT=$actual"
echo "GAWK_FALLBACK_PINNED_TREE=$tree"
echo "GAWK_FALLBACK_CANONICAL_REPOSITORY=$expected_repo"
mv -- "$staging" "$destination"
trap - EXIT
echo "Mirrored transport is staged; Kernarium must still independently verify every source and patch series."
