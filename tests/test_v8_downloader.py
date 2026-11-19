# SPDX-License-Identifier: GPL-2.0-or-later
from __future__ import annotations
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import fetch_official_apks as acquire

class DownloaderTests(unittest.TestCase):
    def test_exact_release_pin_map(self):
        self.assertEqual(len(acquire.SOURCES),6)
        self.assertIn('heliboard',acquire.SOURCES)
        self.assertIn('magisk',acquire.SOURCES)
        for name, (filename,url,size,digest) in acquire.SOURCES.items():
            self.assertTrue(filename.endswith('.apk'),name)
            self.assertTrue(url.startswith('https://'),name)
            self.assertGreater(size,1000000,name)
            self.assertEqual(len(digest),64,name)
            self.assertTrue(all(c in '0123456789abcdef' for c in digest))

    def test_absent_apk_fails_closed(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaisesRegex(ValueError,'byte count'):
                acquire.verify(Path(t)/'missing.apk',size=1,digest='0'*64)

    def test_corrupt_apk_fails_closed(self):
        with tempfile.TemporaryDirectory() as t:
            f=Path(t)/'bad.apk';f.write_bytes(b'bad')
            with self.assertRaisesRegex(ValueError,'SHA-256'):
                acquire.verify(f,size=3,digest='f'*64)

if __name__=='__main__': unittest.main()
