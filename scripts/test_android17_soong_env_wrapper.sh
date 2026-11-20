#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
set -euo pipefail
test -x /usr/bin/env.andarium-original
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/out/andarium-red-userdebug/host/linux-x86/bin"
cat > "$tmp/out/andarium-red-userdebug/host/linux-x86/bin/soong_build" <<'SH'
#!/bin/sh
test "$GOMEMLIMIT" = 8GiB
test "$GOGC" = 25
test "$GOMAXPROCS" = 2
test "$GODEBUG" = gctrace=1
echo "FAKE_SOONG_RECEIVED_MEMORY_CAP"
SH
chmod +x "$tmp/out/andarium-red-userdebug/host/linux-x86/bin/soong_build"
out="$(/usr/bin/env -i "$tmp/out/andarium-red-userdebug/host/linux-x86/bin/soong_build" --fake-check)"
test "$out" = FAKE_SOONG_RECEIVED_MEMORY_CAP
/usr/bin/env -i /bin/sh -c 'test -z "$GOMEMLIMIT"; test -z "$GOGC"'
/usr/bin/env TEST_UNRELATED_ENV=ok /bin/sh -c 'test "$TEST_UNRELATED_ENV" = ok'
echo 'PASS: exact Soong Go heap limit survives env -i; other env uses unchanged'
