#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Readiness checks against an ACTUALLY RUNNING Andarium Android 17 guest.

No device is attached in this development environment. Never treat local
source-overlay tests as equivalent to this live acceptance gate.
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import secrets
import subprocess
import time
from dataclasses import dataclass

AUTHORITY = 'content://dev.twoyi.redclipboard/clipboard'


@dataclass
class Result:
    name: str
    passed: bool
    detail: str


def adb_run(adb: str, *args: str, timeout: int = 20) -> str:
    try:
        p = subprocess.run([adb, 'shell', *args], stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, text=True, timeout=timeout)
    except OSError as error:
        raise RuntimeError('ADB executable unavailable or not runnable') from error
    if p.returncode != 0:
        raise RuntimeError(f'adb shell exit {p.returncode}: {p.stderr.strip()[:180]}')
    return p.stdout.strip()


# Android's content CLI prints exactly one Bundle. Substring extraction is
# unsafe: `not_status=ok` and duplicate fields must never pass a live test.
BUNDLE_RE = re.compile(r"^Result: Bundle\[\{([^{}\r\n]*)\}\]$")
BASE64_RE = re.compile(r"^[A-Za-z0-9_-]*$")
MAX_CLIPBOARD_BYTES = 32_768


def parse_bundle(key: str, response: str) -> str:
    match = BUNDLE_RE.fullmatch(response.strip())
    if not match:
        raise ValueError('Android clipboard response is not a single exact Bundle')
    fields = match.group(1).split(',')
    if len(fields) != 1 or fields[0].count('=') != 1:
        raise ValueError('Android clipboard returned unexpected or ambiguous fields')
    actual, value = (part.strip() for part in fields[0].split('=', 1))
    if actual != key or actual not in ('status', 'b64'):
        raise ValueError('Android clipboard returned the wrong Bundle field')
    if not value.isascii() or any(c.isspace() for c in value):
        raise ValueError('Android clipboard response has invalid token characters')
    if actual == 'b64' and value != '~':
        decode_clipboard_payload(value)
    elif actual == 'status' and value not in (
        'ok', 'not_ready', 'too_large', 'invalid_input', 'permission_denied', 'unknown_method'
    ):
        raise ValueError('Android clipboard response has unknown status')
    return value


def decode_clipboard_payload(value: str) -> str:
    # Don't allocate memory for arbitrary ADB shell output. Reject noncanonical
    # Base64 and malformed Unicode exactly as the Swift/Java endpoints do.
    if len(value) > (MAX_CLIPBOARD_BYTES + 2) // 3 * 4:
        raise ValueError('Android clipboard text exceeds 32 KiB')
    if not BASE64_RE.fullmatch(value) or len(value) % 4 == 1:
        raise ValueError('Android clipboard returned malformed Base64')
    try:
        data = base64.urlsafe_b64decode(value + '=' * (-len(value) % 4))
        canonical = base64.urlsafe_b64encode(data).decode('ascii').rstrip('=')
        if canonical != value or len(data) > MAX_CLIPBOARD_BYTES:
            raise ValueError('Android clipboard returned noncanonical or oversized Base64')
        return data.decode('utf-8', errors='strict')
    except (UnicodeError, base64.binascii.Error) as exc:
        raise ValueError('Android clipboard returned malformed UTF-8 or Base64') from exc


def read_clipboard_payload(adb: str) -> str:
    response = adb_run(adb, 'content', 'call', '--uri', AUTHORITY, '--method', 'read')
    if 'Result: Bundle[{status=' in response:
        status = parse_bundle('status', response)
        raise RuntimeError(f'Android clipboard read refused: {status}')
    return parse_bundle('b64', response)


def write_clipboard_payload(adb: str, payload: str) -> None:
    response = adb_run(adb, 'content', 'call', '--uri', AUTHORITY,
                       '--method', 'write', '--extra', f'b64:s:{payload}')
    status = parse_bundle('status', response)
    if status != 'ok':
        raise RuntimeError(f'Android clipboard write refused: {status}')


def check(name: str, fn) -> Result:
    try:
        detail = fn()
        return Result(name, True, str(detail))
    except Exception as exc:
        return Result(name, False, str(exc))


