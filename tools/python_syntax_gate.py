#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Parse every tracked prebuild Python source without executing code or building apps.

An unterminated string, duplicated entrypoint, or accidental corruption is a
hard failure. This runs before Java/Swift checks to avoid misleading green gates.
"""
from __future__ import annotations

import ast
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP = {".git", "__pycache__", ".venv", "venv", ".pytest_cache"}


def inspect(root: Path = ROOT) -> dict:
    files = sorted(p for p in root.rglob("*.py")
                   if not any(part in SKIP for part in p.relative_to(root).parts))
    issues = []
    for path in files:
        rel = path.relative_to(root).as_posix()
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=rel)
            if rel == "tools/verify_guest.py":
                top = [node for node in tree.body if isinstance(node, (
                    ast.FunctionDef, ast.AsyncFunctionDef))]
                names = [node.name for node in top]
                for essential in ("adb_run", "read_theme_rgb", "write_theme_rgb",
                                  "theme_roundtrip", "create_persistence_marker",
                                  "verify_persistence_marker", "check", "main"):
                    if names.count(essential) != 1:
                        issues.append({"file": rel, "reason": (
                            essential + " must be defined once, found " +
                            str(names.count(essential)))})
                entrypoints = [node for node in tree.body
                               if isinstance(node, ast.If) and
                               isinstance(node.test, ast.Compare) and
                               isinstance(node.test.left, ast.Name) and
                               node.test.left.id == "__name__"]
                if len(entrypoints) != 1:
                    issues.append({"file": rel, "reason": "Expected exactly one Python CLI entrypoint"})
        except (SyntaxError, UnicodeError, OSError) as failure:
            issues.append({"file": rel, "reason": str(failure)})
    return {
        "files_checked": len(files),
        "passed": bool(files) and not issues,
        "issues": issues,
        "scope": "Python syntax and critical verifier structure; not Android/iOS runtime",
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=ROOT)
    args = p.parse_args()
    result = inspect(args.root)
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
