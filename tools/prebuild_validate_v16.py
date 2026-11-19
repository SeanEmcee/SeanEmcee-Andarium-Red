#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Andarium Red offline source validation, without GitHub Actions or app builds.

A PASS means the local source/tests passed, NOT that Android 17, Magisk,
clipboard, AOT, or a signed iPhone runtime has been proven functional.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def commands() -> list[tuple[str, list[str], int]]:
    python = sys.executable
    return [
        ('Python regression suite', [python, '-m', 'unittest', 'discover',
                                     '-s', 'tests', '-q'], 210),
        ('Root Java subprocess harness', [python, 'tools/root_probe_java_test.py'], 60),
        ('Android clipboard Java syntax', [python, 'tools/java_compile_smoke.py'], 60),
        ('Clipboard provider Java behavior', [python, 'tools/clipboard_provider_behavior_test.py'], 60),
        ('Android native HOME Java stubs', [python, 'tools/native_home_stub_compile.py'], 60),
        ('Android native panels Java stubs', [python, 'tools/android_panel_stub_compile.py'], 60),
        ('Android RGB Java persistence', [python, 'tools/accent_store_behavior_test.py'], 60),
        ('Android RGB provider permission behavior', [python, 'tools/theme_provider_behavior_test.py'], 60),
        ('Evidence-based source gates', [python, 'tools/prebuild_parity.py',
                                         '--require-source-ready'], 60),
    ]


def run(*, only: str = '', report: Path | None = None) -> int:
    started = time.monotonic()
    rows = []
    for name, argv, timeout in commands():
        if only and only.lower() not in name.lower():
            continue
        error = ''
        stdout = ''
        elapsed = time.monotonic()
        try:
            p = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True,
                               timeout=timeout, check=False)
            code = p.returncode
            stdout = p.stdout[-4000:]
            error = p.stderr[-4000:]
        except (OSError, subprocess.TimeoutExpired) as exc:
            code = -1
            error = str(exc)
        rows.append({
            'check': name,
            'passed': code == 0,
            'exit_code': code,
            'elapsed_seconds': round(time.monotonic() - elapsed, 2),
            'stdout_tail': stdout,
            'stderr_tail': error,
        })
    if not rows:
        raise ValueError('No source checks matched the filter')
    result = {
        'product': 'Andarium Red Android 17',
        'scope': 'offline source and test harnesses only; no Android/iOS application build',
        'source_checks_passed': all(row['passed'] for row in rows),
        'check_scope': 'FILTERED: not all checks executed' if only else 'COMPLETE: all configured checks executed',
        'checks_attempted': len(rows),
        'checks_configured': len(commands()),
        'checks': rows,
        'elapsed_seconds': round(time.monotonic() - started, 2),
        'release_gate': 'NO-GO',
        'runtime_acceptance': 'UNVERIFIED',
        'warning': 'All green here is not 100% Android/iPhone functional parity.',
    }
    rendered = json.dumps(result, indent=2)
    if report is not None:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(rendered + '\n', encoding='utf-8')
    print(rendered)
    return 0 if result['source_checks_passed'] else 1


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--only', default='', help='Run source checks matching this substring')
    p.add_argument('--report', type=Path, help='Write machine-readable JSON')
    args = p.parse_args()
    return run(only=args.only, report=args.report)


if __name__ == '__main__':
    raise SystemExit(main())
