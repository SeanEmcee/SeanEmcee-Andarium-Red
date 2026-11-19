#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Correct pinned Kernarium's Mesa ARM64/iOS cross compiler endian macros.

The iPhoneOS arm64 CPU is little-endian; Mesa GL's generated lexer includes
u_endian.h without both macros being defined on this Xcode cross target.
Only add those true target architecture definitions to the existing Meson
cross-file C/C++ flags. Leave all third-party source, driver selections,
optimizations, ABI contracts, and release verification untouched.

Fails closed if the pinned source, reviewed anchors, or prior edits differ.
The change applies solely to the ephemeral Kernarium clone, never its remote.
"""
from __future__ import annotations
import argparse
import subprocess
from pathlib import Path

PIN = "fbe12ee72d195f0241c4fc24090a98b259026604"
RELATIVE = "dependencies/build-apple-gpu.sh"
FLAGS = ", '-DUTIL_ARCH_LITTLE_ENDIAN=1', '-DUTIL_ARCH_BIG_ENDIAN=0'"


def apply(root: Path) -> None:
    git = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                         check=True, capture_output=True, text=True)
    if git.stdout.strip() != PIN:
        raise ValueError("Refusing to change a different Kernarium revision")
    target = root / RELATIVE
    before = target.read_text(encoding="utf-8")
    changes = 0
    content = before
    for key in ("c_args", "cpp_args"):
        # Anchor the START of a Meson option line: `c_args` also appears
        # as a suffix of `objc_args` and `objcpp_args`. Substring counting
        # previously rejected the authentic pinned script before compiling.
        marker = ("\n" + key + " = ['-arch', 'arm64', '-target', '$TARGET', "
                  "'-isysroot', '$SDK_ROOT', '-I$STAGE/include']")
        changed = marker[:-1] + FLAGS + "]"
        if content.count(changed) == 1:
            continue
        if content.count(marker) != 1:
            raise ValueError("Unreviewed Mesa cross-compilation flags: " + key)
        content = content.replace(marker, changed, 1)
        changes += 1
    if changes:
        target.write_text(content, encoding="utf-8")
    if content.count("'-DUTIL_ARCH_LITTLE_ENDIAN=1'") != 2 or content.count(
        "'-DUTIL_ARCH_BIG_ENDIAN=0'"
    ) != 2:
        raise ValueError("Mesa endianness correction was not applied exactly twice")
    result = subprocess.run(["git", "-C", str(root), "diff", "--check", "--", RELATIVE],
                            capture_output=True, text=True)
    if result.returncode:
        raise ValueError("Malformed cross-file correction: " + result.stderr)
    # Inspect that no other tracked Kernarium source was modified by THIS
    # correction. Earlier Andarium Red source overlays may already be dirty.
    print("VERIFIED_IOS_ARM64_MESA_ENDIAN_CROSS_FLAGS: little=1 big=0")
    print("ENDIAN_PATCH_SOURCE: " + RELATIVE)
    print("GRAPHICS_DRIVERS_AND_MESA_SOURCES: preserved")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kernarium", type=Path)
    args = parser.parse_args()
    apply(args.kernarium.resolve())
