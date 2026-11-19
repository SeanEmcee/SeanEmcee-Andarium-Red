# SPDX-License-Identifier: Apache-2.0
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ResponsiveDashboardTests(unittest.TestCase):
    def test_native_dashboard_uses_adaptive_grid_width(self):
        src = (ROOT / "launcher_src/java/dev/twoyi/redlauncher/RedNativeDashboard.java").read_text()
        self.assertIn("DashboardGridPolicy.columns", src)
        self.assertIn("DashboardGridPolicy.cellWidth", src)
        self.assertNotIn("grid.setColumnCount(4)", src)

    def test_native_dashboard_layout_math_compiles_and_passes(self):
        cp = subprocess.run([sys.executable, str(ROOT / "tools/dashboard_grid_behavior_test.py")],
                            capture_output=True, text=True, timeout=45)
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertIn("DASHBOARD_GRID_2006_PASS", cp.stdout)


if __name__ == "__main__":
    unittest.main()
