# SPDX-License-Identifier: GPL-2.0-or-later
"""Focused regression checks for the v9 native dashboard and root/clipboard gates.

Not device tests. Clipboard tests mock the ADB exchange and check restoration.
"""
from __future__ import annotations
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import verify_guest as guest

class NativeDashboardTests(unittest.TestCase):
    def test_android_reference_skin_is_default_with_native_fallback(self):
        source = (ROOT/'launcher_src/java/dev/twoyi/redlauncher/MainActivity.java').read_text()
        self.assertIn('getInt(HOME_STYLE_KEY, 1) == 1', source)
        self.assertIn('setHomeStyle(boolean reference, boolean persist)', source)
        self.assertIn('dashboard = new RedNativeDashboard(this);', source)
        self.assertIn('setContentView(dashboard);', source)
        self.assertIn('dashboard.refresh();', source)
        self.assertIn('Use exact-reference layout', source)
        self.assertIn('Use lightweight native layout', source)
        self.assertIn('drawHostAppRail(canvas, x, y, scale)', source)

    def test_missing_apps_are_never_shown_as_working(self):
        source = (ROOT/'launcher_src/java/dev/twoyi/redlauncher/RedNativeDashboard.java').read_text()
        self.assertIn('getPackageInfo(packageName, 0)', source)
        self.assertIn('getApplicationIcon(tile.packageName)', source)
        self.assertIn('Not installed', source)
        self.assertIn('Root access: Not checked', source)
        self.assertIn('checkRootOnUserTap()',source)
        self.assertIn('openRedAppDrawer()', source)
        self.assertNotIn('Root access: Active', source)
        self.assertIn('ticker.removeCallbacks(updateStatus)', source)

    def test_native_home_source_typechecks(self):
        done = subprocess.run([sys.executable, str(ROOT/'tools/native_home_stub_compile.py')],
                              capture_output=True, text=True, timeout=30)
        self.assertEqual(done.returncode, 0, done.stderr or done.stdout)
        self.assertIn('NATIVE_HOME_JAVA_STUB_COMPILE_PASS', done.stdout)

class RootVerificationTests(unittest.TestCase):
    def test_user_build_may_be_magisk_rooted(self):
        with patch.object(guest, 'adb_run', return_value='0') as adb:
            self.assertIn('UID 0', guest.root_uid('adb'))
            adb.assert_called_once_with('adb','su','-c','id -u')
        self.assertNotIn("require_property(args.adb, 'ro.debuggable'", (ROOT/'tools/verify_guest.py').read_text())

    def test_su_must_give_exact_root_uid(self):
        for text in ('1000', '0 extra', 'permission denied', ''):
            with self.subTest(text=text), patch.object(guest, 'adb_run', return_value=text):
                with self.assertRaises(AssertionError): guest.root_uid('adb')

    def test_magisk_daemon_must_respond(self):
        with patch.object(guest, 'adb_run', return_value='/debug_ramdisk/.magisk'):
            self.assertIn('Magisk daemon', guest.magisk_daemon('adb'))
        with patch.object(guest, 'adb_run', return_value='not found'):
            with self.assertRaises(AssertionError): guest.magisk_daemon('adb')

    def test_play_services_trio_is_checked(self):
        source = (ROOT/'tools/verify_guest.py').read_text()
        for name in ('com.android.vending','com.google.android.gms','com.google.android.gsf'):
            self.assertIn(name, source)
        self.assertIn('require-play-services', source)

class ClipboardRestorationTests(unittest.TestCase):
    def test_restores_original_text_and_checks_restoration(self):
        previous = 'b3JpZ2luYWw'   # only dummy test content
        calls=[]
        state={'value':previous}
        def answer(_adb, *parts):
            calls.append(parts)
            method = parts[parts.index('--method')+1]
            if method=='read': return 'Result: Bundle[{b64='+state['value']+'}]'
            raw = parts[parts.index('--extra')+1]
            state['value'] = raw.removeprefix('b64:s:')
            return 'Result: Bundle[{status=ok}]'
        with patch.object(guest, 'adb_run', side_effect=answer):
            self.assertIn('restore passed',guest.clipboard_roundtrip('adb'))
        self.assertEqual(state['value'], previous)
        self.assertEqual(len([p for p in calls if 'write' in p]), 2)

    def test_refuses_to_modify_non_text_clipboard(self):
        with patch.object(guest,'adb_run',return_value='Result: Bundle[{b64=~}]') as adb:
            with self.assertRaisesRegex(AssertionError,'no plain text'):
                guest.clipboard_roundtrip('adb')
            self.assertEqual(adb.call_count,1)

    def test_failed_clipboard_test_still_restores(self):
        original='b3JpZ2luYWw'
        state={'value':original}
        calls=0
        def answer(_adb,*parts):
            nonlocal calls
            calls+=1
            if parts[parts.index('--method')+1]=='read':
                return 'Result: Bundle[{b64='+state['value']+'}]'
            extra=parts[parts.index('--extra')+1].removeprefix('b64:s:')
            state['value']=extra
            return 'Result: Bundle[{status=ok}]'
        # Initial reads succeed, write succeeds, roundtrip read corrupts result,
        # then restore must run and be checked.
        count={'n':0}
        def corrupt(_adb,*parts):
            count['n']+=1
            good=answer(_adb,*parts)
            return 'Result: Bundle[{b64=YmFk}]' if count['n']==4 else good
        with patch.object(guest,'adb_run',side_effect=corrupt):
            with self.assertRaisesRegex(AssertionError,'roundtrip mismatch'):
                guest.clipboard_roundtrip('adb')
        self.assertEqual(state['value'], original)
        self.assertEqual(calls,7)

if __name__=='__main__': unittest.main()
