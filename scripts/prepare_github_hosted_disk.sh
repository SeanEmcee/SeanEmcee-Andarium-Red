#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Runs only inside a disposable GitHub-hosted Ubuntu VM. Removes preinstalled
# toolchains not needed for the pinned, in-tree Android 17 Soong source build.
set -euo pipefail
[[ "$GITHUB_ACTIONS" == true && "$RUNNER_OS" == Linux && "$(uname -m)" == x86_64 ]] || {
  echo 'ERROR: refusing cleanup outside an x86_64 Linux GitHub Actions job' >&2
  exit 2
}
paths=(
  /usr/local/lib/android
  /usr/share/dotnet
  /usr/local/share/powershell
  /opt/ghc
  /opt/hostedtoolcache
  /usr/share/swift
  /opt/az
  /usr/local/share/chromium
  /usr/local/share/boost
  /usr/local/share/vcpkg
)
echo 'Andarium GitHub free-runner disk reclamation; disposable VM only'
echo 'BEFORE'; df -h /
for path in "${paths[@]}"; do
  if [[ -e "$path" && -d "$path" && ! -L "$path" ]]; then
    du -sh "$path" || true
    sudo rm -rf -- "$path"
  fi
done
sudo apt-get clean
echo 'AFTER'; df -h /
free_kib="$(df -Pk / | awk 'END{print $4}')"
echo "RECLAIMED_RUNNER_AVAILABLE_KIB=$free_kib"
if (( free_kib >= 127926272 )); then
  echo 'BTRFS_COMPRESSED_AOSP_WORKSPACE_CAN_BE_ATTEMPTED'
else
  echo 'BTRFS_COMPRESSED_AOSP_WORKSPACE_NOT_YET_FEASIBLE'
fi
