#!/usr/bin/env bash
# Free GitHub self-hosted Ubuntu x86_64 build with persistent AOSP and Ninja.
set -euo pipefail
case "$1" in preflight|prepare|compile|verify) mode="$1";; *) echo "Usage: $0 preflight|prepare|compile|verify" >&2; exit 2;; esac
repo_source="$(cd "$(dirname "$0")/.." && pwd -P)"
root="$HOME/andarium-red-persistent"
source_root="$root/aosp17"
kernarium="$root/Kernarium"
kernel_name=android-6.18-arm64-4k-20261119-6.18.60-ca1
kernel="$root/.build/$kernel_name"
checkpoint="$source_root/.andarium-red-source-checkpoint.json"
proof="$root/outputs/red-proof-1001-userdebug"
revision="$(git -C "$repo_source" rev-parse HEAD)"
[[ "$(uname -s)" == Linux && "$(uname -m)" == x86_64 && "$(id -u)" != 0 ]] || {
 echo "ERROR: use a non-root Linux x86_64 host, e.g. Ubuntu in WSL2" >&2; exit 2;
}
if [[ "${GITHUB_ACTIONS:-}" == true && "${RUNNER_ENVIRONMENT:-}" != self-hosted ]]; then
 echo "ERROR: this build requires persistent self-hosted Linux, not an ephemeral runner" >&2; exit 2;
fi
mkdir -p "$root"
root="$(cd "$root" && pwd -P)"
case "$root/" in /mnt/*|/media/*) echo "ERROR: Windows-mounted filesystem not supported" >&2; exit 2;; esac
preflight() {
 for tool in git repo python3 zip unzip java javac jq flock; do
   command -v "$tool" >/dev/null || { echo "ERROR: missing $tool" >&2; return 2; }
 done
 git lfs version >/dev/null
 case "$(stat -f -c %T "$root")" in 9p|fuseblk|drvfs)
   echo "ERROR: AOSP needs a native, case-sensitive Linux filesystem" >&2; return 2;;
 esac
 local tmp free_kib required
 tmp="$(mktemp -d "$root/.andarium-check-XXXXXX")"
 touch "$tmp/Case" "$tmp/case"
 [[ "$(find "$tmp" -mindepth 1 -maxdepth 1 -type f | wc -l)" == 2 ]] || {
   rm -rf "$tmp"; echo "ERROR: filesystem is not case-sensitive" >&2; return 2;
 }
 rm -rf "$tmp"
 free_kib="$(df -Pk "$root" | awk 'END {print $4}')"
 required=314572800
 [[ -e "$checkpoint" ]] && required=83886080
 [[ "$free_kib" =~ ^[0-9]+$ && "$free_kib" -ge "$required" ]] || {
   echo "ERROR: insufficient storage. Fresh source needs 300 GiB free; resume needs 80 GiB. Google recommends 400 GB." >&2
   df -h "$root"; return 2;
 }
 local ram
 ram="$(awk '/MemTotal:/ {print $2}' /proc/meminfo)"
 (( ram >= 16*1024*1024 )) || { echo "ERROR: less than 16 GiB RAM available" >&2; return 2; }
 (( ram >= 64*1024*1024 )) || echo "WARNING: below Google's recommended 64 GiB physical RAM"
 echo "ANDARIUM_PERSISTENT_HOST_PREFLIGHT_PASS"
 df -h "$root"
}
configure_git() {
 mkdir -p "$root/.build" "$root/logs"
 export GIT_CONFIG_NOSYSTEM=1
 export GIT_CONFIG_GLOBAL="$root/.build/ci-gitconfig"
 git config --file "$GIT_CONFIG_GLOBAL" user.name "Andarium Red CI"
 git config --file "$GIT_CONFIG_GLOBAL" user.email "andarium-red-ci@localhost.invalid"
 export GIT_TERMINAL_PROMPT=0
}
ensure_cached_inputs() {
 if [[ ! -e "$kernarium" ]]; then
   git clone --filter=blob:none --no-checkout https://github.com/imxieyi/Kernarium.git "$kernarium"
   git -C "$kernarium" checkout --detach fbe12ee72d195f0241c4fc24090a98b259026604
 fi
 [[ -d "$kernarium/.git" ]] || { echo "ERROR: pinned Kernarium not found" >&2; return 2; }
 [[ "$(git -C "$kernarium" rev-parse HEAD)" == fbe12ee72d195f0241c4fc24090a98b259026604 ]] || {
   echo "ERROR: cached Kernarium does not match the immutable source pin" >&2; return 2;
 }
 mkdir -p "$root/.build"
 if [[ ! -d "$kernel" ]]; then
   [[ ! -e "$kernel" ]] || { echo "ERROR: unexpected kernel cache path" >&2; return 2; }
   (cd "$root" && python3 "$repo_source/scripts/download_verified_kernel_circleci.py")
 fi
 echo "ANDARIUM_VERIFIED_KERNEL_AND_KERNARIUM_CACHE_READY"
}
check_source() {
 python3 -B - "$checkpoint" "$revision" <<'PY'
import json,sys
from pathlib import Path
f=Path(sys.argv[1])
assert f.is_file() and not f.is_symlink(), "source checkpoint absent"
d=json.loads(f.read_text())
expected={"schema":1,"red_revision":sys.argv[2],"build_number":"1001","diagnostic_userdebug":True,
          "kernarium":"fbe12ee72d195f0241c4fc24090a98b259026604"}
assert d==expected, "prepared source belongs to another SHA or variant; do not mix revisions"
print("ANDARIUM_PERSISTENT_PINNED_SOURCE_CHECKPOINT_VALID")
PY
}
if [[ "$mode" == preflight ]]; then preflight; exit 0; fi
exec 9>"$root/.andarium-build.lock"
flock -n 9 || { echo "ERROR: another persistent Android build is running" >&2; exit 2; }
case "$mode" in
 prepare)
   preflight
   configure_git
   ensure_cached_inputs
   mkdir -p "$source_root" "$root/outputs"
   if [[ -f "$checkpoint" ]]; then
     check_source
     echo "ANDARIUM_PINNED_AOSP_SOURCE_REUSED"
     exit 0
   fi
   bash "$repo_source/scripts/build_red_android17_proof.sh" \
     "$kernarium" "$source_root" "$kernel" "$proof" 1001 \
     --jobs 4 --diagnostic-userdebug --source-checkpoint-only
   check_source
   ;;
 compile)
   preflight
   configure_git
   ensure_cached_inputs
   check_source
   if [[ -d "$proof" ]]; then
     python3 -B "$repo_source/scripts/verify_red_android17_guest.py" --proof "$proof" --kernarium "$kernarium"
     echo "ANDARIUM_PREVIOUS_VERIFIED_PROOF_REUSED=$proof"
     exit 0
   fi
   echo "ANDARIUM_RESUMING_PERSISTENT_OUT=$source_root/out/andarium-red-userdebug"
   bash "$repo_source/scripts/build_red_android17_proof.sh" \
     "$kernarium" "$source_root" "$kernel" "$proof" 1001 \
     --jobs 2 --diagnostic-userdebug --use-prepared-source
   ;;
 verify)
   [[ -d "$proof" ]] || { echo "ERROR: no completed Android image proof exists" >&2; exit 2; }
   python3 -B "$repo_source/scripts/verify_red_android17_guest.py" --proof "$proof" --kernarium "$kernarium"
   ;;
esac
