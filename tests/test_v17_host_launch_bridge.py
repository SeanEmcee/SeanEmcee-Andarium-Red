#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Android home -> Nexaris native shell bridge. No Android runtime claim."""
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JAVA = ROOT / "launcher_src/java/dev/twoyi/redlauncher"


class AndroidHostLaunchTests(unittest.TestCase):
    def test_real_java_wire_harness(self):
        with tempfile.TemporaryDirectory() as tmp:
            command = ["javac", "-d", tmp, str(JAVA / "HostLaunchWire.java"),
                       str(ROOT / "tests/HostLaunchWireHarness.java")]
            compile_ = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(compile_.returncode, 0, compile_.stderr)
            run = subprocess.run(["java", "-cp", tmp,
                                  "dev.twoyi.redlauncher.HostLaunchWireHarness"],
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn("HOST_LAUNCH_WIRE_", run.stdout)
            self.assertIn("_PASS", run.stdout)

    def test_provider_declared_exported_with_enforced_uid(self):
        manifest = ET.parse(ROOT / "launcher_src/AndroidManifest.xml")
        ns = "{http://schemas.android.com/apk/res/android}"
        providers = manifest.findall(".//provider")
        bridge = [p for p in providers if p.get(ns + "name") ==
                  ".HostLaunchBridgeProvider"]
        self.assertEqual(len(bridge), 1)
        self.assertEqual(bridge[0].get(ns + "authorities"),
                         "dev.twoyi.redlauncher.host")
        provider = (JAVA / "HostLaunchBridgeProvider.java").read_text()
        self.assertIn("Binder.getCallingUid() != Process.myUid()", provider)
        self.assertIn("caller == Process.SHELL_UID || caller == Process.ROOT_UID", provider)
        self.assertIn('if ("enqueue".equals(method))', provider)
        self.assertIn('if ("next".equals(method))', provider)
        self.assertIn('if ("ack".equals(method))', provider)
        self.assertIn("HostLaunchWire.matchesAck(event, arg)", provider)
        self.assertIn("EXPIRATION_MS = 120000L", provider)
        self.assertIn("gate.notifyAll()", provider)
        self.assertIn("gate.wait(waitMs)", provider)

    def test_reference_and_native_home_host_app_targets(self):
        home = (JAVA / "MainActivity.java").read_text()
        dashboard = (JAVA / "RedNativeDashboard.java").read_text()
        self.assertIn("drawHostAppRail(canvas, x, y, scale)", home)
        self.assertIn("requestHostApp(HostLaunchWire.ROUTES[index])", home)
        self.assertIn("HostLaunchBridgeProvider.request(this, route)", home)
        self.assertIn("hostRoutes = HostLaunchWire.ROUTES", dashboard)
        self.assertIn("owner.requestHostApp(route)", dashboard)
        self.assertIn("NEXARIS HOST APPS", dashboard)

    def test_five_android_launcher_aliases_are_real_and_prewired(self):
        manifest = ET.parse(ROOT / "launcher_src/AndroidManifest.xml")
        ns = "{http://schemas.android.com/apk/res/android}"
        expected = {
            ".HostNexaris": "nexaris",
            ".HostURLOS": "urlos",
            ".HostRapBox": "rapbox",
            ".HostRapKeys": "rapkeys",
            ".HostSettings": "settings",
        }
        aliases = manifest.findall(".//activity-alias")
        self.assertEqual({a.get(ns + "name") for a in aliases}, set(expected))
        declared = {a.get(ns + "name") for a in manifest.findall(".//activity")}
        self.assertIn(".HostShortcutActivity", declared)
        for alias in aliases:
            self.assertEqual(alias.get(ns + "targetActivity"), ".HostShortcutActivity")
            self.assertEqual(alias.get(ns + "exported"), "true")
            filters = alias.findall("intent-filter")
            self.assertEqual(len(filters), 1)
            actions = {a.get(ns + "name") for a in filters[0].findall("action")}
            categories = {c.get(ns + "name") for c in filters[0].findall("category")}
            self.assertIn("android.intent.action.MAIN", actions)
            self.assertIn("android.intent.category.LAUNCHER", categories)
            icon = alias.get(ns + "icon")
            self.assertTrue(icon and icon.startswith("@drawable/ic_host_"))
            self.assertTrue((ROOT / "launcher_src/res/drawable" /
                             (icon.removeprefix("@drawable/") + ".xml")).is_file())
        activity = (JAVA / "HostShortcutActivity.java").read_text()
        self.assertIn("HostLaunchBridgeProvider.request(this, route)", activity)
        self.assertIn("component.getClassName()", activity)
        self.assertIn("finish();", activity)
        self.assertNotIn("getStringExtra", activity)
        for alias, route in expected.items():
            self.assertIn(alias[1:] + '\": return \"' + route + '\"', activity)

    def test_overlay_includes_host_transport_source(self):
        integration = (ROOT / "install_source_overlay.py").read_text()
        self.assertIn("RedHostRouteRuntime.swift", integration)
        runtime = (ROOT / "host/RedHostRouteRuntime.swift").read_text()
        self.assertIn("redReadNativeHostLaunchMessage()", runtime)
        self.assertIn("redAcknowledgeNativeHostLaunchMessage", runtime)
        self.assertIn("redClipboardShell(", runtime)
        self.assertIn("id.utf8.count == 32", runtime)


if __name__ == "__main__":
    unittest.main()
