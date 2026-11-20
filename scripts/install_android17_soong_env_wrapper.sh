#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Guarded system env wrapper on a disposable GitHub Ubuntu x86_64 host only.
set -eo pipefail
if [[ "$GITHUB_ACTIONS" != true || "$RUNNER_OS" != Linux ||
      "$RUNNER_ENVIRONMENT" != github-hosted || "$(uname -m)" != x86_64 ]]; then
  echo "ERROR: refusing to replace env outside GitHub-hosted Linux x86_64" >&2
  exit 2
fi
self="$(cd "$(dirname "$0")" && pwd -P)"
target=/usr/bin/env
original=/usr/bin/env.andarium-original
case "$1" in
  --install)
    [[ -f "$target" && ! -L "$target" && -x "$target" &&
       ! -e "$original" && ! -L "$original" ]] || {
      echo 'ERROR: unexpected env utility state, refusing modification' >&2
      exit 2
    }
    sudo cp -p "$target" "$original"
    sudo install -m 0755 "$self/android17_soong_env_wrapper" /usr/bin/env.andarium-new
    sudo mv -f /usr/bin/env.andarium-new "$target"
    echo "ANDARIUM_SOONG_ENV_BRIDGE_INSTALLED"
    ;;
  --restore)
    if [[ -f "$original" && ! -L "$original" ]]; then
      sudo mv -f "$original" "$target"
      echo "ANDARIUM_SOONG_ENV_BRIDGE_RESTORED"
    else
      echo 'ERROR: refusing to restore an absent original env utility' >&2
      exit 2
    fi
    ;;
  *)
    echo 'Usage: bash scripts/install_android17_soong_env_wrapper.sh --install|--restore' >&2
    exit 2
    ;;
esac
