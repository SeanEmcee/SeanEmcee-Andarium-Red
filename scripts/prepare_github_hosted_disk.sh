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
# Remove optional globally installed SDKs and language package caches.
# The pinned Android builder uses its checked-in toolchains, OpenJDK 17 and
# Ubuntu's /usr/bin/python3, not the GitHub image's hosted extras.
optional_paths=(
  /usr/local/go
  /usr/local/lib/node_modules
  /usr/local/lib/python3.11/site-packages
  /usr/local/lib/python3.12/site-packages
  /usr/local/lib/python3.13/site-packages
  /usr/local/lib/python3.11/dist-packages
  /usr/local/lib/python3.12/dist-packages
  /usr/local/lib/python3.13/dist-packages
  /opt/pipx
  /opt/google
)
for path in "${optional_paths[@]}"; do
  if [[ -d "$path" && ! -L "$path" ]]; then
    du -sh "$path" || true
    sudo rm -rf -- "$path"
  fi
done
# Free GitHub-hosted images carry per-user toolchains and language caches.
# They are unnecessary for the Android pinned-source builder, which downloads
# its own source/toolchains. Remove only known optional paths on the disposable VM;
# leave apt's JDK, Git, Python stdlib, /usr/bin, and /usr/lib intact.
cache_paths=(
  /home/runner/.rustup
  /home/runner/.cargo
  /home/runner/.cache
  /home/runner/.npm
  /home/runner/.local/share/pnpm
  /home/runner/.local/share/JetBrains
  /usr/local/.rustup
  /usr/local/.cargo
  /usr/share/gradle
  /opt/gradle
  /opt/apache-maven
  /usr/share/maven
  /usr/share/scala
  /usr/share/kotlin
  /usr/local/share/jupyter
)
for path in "${cache_paths[@]}"; do
  if [[ -d "$path" && ! -L "$path" ]]; then
    du -sh "$path" || true
    sudo rm -rf -- "$path"
  fi
done
# Docker image layers are unrelated to the in-tree Soong producer. Use Docker's
# own cleanup API, never delete /var/lib/docker while dockerd is running.
if command -v docker >/dev/null 2>&1; then
  timeout 120 sudo docker system prune --all --force --volumes || true
fi
sudo apt-get clean
# Verify the remaining host still has the Unix and Python tools our scripts use.
for cmd in git python3 bash df awk tar; do
  command -v "$cmd" >/dev/null || { echo "ERROR: required tool lost in cleanup: $cmd" >&2; exit 1; }
done
python3 -c 'import os,hashlib,tarfile,subprocess,urllib.request' || {
  echo 'ERROR: necessary Python standard library unavailable after cleanup' >&2; exit 1;
}
echo 'AFTER'; df -h /
# If the minimum still isn't met, print the largest *top-level* remaining
# directories to identify precise, safe candidates rather than guessing.
available_now="$(df -Pk / | awk 'END{print $4}')"
if [[ "$available_now" =~ ^[0-9]+$ ]] && (( available_now < 127926272 )); then
  for directory in /opt /usr/local /var /home/runner; do
    echo "REMAINING_DISK_USAGE_TOP_LEVEL=$directory"
    timeout 60 sudo du -x -h --max-depth=1 "$directory" 2>/dev/null | sort -h | tail -n 18 || true
  done
fi
free_kib="$(df -Pk / | awk 'END{print $4}')"
echo "RECLAIMED_RUNNER_AVAILABLE_KIB=$free_kib"
if (( free_kib >= 127926272 )); then
  echo 'BTRFS_COMPRESSED_AOSP_WORKSPACE_CAN_BE_ATTEMPTED'
else
  echo 'BTRFS_COMPRESSED_AOSP_WORKSPACE_NOT_YET_FEASIBLE'
fi
