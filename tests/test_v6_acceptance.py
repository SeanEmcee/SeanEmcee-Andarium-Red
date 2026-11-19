# SPDX-License-Identifier: GPL-2.0-or-later
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import verify_guest as v

class V6GuestAcceptanceTests(unittest.TestCase):
    def test_bundle_parser(self):
        self.assertEqual(v.parse_bundle('status', 'Result: Bundle[{status=ok}]'), 'ok')
        self.assertEqual(v.parse_bundle('b64', 'Result: Bundle[{b64=YWJj}]'), 'YWJj')
        with self.assertRaises(ValueError): v.parse_bundle('b64', 'unknown')
    def test_root_and_status_require_actual_probe(self):
        with self.assertRaises(RuntimeError):
            v.adb_run('__nonexistent_adb__', 'id')
    def test_android17_version_requires_exact_version(self):
        from unittest.mock import patch
        with patch.object(v, 'adb_run', return_value='13'):
            with self.assertRaises(AssertionError): v.require_property('adb', 'ro.build.version.release', '17')
        with patch.object(v, 'adb_run', return_value='17'):
            self.assertEqual(v.require_property('adb','ro.build.version.release','17'),'17')
    def test_installed_package_requires_adb_confirmation(self):
        from unittest.mock import patch
        with patch.object(v, 'adb_run', return_value=''):
            with self.assertRaises(AssertionError): v.require_package('adb','com.topjohnwu.magisk')
        with patch.object(v, 'adb_run', return_value='package:/data/app/com.topjohnwu.magisk/base.apk'):
            self.assertEqual(v.require_package('adb','com.topjohnwu.magisk'),'com.topjohnwu.magisk')
if __name__ == '__main__': unittest.main()
