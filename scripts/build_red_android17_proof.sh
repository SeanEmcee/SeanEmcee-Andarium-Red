#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Build an actual Red Android 17 image from the reviewed LineageOS 24 sources.
# Requires a provisioned x86_64 Linux Android build host and a verified
# Kernarium ABI29 ARM64/4KiB kernel artifact produced on macOS.
# No fake target-files, implicit root, signing secrets, or release substitution.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: bash scripts/build_red_android17_proof.sh \
  /ABS/Kernarium /ABS/AOSP17 /ABS/KERNEL_ARTIFACT /ABS/PROOF_OUT BUILD_NUMBER \
  [--jobs N] [--diagnostic-userdebug]

AOSP17 must be a writable, case-sensitive x86_64 Linux Repo workspace.
The script prepares pinned LineageOS 24 Android 17 source, applies the
modified Red launcher/clipboard source, runs real Soong, assembles an
actual GPT system disk, and packages a verifiable UNSIGNED development proof.

--diagnostic-userdebug requests an AOSP test-key userdebug image with debug su.
It is NOT Magisk-managed root, not a signed release and not a production build.
The original user build remains the default. Never reuse output from another
build variant. All outputs must be on a sufficiently provisioned builder.
EOF
}
if (( $# < 5 )); then usage >&2; exit 2; fi
kernarium="$1"; aosp="$2"; artifact="$3"; proof="$4"; number="$5"
shift 5
jobs=4
diagnostic=0
while (( $# )); do
  case "$1" in
    --jobs)
      if (( $# < 2 )); then echo "ERROR: --jobs needs an integer" >&2; exit 2; fi
      jobs="$2"; shift 2 ;;
    --diagnostic-userdebug) diagnostic=1; shift ;;
    *) echo "ERROR: unrecognized option $1" >&2; usage >&2; exit 2 ;;
  esac
done
if [[ ! "$jobs" =~ ^[1-9][0-9]*$ || ! "$number" =~ ^[1-9][0-9]{0,9}$ ]]; then
  echo "ERROR: jobs and build number must be positive decimal integers" >&2
  exit 2
fi
if [[ "$(uname -s)" != Linux || "$(uname -m)" != x86_64 ]]; then
  echo "ERROR: Android 17 Soong requires an x86_64 Linux builder" >&2
  exit 1
fi
for location in "$kernarium" "$aosp" "$artifact" "$proof"; do
  if [[ "$location" != /* ]]; then
    echo "ERROR: all input/output paths must be absolute: $location" >&2
    exit 2
  fi
done
repo_source="$(cd "$(dirname "$0")/.." && pwd -P)"
kernarium="$(cd "$kernarium" && pwd -P)"
artifact="$(cd "$artifact" && pwd -P)"
if [[ "$(git -C "$kernarium" rev-parse HEAD)" != fbe12ee72d195f0241c4fc24090a98b259026604 ]]; then
  echo "ERROR: reviewed upstream Kernarium revision not checked out" >&2
  exit 1
fi
if [[ -e "$proof" || -L "$proof" ]]; then
  echo "ERROR: refusing to overwrite existing proof output: $proof" >&2
  exit 1
fi
for command in repo git python3 zip unzip java javac; do
  command -v "$command" >/dev/null || {
    echo "ERROR: missing Android build tool: $command" >&2; exit 1;
  }
done
git lfs version >/dev/null || { echo "ERROR: git-lfs unavailable" >&2; exit 1; }
if [[ ! -d "$aosp" ]]; then
  echo "ERROR: create an adequately sized Linux AOSP workspace first: $aosp" >&2
  exit 1
fi
aosp="$(cd "$aosp" && pwd -P)"
# The binary must be for the tracked Android tree, bridge ABI and page size.
common="$kernarium/kernel/common"
python3 -B "$common/artifacts/verify-kernel-artifact.py" \
  --artifact "$artifact" --common-root "$common" \
  --kernel-metadata "$kernarium/kernel/mainline-6.18/patches/metadata.env" \
  --abi-metadata "$common/abi/identity.env"
python3 -B "$common/artifacts/verify-kernel-artifact.py" \
  --artifact "$artifact" --common-root "$common" \
  --abi-metadata "$common/abi/identity.env" \
  --compatible --expected-family android-6.18 \
  --expected-slice arm64 --expected-release-series 6.18 \
  --descriptor "$kernarium/kernel/mainline-6.18/artifacts/accepted-android-4k.env"

# Both integration preflights must pass before modifying the source checkout.
variant_args=()
if (( diagnostic )); then variant_args=(--diagnostic-userdebug); fi
python3 -B "$repo_source/integrate_andarium.py" \
  --kernarium "$kernarium" --source "$repo_source" "${variant_args[@]}" --dry-run
python3 -B "$repo_source/integrate_andarium.py" \
  --kernarium "$kernarium" --source "$repo_source" "${variant_args[@]}"

# The vendor's preparer requires an initialized Repo workspace; initialize
# only its pinned, reviewed public LineageOS manifest if absent.
if [[ ! -d "$aosp/.repo" ]]; then
  (
    cd "$aosp"
    repo init -u https://github.com/LineageOS/android.git \
      -b b51a0c449a3279ca55fb6d4d91d2143e42e2fff5 \
      --manifest-depth=1 --git-lfs --partial-clone --clone-filter=blob:none \
      --repo-rev=stable --no-repo-verify --no-clone-bundle
  )
fi

cd "$kernarium"
android/lineage-24/build/prepare-sources.sh --aosp-source "$aosp" --jobs "$jobs"
android/lineage-24/build/apply-aosp-patches.sh --aosp-source "$aosp"

variant=user
if (( diagnostic )); then variant=userdebug; fi
out="$aosp/out/andarium-red-$variant"
android/lineage-24/build/build-aosp.sh \
  --aosp-source "$aosp" --out "$out" --kernel-artifact "$artifact" \
  --build-number "$number" --jobs "$jobs"

# The reviewed Soong producer emits one canonical target-files archive.
# Never accept stale or differently named output via a wildcard search.
target="$out/target/product/lineage_andarium/obj/PACKAGING/target_files_intermediates/lineage_andarium-target_files.zip"
if [[ ! -f "$target" || -L "$target" ]]; then
  echo "ERROR: pinned Android17 product did not produce $target" >&2
  exit 1
fi
target_dir="${target%.zip}"
if [[ ! -d "$target_dir" || -L "$target_dir" ]]; then
  echo "ERROR: target-files IMAGES staging directory missing: $target_dir" >&2
  exit 1
fi
if (( diagnostic )); then
  # Only an actual target-files su payload can support diagnostic guest root.
  # This check does not claim a working su permission or Magisk daemon.
  if ! unzip -Z1 "$target" | grep -Eq '^SYSTEM/(system/)?(xbin|bin)/su$'; then
    echo "ERROR: userdebug target files contain no su binary" >&2
    exit 1
  fi
  echo "DIAGNOSTIC_BUILD_CONTAINS_SU_BINARY (not boot-tested, not Magisk)"
fi
host_tools="$out/host/linux-x86/bin"
for bin in mkbootfs mkbootimg; do
  if [[ ! -x "$host_tools/$bin" ]]; then
    echo "ERROR: compiled Android host tool missing: $host_tools/$bin" >&2
    exit 1
  fi
done
disk_dir="$(dirname "$proof")/andarium-red-disk-$number-$variant"
if [[ -e "$disk_dir" ]]; then
  echo "ERROR: refusing to overwrite assembled disk: $disk_dir" >&2
  exit 1
fi
android/lineage-24/build/assemble-image.sh \
  --target-files "$target" --kernel-artifact "$artifact" \
  --mkbootfs "$host_tools/mkbootfs" --mkbootimg "$host_tools/mkbootimg" \
  --output-dir "$disk_dir"

python3 -B "$repo_source/tools/create_unsigned_proof.py" \
  --kernarium "$kernarium" --target-files "$target" \
  --disk-dir "$disk_dir" \
  --kernel-cmdline "$kernarium/android/lineage-24/support/boot/kernel-command-line.txt" \
  --output "$proof" --release-name "red-v17-$number-$variant"
python3 -B "$repo_source/scripts/verify_red_android17_guest.py" \
  --proof "$proof" --kernarium "$kernarium"
echo "COMPILED_RED_ANDROID17_UNSIGNED_PROOF=$proof"
echo "ROOT_STATUS=unverified_on_device; userdebug diagnostic su is not Magisk"
echo "LIVE_CONTAINER_STATUS=requires_an_actual_iPhone_test"
