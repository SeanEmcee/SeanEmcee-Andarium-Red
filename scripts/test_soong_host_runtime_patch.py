#!/usr/bin/env python3
"""Fixture tests for Soong host-only Go limits and exact reversal."""
from pathlib import Path
import subprocess
import sys
import tempfile

patcher = Path(__file__).with_name("patch_soong_host_runtime.py")
def cmd(*a):
    return subprocess.run(a, check=True, text=True, capture_output=True)
with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    repo = root / "build/soong"
    main = repo / "cmd/soong_build/main.go"
    main.parent.mkdir(parents=True)
    main.write_text('package main\nimport (\n\t"flag"\n\t"fmt"\n\t"os"\n\t"runtime"\n\t"time"\n)\n'
                    'func main() {\n\tflag.Parse()\n\tfmt.Println("OK")\n}\n', encoding="utf-8")
    cmd("git", "-C", str(repo), "init", "-q")
    cmd("git", "-C", str(repo), "add", ".")
    cmd("git", "-C", str(repo), "-c", "user.name=CI", "-c", "user.email=ci@example.invalid", "commit", "-qm", "original")
    original = main.read_bytes()
    cmd(sys.executable, str(patcher), "apply", "--workspace", str(root), "--audit", str(root/"audit.txt"))
    current = main.read_text()
    assert "debug.SetMemoryLimit(6 * 1024 * 1024 * 1024)" in current
    assert "debug.SetGCPercent(20)" in current
    assert "runtime.GOMAXPROCS(1)" in current
    assert "ANDARIUM_SOONG_GO_STATS" in current
    assert "time.NewTicker(60 * time.Second)" in current
    assert (root/"audit.txt").is_file()
    if subprocess.run(["which", "go"], capture_output=True).returncode == 0:
        result = cmd("go", "run", str(main))
        assert result.stdout.strip() == "OK"
        assert "ANDARIUM_SOONG_RUNTIME_LIMIT_ACTIVE" in result.stderr
    again = subprocess.run([sys.executable, str(patcher), "apply", "--workspace", str(root),
                            "--audit", str(root/"audit.txt")], capture_output=True)
    assert again.returncode != 0, "double patch was accepted"
    cmd(sys.executable, str(patcher), "restore", "--workspace", str(root))
    assert main.read_bytes() == original
    assert not cmd("git", "-C", str(repo), "status", "--porcelain").stdout.strip()
print("PASS: Soong in-process Go memory policy, exact source and revert")
