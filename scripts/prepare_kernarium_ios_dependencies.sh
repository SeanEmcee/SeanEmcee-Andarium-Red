#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Build Kernarium's pinned iOS GPU, networking, storage and zstd dependency
# prefixes from its authenticated upstream source manifest. No fake libraries.
set -euo pipefail
if (( $# != 1 )); then
  echo "Usage: bash scripts/prepare_kernarium_ios_dependencies.sh KERNARIUM_PATH" >&2
  exit 2
fi
source_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
checkout="$(cd "$1" && pwd)"
test -f "$checkout/dependencies/manifest.tsv"
test -f "$checkout/dependencies/build-apple-gpu.sh"
test "$(uname -s)" = Darwin
cd "$checkout"

echo "Checking the exact Mesa ARM64/iOS cross-target architecture flags ..."
python3 "$source_root/scripts/patch_kernarium_mesa_cross_endian.py" "$checkout"

echo "Installing macOS build tools for pinned third-party dependencies ..."
brew install ninja bison flex pkgconf autoconf automake libtool gettext gperf rsync
python3 -m venv .build/gpu-tools-venv
. .build/gpu-tools-venv/bin/activate
python -m pip install --disable-pip-version-check --upgrade pip
python -m pip install --disable-pip-version-check 'meson>=1.4,<2' mako packaging PyYAML

export PATH="$(brew --prefix bison)/bin:$(brew --prefix flex)/bin:$(brew --prefix gettext)/bin:$PATH"
# Upstream's Mesa builder deliberately invokes env -i with a narrow PATH:
# Python venv bin + Meson bin + Ninja bin + system tools. On macOS,
# /usr/bin/bison is ancient and cannot parse the pinned Mesa grammar.
# Place the real Homebrew executables inside that existing trusted venv/bin,
# not fake generated C or patched third-party parser sources.
ln -sfn "$(brew --prefix bison)/bin/bison" .build/gpu-tools-venv/bin/bison
ln -sfn "$(brew --prefix flex)/bin/flex" .build/gpu-tools-venv/bin/flex
(
  env -i PATH="$PWD/.build/gpu-tools-venv/bin:/usr/bin:/bin" bison --version
  env -i PATH="$PWD/.build/gpu-tools-venv/bin:/usr/bin:/bin" flex --version
)
export UML_APPLE_GPU_DEPENDENCY_JOBS=4
export UML_IOS_NETWORK_DEPENDENCY_JOBS=4
export UML_IOS_STORAGE_DEPENDENCY_JOBS=4
export UML_IOS_ZSTD_DEPENDENCY_JOBS=4

echo "Fetching only exact upstream dependency revisions ..."
for product in apple-gpu-vulkan-experiment ios-network ios-storage ios-compression; do
  dependencies/prepare.sh --product "$product"
done

echo "Building the pinned, actual iOS device dependency prefixes ..."
dependencies/build-apple-gpu.sh --platform ios --jobs 4
dependencies/build-ios-network.sh --platform ios
dependencies/build-ios-storage.sh
dependencies/build-ios-zstd.sh

echo "Verifying built GPU prefix with Kernarium's own contract ..."
dependencies/build-apple-gpu.sh --platform ios --verify-only
echo "Andarium iOS native dependency preparation complete."
