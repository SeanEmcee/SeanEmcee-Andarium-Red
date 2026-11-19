# SPDX-License-Identifier: GPL-2.0-or-later
import sys
import tempfile
import unittest
import struct
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import magisk_boot_preflight as m

class BootPreflightTests(unittest.TestCase):
    def test_rejects_missing_bootimage(self):
        with self.assertRaises(ValueError): m.inspect_init_boot(Path('/nonexistent/boot.img'))

    def test_rejects_non_android_boot(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'init_boot.img';p.write_bytes(b'A'*64)
            with self.assertRaises(ValueError):m.inspect_init_boot(p)

    def test_reads_kernel_less_v4_header(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'init_boot.img'
            data=bytearray(4096);data[:8]=b'ANDROID!'
            struct.pack_into('<4I',data,8,0,512,0,1584)
            struct.pack_into('<I',data,40,4)
            p.write_bytes(data)
            result=m.inspect_init_boot(p)
            self.assertEqual(result['boot_header_version'],4)
            self.assertEqual(result['kernel_bytes'],0)
            self.assertIn('UNVERIFIED',result['magisk_boot_interception_compatible'])

    def test_rejects_kernel_in_initboot(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'init_boot.img'
            data=bytearray(4096);data[:8]=b'ANDROID!'
            struct.pack_into('<4I',data,8,1024,512,0,1584)
            struct.pack_into('<I',data,40,4)
            p.write_bytes(data)
            with self.assertRaisesRegex(ValueError,'no kernel'):m.inspect_init_boot(p)

    def test_no_fabricated_magisk_asset_proof(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'magisk.apk';p.write_bytes(b'not official')
            with self.assertRaisesRegex(ValueError,'checksum'):m.inspect_magisk(p)

if __name__=='__main__':unittest.main()
