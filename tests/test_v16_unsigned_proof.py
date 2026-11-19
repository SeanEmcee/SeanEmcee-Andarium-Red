#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Unit tests for the real unsigned Android target-files -> proof packager.

Uses a synthetic ZIP to test archive parsing and manifest policy, not to
pretend that an Android 17 build or device boot has passed.
"""
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.create_unsigned_proof import manifest, target_metadata


def archive(*, modules=True, release="17", build="1001"):
    payload = io.BytesIO()
    buildprop = "\n".join((
        "ro.build.version.release=" + release,
        "ro.build.fingerprint=andarium-red/test/android17:user/test",
        "ro.build.version.incremental=" + build,
        "ro.build.version.security_patch=2026-11-05",
    )) + "\n"
    apk = io.BytesIO()
    with zipfile.ZipFile(apk, "w") as a:
        a.writestr("AndroidManifest.xml", b"\\x03\\x00\\x08\\x00")
        a.writestr("classes.dex", b"dex\\n039\\x00")
    with zipfile.ZipFile(payload, "w") as z:
        z.writestr("SYSTEM/build.prop", buildprop)
        if modules:
            z.writestr("SYSTEM/app/TwoyiRedLauncher/TwoyiRedLauncher.apk", apk.getvalue())
            z.writestr("SYSTEM/priv-app/TwoyiRedClipboard/TwoyiRedClipboard.apk", apk.getvalue())
    payload.seek(0)
    return zipfile.ZipFile(payload)


class AndroidProofPackingTests(unittest.TestCase):
    def test_android_17_properties_and_modules_are_required(self):
        with archive() as z:
            props, modules = target_metadata(z)
        self.assertEqual(props["release"], "17")
        self.assertEqual(props["build_number"], "1001")
        self.assertEqual(len(modules), 2)

    def test_rejects_guest_without_our_integrations(self):
        with archive(modules=False) as z:
            with self.assertRaisesRegex(ValueError, "TwoyiRedLauncher"):
                target_metadata(z)

    def test_rejects_named_but_invalid_apk(self):
        payload = io.BytesIO()
        with zipfile.ZipFile(payload, "w") as outer:
            outer.writestr("SYSTEM/build.prop", "\\n".join((
                "ro.build.version.release=17",
                "ro.build.fingerprint=andarium-red/test",
                "ro.build.version.incremental=1001",
                "ro.build.version.security_patch=2026-11-05",
            )))
            outer.writestr("SYSTEM/app/TwoyiRedLauncher/TwoyiRedLauncher.apk", b"fake")
            outer.writestr("SYSTEM/priv-app/TwoyiRedClipboard/TwoyiRedClipboard.apk", b"fake")
        payload.seek(0)
        with zipfile.ZipFile(payload) as z:
            with self.assertRaises(zipfile.BadZipFile):
                target_metadata(z)

    def test_rejects_non17_target(self):
        with archive(release="16") as z:
            with self.assertRaisesRegex(ValueError, "not Android 17"):
                target_metadata(z)

    def test_rejects_invalid_build_number(self):
        with archive(build="eng.user") as z:
            with self.assertRaisesRegex(ValueError, "numeric build number"):
                target_metadata(z)

    def test_manifest_faithfully_marks_unsigned(self):
        props = {"fingerprint": "test", "build_number": "1001",
                 "security_patch": "2026-11-05"}
        result = manifest(release_name="red-v15-test",
                          product_family="lineage-andarium",
                          properties=props, disk_sha="a" * 64,
                          target_sha="b" * 64)
        self.assertEqual(result["acceptance"], "unsigned-proof")
        self.assertEqual(result["release_id"], "unsigned-proof-red-v15-test")
        self.assertEqual(result["android"]["major"], 17)
        self.assertEqual(result["android"]["build_number"], 1001)
        self.assertIs(result["android"]["signed"], False)
        self.assertEqual(result["producer"]["system_disk_sha256"], "a" * 64)

    def test_rejects_invalid_proof_name(self):
        props = {"fingerprint": "test", "build_number": "1001",
                 "security_patch": "2026-11-05"}
        with self.assertRaisesRegex(ValueError, "Proof release name"):
            manifest(release_name="../escaped", product_family="lineage-andarium",
                     properties=props, disk_sha="a" * 64, target_sha="b" * 64)


if __name__ == "__main__":
    unittest.main()
