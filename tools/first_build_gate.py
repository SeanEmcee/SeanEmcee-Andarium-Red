#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Read-only first-build gate for Andarium Red v15.

Tests the EXACT source that is staged into Kernarium, does not invoke Actions,
does not sign or build an IPA, and never pretends an Android image was built.

Examples:
  python3 tools/first_build_gate.py --kernarium /path/to/Kernarium
  python3 tools/first_build_gate.py --kernarium /path/to/Kernarium --require-artifacts
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import integrate_andarium as combined
import red_runtime_overlay as red

REQUIRED_RELEASE_FILES = (
    "release-manifest.json", "boot/kernel-command-line.txt",
    "guest/partition-layout.json", "guest/system.img",
)
REQUIRED_FRAMEWORKS = (
    "KRuntime_Android_6_18_4K.xcframework",
    "MesaEGL.xcframework",
    "MesaGallium.xcframework",
    "KosmicKrisp.xcframework",
    "LibZstd.xcframework",
)


def run(command: list[str], *, cwd: Path, timeout: int = 240) -> tuple[bool, str]:
    try:
        p = subprocess.run(command, cwd=cwd, capture_output=True, text=True,
                           timeout=timeout, check=False)
        result = (p.stdout + "\n" + p.stderr).strip()
        return p.returncode == 0, result[-2800:]
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)