def require_property(adb: str, name: str, expected: str) -> str:
    actual = adb_run(adb, 'getprop', name)
    if actual != expected:
        raise AssertionError(f'{name} is {actual!r}, expected {expected!r}')
    return actual


def require_package(adb: str, package: str) -> str:
    found = adb_run(adb, 'pm', 'path', package)
    if not found.startswith('package:'):
        raise AssertionError(f'{package} not installed: {found[:100]!r}')
    return package


def require_nonempty(output: str) -> str:
    text = output.strip()
    if not text: raise AssertionError('Guest tool returned no output')
    return text


def require_substring(output: str, expected: str) -> str:
    if expected not in output:
        raise AssertionError(f'Expected Android component not registered: {expected}')
    return expected


def clipboard_privilege(adb: str) -> str:
    """Verify Android 17's signature-granted background clipboard capability.

    A manifest declaration alone does NOT establish this permission was granted.
    This is a precondition, not proof of a successful clipboard round-trip.
    """
    require_package(adb, 'dev.twoyi.redclipboard')
    report = adb_run(adb, 'dumpsys', 'package', 'dev.twoyi.redclipboard')
    import re
    if not re.search(r'(?m)^\s*android\.permission\.READ_CLIPBOARD_IN_BACKGROUND:\s*granted=true\b', report):
        raise AssertionError('Clipboard provider lacks Android signature permission READ_CLIPBOARD_IN_BACKGROUND')
    return 'Background clipboard permission granted to platform provider'


def active_heliboard(adb: str) -> str:
    require_package(adb, 'helium314.keyboard')
    active = adb_run(adb, 'settings', 'get', 'secure', 'default_input_method')
    if not active.startswith('helium314.keyboard/'):
        raise AssertionError('HeliBoard is not the active Android input method')
    return 'HeliBoard selected as current IME; typing still requires UI test'


def root_uid(adb: str) -> str:
    uid = adb_run(adb, 'su', '-c', 'id -u')
    if uid != '0':
        raise AssertionError('su did not grant guest UID 0')
    return 'Guest su returned UID 0 (not yet attributed to Magisk)'


def magisk_daemon(adb: str) -> str:
    # This reports daemon presence, not that every Magisk module works.
    response = adb_run(adb, 'sh', '-c', 'magisk --path')
    if not response or 'not found' in response.lower():
        raise AssertionError('Magisk daemon path not available')
    return 'Magisk daemon responds (separate from guest su test)'


