#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Reproduce the pinned Android 17 ARM64/4KiB Darwin UML kernel artifact.
# Never substitute an older bridge ABI, fabricate a manifest, or bypass checks.
set -euo pipefail

if (( $# != 1 )); then
  echo "Usage: bash scripts/prepare_kernarium_4k_kernel.sh KERNARIUM_PATH" >&2
  exit 2
fi
kernarium="$(cd "$1" && pwd -P)"
expected_revision=fbe12ee72d195f0241c4fc24090a98b259026604
if [[ "$(git -C "$kernarium" rev-parse HEAD)" != "$expected_revision" ]]; then
  echo "ERROR: kernel build refuses a Kernarium revision other than $expected_revision" >&2
  exit 1
fi
if [[ "$(uname -s)" != Darwin || "$(uname -m)" != arm64 ]]; then
  echo "ERROR: this Darwin UML ARM64 kernel must be built on an ARM64 Mac" >&2
  exit 1
fi

line="$kernarium/kernel/mainline-6.18"
common="$kernarium/kernel/common"
descriptor="$line/artifacts/accepted-android-4k.env"
read_descriptor() {
  local key="$1"
  sed -n "s/^$key='\([^']*\)'$/\1/p" "$descriptor"
}
release_id="$(read_descriptor UML_KERNEL_ARTIFACT_RELEASE_ID)"
directory="$(read_descriptor UML_KERNEL_ARTIFACT_DIRECTORY_NAME)"
if [[ ! "$release_id" =~ ^[A-Za-z0-9._-]+$ || ! "$directory" =~ ^android-6\.18-arm64-4k-[A-Za-z0-9._-]+$ ]]; then
  echo "ERROR: unsafe or missing accepted kernel release identity" >&2
  exit 1
fi
artifact="$kernarium/.build/kernel/artifacts/$directory"
verify() {
  python3 -B "$common/artifacts/verify-kernel-artifact.py" \
    --artifact "$artifact" --common-root "$common" \
    --abi-metadata "$common/abi/identity.env" \
    --compatible --expected-family android-6.18 \
    --expected-slice arm64 --expected-release-series 6.18 \
    --descriptor "$descriptor"
}
if [[ -d "$artifact" ]]; then
  verify
  echo "Reusing verified accepted Android 17 4 KiB artifact at $artifact"
  exit 0
fi

# The native dependency step supplies pinned build inputs and a Meson venv.
venv="$kernarium/.build/gpu-tools-venv/bin/activate"
if [[ ! -f "$venv" ]]; then
  echo "ERROR: build-tool virtualenv missing; run native dependencies first" >&2
  exit 1
fi
# shellcheck source=/dev/null
source "$venv"
# Homebrew LLVM 23 ships lld separately; selecting LLVM's removed ld.lld
# path is a deterministic failure on the Xcode 27 Golden Gate runner.
brew install llvm lld make
llvm="$(brew --prefix llvm)/bin"
lld="$(brew --prefix lld)/bin"
gmake="$(brew --prefix make)/bin/gmake"
for tool in "$llvm/clang" "$lld/ld.lld" "$llvm/llvm-objcopy" "$gmake"; do
  [[ -x "$tool" ]] || { echo "ERROR: kernel tool unavailable: $tool" >&2; exit 1; }
done
export PATH="$lld:$llvm:$(brew --prefix bison)/bin:$(brew --prefix flex)/bin:$PATH"
export UML_KERNEL_CC="$llvm/clang"
export UML_KERNEL_HOST_CC="$llvm/clang"
export UML_KERNEL_LD="$lld/ld.lld"
export UML_KERNEL_MAKE="$gmake"
export UML_KERNEL_JOBS=4
export UML_KERNEL_HOST_TOOLS_JOBS=4

# GitHub's macOS workspace may be case insensitive. Use a real
# case-sensitive APFS disk image for the upstream Linux kernel source.
# macOS 27's hdiutil accepts the documented 'Case-sensitive APFS' filesystem
# name, not the older APFSX alias. Do not suppress hdiutil diagnostics.
image="$kernarium/.build/ci-kernel-source.sparseimage"
mount="$kernarium/.build/ci-kernel-source"
mkdir -p "$mount"
echo "KERNEL_VOLUME_STAGE: creating case-sensitive APFS sparse image"
if ! hdiutil create -size 35g -type SPARSE -fs 'Case-sensitive APFS' \
    -volname AndariumRedKernel "$image"; then
  echo "ERROR: failed creating case-sensitive APFS disk image (see hdiutil output above)" >&2
  exit 1
fi
attached=0
cleanup() {
  if (( attached )); then
    hdiutil detach "$mount" || echo "WARNING: temporary kernel source volume did not detach" >&2
  fi
}
trap cleanup EXIT
echo "KERNEL_VOLUME_STAGE: mounting case-sensitive APFS image"
if ! hdiutil attach -nobrowse -mountpoint "$mount" "$image"; then
  echo "ERROR: failed attaching case-sensitive APFS image (see hdiutil output above)" >&2
  exit 1
fi
attached=1
echo "KERNEL_VOLUME_STAGE: verifying filesystem is case sensitive"
testfile="$mount/.andarium-red-caseprobe"
printf '%s\n' "probe" > "$testfile"
if [[ -e "$mount/.ANDARIUM-RED-CASEPROBE" ]]; then
  rm -f "$testfile"
  echo "ERROR: kernel source mount is not case sensitive" >&2
  exit 1
fi
rm -f "$testfile"
printf 'UML_KERNEL_SOURCE_DIR=%s/linux\n' "$mount" > "$line/source-location.conf"
echo "KERNEL_VOLUME_STAGE: filesystem verified; preparing Linux source"

# Fetch the exact upstream stable revision and replay only the pinned
# Kernarium patches; the canonical final source tree is verified twice.
export GIT_COMMITTER_NAME='Andarium Red Kernel CI'
export GIT_COMMITTER_EMAIL='andarium-red-kernel-ci@users.noreply.github.com'
cd "$kernarium"
"$line/scripts/prepare-source.sh" --slice arm64
"$line/scripts/prepare-source.sh" --slice arm64 --verify

# Real BTF needs authenticated, pinned pahole and static libelf.
dependencies/prepare.sh --product kernel-host-tools
dependencies/prepare.sh --archive-manifest dependencies/kernel-host-tools/archives.tsv
dependencies/build-kernel-host-tools.sh --jobs 4
dependencies/build-kernel-host-tools.sh --verify-only

source_dir="$mount/linux"
build_dir="$kernarium/.build/kernel-build/android-arm64"
"$line/build/build-kernel.sh" --product android --slice arm64 \
  --build "$build_dir" --jobs 4

# Upstream publisher checks source identity, Android config, ELF geometry,
# DWARF/BTF, 4KiB memory layout and bridge imports before publication.
python3 -B "$line/build/publish-artifact.py" \
  --source "$source_dir" --build "$build_dir" --slice arm64 \
  --product android --output-root "$kernarium/.build/kernel/artifacts" \
  --release-id "$release_id" --objcopy "$llvm/llvm-objcopy"
verify
test -f "$artifact/kernel/vmlinux"
echo "VERIFIED_PINNED_ANDROID17_ARM64_4K_KERNEL_ARTIFACT=$artifact"