def inspection(kernarium: Path, *, source: Path = ROOT, require_artifacts: bool = False,
               run_tests: bool = True) -> dict:
    checks = []

    def add(name: str, good: bool, detail: str = "", *, required: bool = True):
        checks.append({"name": name, "pass": bool(good),
                       "required": bool(required), "detail": detail})

    project = kernarium / "Andarium/Andarium.xcodeproj/project.xcproj"
    found_project = project.is_file()
    add("Andarium JSON Xcode project present", found_project, str(project))
    if found_project:
        p = project.read_text()
        add("Synchronized Shared + GuestHost source folders",
            '"path": "Andarium/Shared"' in p and
            '"path": "../GuestHost/Sources"' in p,
            "Both folders must be Xcode target members")

    revision = combined.verified_upstream_revision(kernarium)
    add("Reviewed Kernarium revision",
        revision == combined.REVIEWED_UPSTREAM,
        f"found={revision or '(unavailable)'} expected={combined.REVIEWED_UPSTREAM}")

    add("Complete upstream host files", red.is_complete_checkout(kernarium))
    staged_swift = kernarium / "Andarium/Andarium/Shared"
    for fname in red.ADD_SWIFT:
        source_file = source / "host" / fname
        stage_file = staged_swift / fname
        add(f"ANDD source {fname}", source_file.is_file())
        add(f"ANDD staged source matches {fname}",
            source_file.is_file() and stage_file.is_file() and
            source_file.read_bytes() == stage_file.read_bytes(),
            "Source integration must copy the exact file into the synchronized Xcode folder")
    protocol = kernarium / "darwin/device/gpu/protocol.hpp"
    display_policy = source / "host/RedDisplayChoice.swift"
    add("Custom display matches Android EDID maximum",
        protocol.is_file() and "maximumEdidDimension = 4095" in protocol.read_text() and
        display_policy.is_file() and "maximumSide = 4095" in display_policy.read_text())
    if red.is_complete_checkout(kernarium):
        try:
            proposed = red.plan(kernarium, source)
            count = sum(path.read_text() != new for path, new in proposed.items())
            add("Host patch anchors and idempotence", True, f"{count} host files require patching")
        except Exception as exc:
            add("Host patch anchors and idempotence", False, str(exc))

    # Kernarium already implements opt-in host permission bridges. We must
    # preserve those UI handlers and live driver capabilities in the pinned
    # checkout; overlay-only tests cannot establish that permissions work.
    host_model = kernarium / "Andarium/Andarium/Shared/Model.swift"
    host_home = kernarium / "Andarium/Andarium/Shared/HomeSections.swift"
    host_live = kernarium / "Andarium/Andarium/Live/LiveRuntime.swift"
    permission_requirements = {
        "Camera": ("setCamera(", "model.setCamera("),
        "Microphone": ("setMicrophone(", "model.setMicrophone("),
        "Location": ("setLocation(", "model.setLocation("),
    }
    model_text = host_model.read_text() if host_model.is_file() else ""
    home_text = host_home.read_text() if host_home.is_file() else ""
    live_text = host_live.read_text() if host_live.is_file() else ""
    for name, (model_hook, ui_hook) in permission_requirements.items():
        add(f"Native {name.lower()} permission setting retained",
            model_hook in model_text and ui_hook in home_text,
            "iOS authorization is still granted and exercised only on a device")
    add("Camera boot setting connected to runtime",
        "cameraBootMode()" in live_text and "android_camera_mode" in live_text)
    add("Foreground location runtime connected",
        "LocationSession(" in live_text)
    instance = kernarium / "Andarium/AndariumCore/Sources/AndariumCore/Instance.swift"
    add("Persistent guest instance metadata source retained",
        instance.is_file() and "instance.json" in instance.read_text()
        if instance.is_file() else False,
        "Persistence must still be tested across relaunch and device restart")

    for setting in ("com.apple.developer.kernel.extended-virtual-addressing",
                    "com.apple.developer.kernel.increased-memory-limit"):
        entitlements = kernarium / "Andarium/Config/Andarium.entitlements"
        add(setting + " declared", entitlements.is_file() and
            setting in entitlements.read_text() if entitlements.is_file() else False,
            "A declared entitlement is NOT proof a signing profile grants it")

    if run_tests:
        good, info = run([sys.executable, "-m", "unittest", "discover",
                          "-s", "tests", "-q"], cwd=source, timeout=360)
        add("Andarium Red Python regression suite", good, info)
        swiftc = shutil.which("swiftc")
        add("Swift compiler for policy checks", swiftc is not None, swiftc or "swiftc not found")
        if swiftc is not None:
            with tempfile.TemporaryDirectory(prefix="andd-prebuild-") as temp:
                target = str(Path(temp) / "andd-values")
                files = [str(source / "host/RedDisplayChoice.swift"),
                         str(source / "tests/RedResolutionValuesHarness.swift")]
                good, info = run([swiftc, *files, "-o", target], cwd=source)
                add("Actual ANDD value source compiles", good, info)
                if good:
                    good, info = run([target], cwd=source)
                    add("ANDD value and persistence behavior", good and
                        "ANDD_VALUE_HARNESS_" in info and "_PASS" in info, info)
        if swiftc is not None:
            with tempfile.TemporaryDirectory(prefix="red-memory-prebuild-") as temp:
                target = str(Path(temp) / "memory-preset-values")
                files = [str(source / "host/RedMemoryPresetSettings.swift"),
                         str(source / "tests/RedMemoryPresetHarness.swift")]
                good, info = run([swiftc, *files, "-o", target], cwd=source)
                add("Actual memory preference source compiles", good, info)
                if good:
                    good, info = run([target], cwd=source)
                    add("Memory profile defaults and persistence behavior",
                        good and "RED_MEMORY_PRESET_12_PASS" in info, info)
        if swiftc is not None:
            for fname in red.ADD_SWIFT:
                good, info = run([swiftc, "-frontend", "-parse",
                                  str(source / "host" / fname)], cwd=source)
                add(f"Swift syntax: {fname}", good, info)
    else:
        add("Automated regression tests", False, "skipped by request; cannot certify source gate", required=True)

    if require_artifacts:
        stage = kernarium / ".build/andarium-system"
        for fname in REQUIRED_RELEASE_FILES:
            add(f"Staged Android release: {fname}", (stage / fname).is_file())
        framework = kernarium / ".build/kernarium-xcframeworks"
        for fname in REQUIRED_FRAMEWORKS:
            add(f"Runtime framework: {fname}", (framework / fname).exists())
        add("Apple Xcode tools", shutil.which("xcodebuild") is not None,
            shutil.which("xcodebuild") or "Run this step on macOS with Xcode 27")
    else:
        add("Accepted Android system/runtime binaries",
            False, "Not checked: pass --require-artifacts before compiling an IPA",
            required=False)

    blocked = [x["name"] for x in checks if x["required"] and not x["pass"]]
    return {
        "source_gate": "PASS" if not blocked else "FAIL",
        "first_build_compilation_executed": False,
        "first_build_compilation_certified": False,
        "iphone_runtime_certified": False,
        "reviewed_upstream": combined.REVIEWED_UPSTREAM,
        "blockers": blocked, "checks": checks,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kernarium", required=True, type=Path)
    ap.add_argument("--source", type=Path, default=ROOT)
    ap.add_argument("--require-artifacts", action="store_true")
    ap.add_argument("--skip-tests", action="store_true",
                    help="Developer-only quick inspection; cannot certify the test gate")
    ap.add_argument("--report", type=Path)
    a = ap.parse_args()
    result = inspection(a.kernarium.resolve(), source=a.source.resolve(),
                        require_artifacts=a.require_artifacts,
                        run_tests=not a.skip_tests)
    content = json.dumps(result, indent=2)
    print(content)
    if a.report:
        a.report.parent.mkdir(parents=True, exist_ok=True)
        a.report.write_text(content + "\n")
    if result["source_gate"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
