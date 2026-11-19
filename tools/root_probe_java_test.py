#!/usr/bin/env python3
"""Pure Java root verification harness; not an Android runtime proof."""
import subprocess
import tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if __name__ == '__main__':
    with tempfile.TemporaryDirectory() as td:
        d=Path(td)
        files=[ROOT/'launcher_src/java/dev/twoyi/redlauncher/RedRootProbe.java',ROOT/'tests/RedRootProbeHarness.java']
        result=subprocess.run(['javac','-d',str(d),*map(str,files)],capture_output=True,text=True)
        if result.returncode: raise SystemExit(result.stderr)
        result=subprocess.run(['java','-cp',str(d),'dev.twoyi.redlauncher.RedRootProbeHarness'],capture_output=True,text=True)
        if result.returncode: raise SystemExit(result.stderr)
        print(result.stdout.strip())
