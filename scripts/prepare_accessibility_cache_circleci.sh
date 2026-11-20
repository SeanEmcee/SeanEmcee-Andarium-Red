#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Cache exact accessibility checkouts, never unverified workspace state.
set -euo pipefail
if (( $# != 2 )); then echo "Usage: $0 /ABS/Kernarium /ABS/CACHE_DIR" >&2; exit 2; fi
kernarium="$1"; cache="$2"
[[ "$kernarium" = /* && "$cache" = /* ]] || exit 2
[[ "$(git -C "$kernarium" rev-parse HEAD)" = fbe12ee72d195f0241c4fc24090a98b259026604 ]] || {
 echo "Wrong pinned Kernarium revision" >&2; exit 1;
}
source "$kernarium/android/lineage-24/third_party/accessibility/metadata.env"
verifier="$kernarium/android/lineage-24/tools/verify-accessibility-source.py"
root="$cache/aosp"
if [[ -e "$cache" || -L "$cache" ]]; then
  [[ -d "$root/.repo" && ! -L "$cache" ]] || {
    echo "Refusing incomplete or symlink accessibility cache" >&2; exit 1;
  }
  python3 -B "$verifier" --android-root "$kernarium/android/lineage-24" --aosp-source "$root"
  echo "ANDARIUM_ACCESSIBILITY_CACHE_HIT_VERIFIED"
  exit 0
fi
mkdir -p "$root/.repo" "$root/external"
series_tree() { awk -F '\t' '$1 == "tree" { print $2 }' "$kernarium/$1/series.tsv"; }
pinned_checkout() {
  local label="$1" rel="$2" repository="$3" commit="$4" tree="$5" branch="$6" series="$7"
  local dest="$root/$rel" final_tree=""
  [[ ! -e "$dest" && ! -L "$dest" ]] || exit 1
  mkdir -p "$(dirname "$dest")"
  git init -q "$dest"
  git -C "$dest" remote add origin "$repository"
  git -C "$dest" fetch --no-tags --depth=1 origin "$commit"
  if [[ -n "$branch" ]]; then
    git -C "$dest" switch --create "$branch" "$commit"
  else
    git -C "$dest" checkout --detach "$commit"
  fi
  [[ "$(git -C "$dest" rev-parse HEAD^{tree})" = "$tree" ]] || {
    echo "Pinned $label upstream tree differs" >&2; exit 1;
  }
  if [[ -n "$series" ]]; then
    final_tree="$(series_tree "$series")"
    [[ -n "$final_tree" ]] || exit 1
    python3 -B "$kernarium/scripts/patch_series.py" apply \
       --repo "$dest" --series-dir "$kernarium/$series" --expect-tree "$final_tree"
  fi
}
pinned_checkout TalkBack "$TALKBACK_DESTINATION" "$TALKBACK_UPSTREAM_REPOSITORY" \
  "$TALKBACK_UPSTREAM_COMMIT" "$TALKBACK_UPSTREAM_TREE" "$TALKBACK_PATCH_BRANCH" "$TALKBACK_SERIES"
pinned_checkout 'eSpeak NG' "$ESPEAK_NG_DESTINATION" "$ESPEAK_NG_UPSTREAM_REPOSITORY" \
  "$ESPEAK_NG_UPSTREAM_COMMIT" "$ESPEAK_NG_UPSTREAM_TREE" "$ESPEAK_NG_PATCH_BRANCH" "$ESPEAK_NG_SERIES"
pinned_checkout libsonic "$SONIC_DESTINATION" "$SONIC_UPSTREAM_REPOSITORY" \
  "$SONIC_UPSTREAM_COMMIT" "$SONIC_UPSTREAM_TREE" "" ""
python3 -B "$verifier" --android-root "$kernarium/android/lineage-24" --aosp-source "$root"
echo "ANDARIUM_ACCESSIBILITY_CACHE_CREATED_VERIFIED"
du -sh "$cache"
