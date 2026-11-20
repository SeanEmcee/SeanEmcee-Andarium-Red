#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Reuse authenticated, pinned kernel host-tool source and compiled tool prefixes.
# This stage can be cached before any expensive Android kernel compilation.
set -euo pipefail
if (( $# != 1 )); then
  echo "Usage: bash scripts/prepare_kernarium_kernel_host_tools.sh KERNARIUM_PATH" >&2
  exit 2
fi
kernarium="$(cd "$1" && pwd -P)"
source_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
[[ "$(git -C "$kernarium" rev-parse HEAD)" == "fbe12ee72d195f0241c4fc24090a98b259026604" ]] || {
  echo "ERROR: host-tool preparation requires pinned Kernarium checkout" >&2
  exit 1
}
cd "$kernarium"
if dependencies/prepare.sh --product kernel-host-tools --verify >/dev/null 2>&1; then
  echo "Reusing verified pinned kernel host-tool source checkouts"
else
# Real BTF needs authenticated, pinned pahole and static libelf. Fetch the
# actual upstream Git objects first. Savannah's HTTPS Git service can return
# intermittent 502s for gawk; retry that precise transient failure, then use
# a byte-identical pinned Git commit from a reviewed mirror as *transport*.
# Never change dependencies/manifest.tsv, its canonical repository identity,
# the pinned commit, patch replay, or Kernarium's source verifier.
host_prepare_log="$kernarium/.build/kernel-host-tools-source-prepare.log"
prepared=0
for attempt in 1 2; do
  if dependencies/prepare.sh --product kernel-host-tools >"$host_prepare_log" 2>&1; then
    prepared=1
    break
  fi
  if ! grep -Fq 'git.savannah.gnu.org/git/gawk.git' "$host_prepare_log" ||
     ! grep -Eq 'error: 50(2|3|4)' "$host_prepare_log"; then
    tail -n 80 "$host_prepare_log" >&2
    echo "ERROR: pinned host-tool source preparation failed for a reason other than the known Savannah outage" >&2
    exit 1
  fi
  echo "Gawk source fetch got a transient Savannah HTTP 50x; canonical retry $attempt/2"
  sleep 3
done
if (( ! prepared )); then
  echo "Canonical Gawk Git transport unavailable; seeding the identical pinned Git object from reviewed mirror"
  # The guarded seed owns no source identity and accepts only one hard-pinned
  # Gawk commit; the original prepare.sh still verifies it as usual.
  bash "$source_root/scripts/seed_pinned_gawk_git_cache.sh" "$kernarium"
  dependencies/prepare.sh --product kernel-host-tools
fi
dependencies/prepare.sh --product kernel-host-tools --verify
fi
# Never trust restored caches or mirrored transport without the same original
# Kernarium source, archive, and compiled-prefix verification.
dependencies/prepare.sh --product kernel-host-tools --verify
dependencies/prepare.sh --archive-manifest dependencies/kernel-host-tools/archives.tsv
dependencies/build-kernel-host-tools.sh --jobs 4
dependencies/build-kernel-host-tools.sh --verify-only
echo "VERIFIED_PINNED_KERNEL_HOST_TOOLS=$kernarium/.build/dependencies/kernel-host-tools"
