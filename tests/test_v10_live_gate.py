# SPDX-License-Identifier: GPL-2.0-or-later
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import verify_guest

class LiveGateTests(unittest.TestCase):
    def test_clipboard_permission_granted(self):
        def answer(_adb,*args):
            if args[:2]==('pm','path'):return 'package:/product/app/TwoyiRedClipboard/base.apk'
            return 'requested permissions:\n android.permission.READ_CLIPBOARD_IN_BACKGROUND: granted=true\n'
        with patch.object(verify_guest,'adb_run',side_effect=answer):
            self.assertIn('granted',verify_guest.clipboard_privilege('adb'))

    def test_clipboard_permission_not_granted(self):
        def answer(_adb,*args):
            if args[:2]==('pm','path'):return 'package:/system/priv-app/TwoyiRedClipboard/base.apk'
            return 'android.permission.READ_CLIPBOARD_IN_BACKGROUND: granted=false'
        with patch.object(verify_guest,'adb_run',side_effect=answer):
            with self.assertRaisesRegex(AssertionError,'lacks Android signature'):
                verify_guest.clipboard_privilege('adb')

    def test_clipboard_permission_missing(self):
        with patch.object(verify_guest,'adb_run',return_value='not installed'):
            with self.assertRaisesRegex(AssertionError,'not installed'):
                verify_guest.clipboard_privilege('adb')

    def test_heliboard_active(self):
        def answer(_adb,*args):
            if args[:2]==('pm','path'):return 'package:/data/app/helium314.keyboard/base.apk'
            return 'helium314.keyboard/.LatinIME'
        with patch.object(verify_guest,'adb_run',side_effect=answer):
            self.assertIn('selected',verify_guest.active_heliboard('adb'))

    def test_heliboard_not_active(self):
        def answer(_adb,*args):
            if args[:2]==('pm','path'):return 'package:/data/app/helium314.keyboard/base.apk'
            return 'com.android.inputmethod.latin/.LatinIME'
        with patch.object(verify_guest,'adb_run',side_effect=answer):
            with self.assertRaisesRegex(AssertionError,'not the active'):
                verify_guest.active_heliboard('adb')

if __name__=='__main__':unittest.main()