def clipboard_roundtrip(adb: str) -> str:
    """Explicit opt-in roundtrip; never overwrite a concurrent clipboard edit.

    Android has no compare-and-swap clipboard API, so this is best-effort. We
    restore only if the test value is STILL present; unexpected newer content
    belongs to the user and is deliberately left untouched. No clipboard
    contents are logged or included in a report.
    """
    original = read_clipboard_payload(adb)
    if original == '~':
        raise AssertionError('Clipboard has no plain text; refusing destructive test')
    # Canonical Base64 and UTF-8 were already checked above.
    test_string = 'Android17 clipboard bridge test / ' + secrets.token_hex(12)
    encoded = base64.urlsafe_b64encode(test_string.encode()).rstrip(b'=').decode()
    # Refuse if a different application replaced the user's clipboard between
    # our initial snapshot and the write. This cannot make the race atomic.
    if read_clipboard_payload(adb) != original:
        raise RuntimeError('Clipboard changed before test; refusing to overwrite it')

    problem: Exception | None = None
    try:
        write_clipboard_payload(adb, encoded)
        if read_clipboard_payload(adb) != encoded:
            raise AssertionError('guest clipboard roundtrip mismatch')
    except Exception as error:
        problem = error

    # If somebody else copied text during the test, do NOT clobber it with
    # our saved copy. This safety check also handles an unacknowledged write.
    current = read_clipboard_payload(adb)
    if current == encoded:
        write_clipboard_payload(adb, original)
        if read_clipboard_payload(adb) != original:
            raise AssertionError('Clipboard restore did not preserve original text') from problem
    elif current != original:
        raise RuntimeError('Clipboard changed during test; preserving newer content') from problem
    if problem is not None:
        raise problem
    return 'Android provider roundtrip and original-text restore passed; iOS UI remains untested'


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--adb', default='adb', help='Executable with authorized connection to Android guest')
    ap.add_argument('--require-root', action='store_true', help='Require su to work inside Android guest')
    ap.add_argument('--require-appmanager', action='store_true', help='Also require the real App Manager package')
    ap.add_argument('--require-keyboard', action='store_true', help='Require installed and registered HeliBoard input method')
    ap.add_argument('--require-active-keyboard', action='store_true', help='Require HeliBoard to be selected as the current Android IME')
    ap.add_argument('--require-clipboard-privilege', action='store_true', help='Require platform granted background clipboard permission, not merely APK installation')
    ap.add_argument('--require-magisk-root', action='store_true', help='Explicitly request and test Magisk-managed root; may show a superuser prompt')
    ap.add_argument('--check-clipboard', action='store_true', help='Explicitly test Android text clipboard when original text can be restored and confirmed')
    ap.add_argument('--require-play-services', action='store_true', help='Require genuine installed Play Store, Google Play services and Services Framework (does not install them)')
    ap.add_argument('--output', default='', help='Optional JSON report path')
    args = ap.parse_args()
    started = time.monotonic()
    tests = [
        check('Android 17 version', lambda: require_property(args.adb, 'ro.build.version.release', '17')),
        check('Android fully booted', lambda: require_property(args.adb, 'sys.boot_completed', '1')),
        check('Red launcher installed', lambda: require_package(args.adb, 'dev.twoyi.redlauncher')),
        check('Magisk manager installed', lambda: require_package(args.adb, 'com.topjohnwu.magisk')),
        check('Titanium browser installed', lambda: require_package(args.adb, 'io.github.jqssun.helium')),
        check('Clipboard provider installed', lambda: require_package(args.adb, 'dev.twoyi.redclipboard')),
    ]
    if args.require_appmanager:
        tests.append(check('App Manager installed', lambda: require_package(args.adb, 'io.github.muntashirakon.AppManager')))
    if args.require_keyboard:
        tests.append(check('HeliBoard installed', lambda: require_package(args.adb, 'helium314.keyboard')))
        tests.append(check('HeliBoard input method registered', lambda: require_substring(
            adb_run(args.adb, 'ime', 'list', '-s'), 'helium314.keyboard')))
    if args.require_active_keyboard:
        tests.append(check('HeliBoard currently selected', lambda: active_heliboard(args.adb)))
    if args.require_clipboard_privilege:
        tests.append(check('Android clipboard signature permission granted', lambda: clipboard_privilege(args.adb)))
    if args.require_play_services:
        for package in ('com.android.vending', 'com.google.android.gms', 'com.google.android.gsf'):
            tests.append(check('Google component installed: ' + package,
                lambda package=package: require_package(args.adb, package)))
    if args.require_magisk_root:
        # Magisk can root a non-debuggable user image. ro.debuggable=0 is
        # neither proof nor disproof of Magisk root.
        tests.append(check('Magisk executable reports version', lambda: require_nonempty(
            adb_run(args.adb, 'sh', '-c', 'magisk -v'))))
    if args.require_root or args.require_magisk_root:
        tests.append(check('Guest su returns exact UID 0', lambda: root_uid(args.adb)))
    if args.require_magisk_root:
        tests.append(check('Magisk daemon responds', lambda: magisk_daemon(args.adb)))
    if args.check_clipboard:
        tests.append(check('Android clipboard provider roundtrip', lambda: clipboard_roundtrip(args.adb)))
    out = {'product':'Andarium Red Android17',
           'requested_checks_passed':all(t.passed for t in tests),
           'checks':[vars(t) for t in tests],
           'elapsed_check_seconds':round(time.monotonic()-started, 2),
           'caveat':'These checks do not validate iPhone launch time or iOS UI. Magisk-managed root is not certified unless --require-magisk-root is used and passes on a live guest.'}
    print(json.dumps(out,indent=2))
    if args.output:
        from pathlib import Path
        Path(args.output).write_text(json.dumps(out,indent=2)+'\n')
    return 0 if out['requested_checks_passed'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
