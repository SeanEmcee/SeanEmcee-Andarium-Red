#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Prepare the Android 17 Andarium app source for EMBEDDING in Nexaris.

Source-only operation: does not modify an installed app, compile binaries,
download runtime frameworks, create an IPA, or prove a working Android guest.

The upstream file contains both Andarium's @main UIApplicationDelegate and
AndariumProcess/RootView. Excluding the whole file loses real guest UI types.
Only the standalone app delegate is conditionally omitted when embedding.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

APP = Path("Andarium/Andarium/Shared/AndariumApp.swift")
METADATA = Path("android/lineage-24/metadata/lineage.env")
BEGIN = "@main\nfinal class AndariumApp: UIResponder, UIApplicationDelegate {"
AFTER = "/// The entry, model and runtime of the process."
FLAG = "NEXARIS_EMBEDDED_ANDARIUM"
START_GUARD = "#if !" + FLAG + "\n"
END_GUARD = "#endif // !" + FLAG + "\n\n"
EXPECTED_ANDROID = "LINEAGE24_ANDROID_MAJOR=17"


def prepare(source: str) -> tuple[str, bool]:
    """Return conditionalized source and whether it changed. Fail closed."""
    tagged = START_GUARD + BEGIN
    if tagged in source and END_GUARD + AFTER in source:
        if source.count(tagged) != 1 or source.count(END_GUARD + AFTER) != 1:
            raise ValueError("Duplicated Andarium application guard")
        return source, False
    if source.count(BEGIN) != 1 or source.count(AFTER) != 1:
        raise ValueError("Upstream Andarium application layout changed")
    i = source.index(BEGIN)
    j = source.index(AFTER)
    if i >= j or "final class AndariumProcess" not in source[j:]:
        raise ValueError("AndariumProcess/RootView must remain available")
    before = source[:i] + START_GUARD + source[i:j] + END_GUARD + source[j:]
    if before.count("@main") != 1:
        raise ValueError("Unexpected additional @main entrypoints")
    return before, True


def inspect(root: Path, apply: bool = False) -> dict:
    app = root / APP
    metadata = root / METADATA
    if not app.is_file() or not metadata.is_file():
        raise ValueError("Expected a Kernarium checkout with Android 17 Andarium sources")
    if EXPECTED_ANDROID not in metadata.read_text():
        raise ValueError("Upstream guest release is not declared Android 17")
    previous = app.read_text(encoding="utf-8")
    prepared, changed = prepare(previous)
    if apply and changed:
        app.write_text(prepared, encoding="utf-8")
    return {
        "android": "17",
        "source_guard_ready": not changed or apply,
        "source_change_needed": changed,
        "source_changed": bool(apply and changed),
        "flag": FLAG,
        "still_required": [
            "Link AndariumCore, GuestHost, Kernarium native runtime and GPU frameworks into Nexaris",
            "Preserve Andarium's guest release resources and independent data storage",
            "Enable NEXARIS_EMBEDDED_ANDARIUM only in a combined signed target",
            "Build/boot Android 17 and run iPhone runtime acceptance checks",
        ],
        "runtime_verified": False,
        "release_gate": "NO-GO",
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--kernarium", type=Path, required=True)
    p.add_argument("--apply", action="store_true", help="Explicitly edit only upstream AndariumApp.swift")
    args = p.parse_args()
    try:
        report = inspect(args.kernarium, apply=args.apply)
    except (OSError, ValueError) as exc:
        print(json.dumps({"source_guard_ready": False, "error": str(exc),
                          "release_gate": "NO-GO"}, indent=2))
        return 1
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
