#!/usr/bin/env python3
"""Audited, reversible Go memory policy for pinned Android 17 Soong host tool.

Only cmd/soong_build/main.go is touched, after original pinned verifiers.
No device image, Android app or unrelated Go package is modified.
"""
import argparse
import hashlib
from pathlib import Path
import subprocess

SOURCE_IMPORT = '\t"runtime"\n'
TARGET_IMPORT = '\t"runtime"\n\t"runtime/debug"\n'
SOURCE_MAIN = "func main() {\n\tflag.Parse()\n"
TARGET_MAIN = """func main() {
    // Build-host-only memory controls. Ninja env -i otherwise drops GOMEMLIMIT.
    debug.SetMemoryLimit(4608 * 1024 * 1024)
    debug.SetGCPercent(8)
    runtime.GOMAXPROCS(1)
    fmt.Fprintln(os.Stderr, "ANDARIUM_SOONG_RUNTIME_LIMIT_ACTIVE: GoLimit=4.5GiB GOGC=8 GOMAXPROCS=1")
    flag.Parse()
"""

def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["apply", "restore"])
    ap.add_argument("--workspace", type=Path, required=True)
    ap.add_argument("--audit", type=Path)
    opts = ap.parse_args()
    repo = opts.workspace / "build/soong"
    file = repo / "cmd/soong_build/main.go"
    assert (repo / ".git").exists() and not repo.is_symlink()
    assert file.is_file() and not file.is_symlink()
    original = git(repo, "show", "HEAD:cmd/soong_build/main.go").stdout
    clean_text = original.decode("utf-8")
    assert clean_text.count(SOURCE_IMPORT) == 1 and clean_text.count(SOURCE_MAIN) == 1
    assert "ANDARIUM_SOONG_RUNTIME_LIMIT_ACTIVE" not in clean_text
    patched_text = clean_text.replace(SOURCE_IMPORT, TARGET_IMPORT, 1).replace(SOURCE_MAIN, TARGET_MAIN, 1)
    assert patched_text.count("ANDARIUM_SOONG_RUNTIME_LIMIT_ACTIVE") == 1
    actual = file.read_bytes()
    if opts.mode == "apply":
        assert opts.audit is not None
        assert not git(repo, "status", "--porcelain", "--", "cmd/soong_build/main.go").stdout
        assert actual == original, "refusing to patch a modified Soong source"
        file.write_bytes(patched_text.encode("utf-8"))
        opts.audit.parent.mkdir(parents=True, exist_ok=True)
        opts.audit.write_text(
            "Pinned Soong commit: " + git(repo, "rev-parse", "HEAD").stdout.decode().strip()
            + "\nOriginal SHA256: " + hashlib.sha256(original).hexdigest()
            + "\nInstrumentation SHA256: " + hashlib.sha256(patched_text.encode()).hexdigest()
            + "\nHost-only runtime limits: Go 4.5GiB, GC 8%, GOMAXPROCS=1\n",
            encoding="utf-8")
        print("ANDARIUM_SOONG_HOST_SOURCE_INSTRUMENTED")
        print(opts.audit.read_text(encoding="utf-8"))
    else:
        assert actual == patched_text.encode("utf-8"), "refusing to undo unrelated source changes"
        file.write_bytes(original)
        assert not git(repo, "status", "--porcelain", "--", "cmd/soong_build/main.go").stdout
        print("ANDARIUM_SOONG_HOST_SOURCE_RESTORED")

if __name__ == "__main__":
    main()
