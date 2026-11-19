# SPDX-License-Identifier: GPL-2.0-or-later
"""Real acceptance-parser and clipboard-race regression tests (fake ADB only)."""
import base64
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import verify_guest as guest


def encoded(value):
    return base64.urlsafe_b64encode(value.encode('utf-8')).decode().rstrip('=')


class GuestResponseTests(unittest.TestCase):
    def test_exact_status(self):
        self.assertEqual('ok', guest.parse_bundle('status', 'Result: Bundle[{status=ok}]'))

    def test_rejects_ambiguous_and_spoofed_responses(self):
        for value in (
            'noise status=ok Result: Bundle[{status=ok}]',
            'Result: Bundle[{not_status=ok}]',
            'Result: Bundle[{status=ok, status=ok}]',
            'Result: Bundle[{b64=QQ, status=ok}]',
            'Result: Bundle[{status=ok}]\nResult: Bundle[{status=ok}]',
            'Result: Bundle[{status=ok,more=bad}]',
            'Result: Bundle[{status=ok\\n}]',
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                guest.parse_bundle('status', value)

    def test_rejects_malformed_and_noncanonical_base64(self):
        for value in ('AB', 'Zh', 'AA_', 'AA=', '****', '💥', 'a'*50000, 'QQ==', 'A'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                guest.parse_bundle('b64', f'Result: Bundle[{{b64={value}}}]')

    def test_rejects_malformed_unicode(self):
        with self.assertRaisesRegex(ValueError, 'malformed UTF-8'):
            guest.parse_bundle('b64', 'Result: Bundle[{b64=wyg}]')

    def test_accepts_boundary_utf8(self):
        value = '☂' * (guest.MAX_CLIPBOARD_BYTES // 3)
        self.assertEqual(value, guest.decode_clipboard_payload(encoded(value)))

    def test_refuses_oversized_utf8(self):
        with self.assertRaises(ValueError):
            guest.decode_clipboard_payload(encoded('🍀' * 8193))


class RaceAwareRoundTripTests(unittest.TestCase):
    def test_rejects_clipboard_changed_before_test(self):
        state = {'read': 0, 'write': 0}
        def answer(_adb, *cmd):
            if 'read' in cmd:
                state['read'] += 1
                payload = 'first' if state['read'] == 1 else 'second'
                return f'Result: Bundle[{{b64={encoded(payload)}}}]'
            state['write'] += 1
            return 'Result: Bundle[{status=ok}]'
        with patch.object(guest, 'adb_run', side_effect=answer):
            with self.assertRaisesRegex(RuntimeError, 'before test'):
                guest.clipboard_roundtrip('adb')
        self.assertEqual(state['write'], 0)

    def test_does_not_overwrite_clipboard_changed_midtest(self):
        state = {'data': encoded('original'), 'read_count': 0, 'writes': []}
        external = encoded('newer user content')
        def answer(_adb, *parts):
            method = parts[parts.index('--method')+1]
            if method == 'read':
                state['read_count'] += 1
                if state['read_count'] == 4:  # before restoring
                    state['data'] = external
                return f'Result: Bundle[{{b64={state["data"]}}}]'
            payload = parts[parts.index('--extra')+1][len('b64:s:'):]
            state['data'] = payload
            state['writes'].append(payload)
            return 'Result: Bundle[{status=ok}]'
        with patch.object(guest, 'adb_run', side_effect=answer):
            with self.assertRaisesRegex(RuntimeError, 'preserving newer content'):
                guest.clipboard_roundtrip('adb')
        self.assertEqual(state['data'], external)
        self.assertEqual(len(state['writes']), 1)  # test write only, never restored on top of user edit

    def test_does_not_expose_clipboard_contents_in_result(self):
        state = {'data': encoded('distinctive confidential original token')}
        def answer(_adb, *parts):
            method = parts[parts.index('--method')+1]
            if method == 'read':
                return f'Result: Bundle[{{b64={state["data"]}}}]'
            state['data'] = parts[parts.index('--extra')+1][len('b64:s:'):]
            return 'Result: Bundle[{status=ok}]'
        with patch.object(guest, 'adb_run', side_effect=answer):
            result = guest.clipboard_roundtrip('adb')
        self.assertNotIn('confidential', result)
        self.assertEqual(state['data'], encoded('distinctive confidential original token'))

    def test_rejects_spoofed_write_success(self):
        def answer(_adb, *parts):
            if parts[parts.index('--method')+1] == 'read':
                return f'Result: Bundle[{{b64={encoded("original")}}}]'
            return 'Result: Bundle[{not_status=ok}]'
        with patch.object(guest, 'adb_run', side_effect=answer):
            with self.assertRaises(ValueError):
                guest.clipboard_roundtrip('adb')


if __name__ == '__main__': unittest.main()
