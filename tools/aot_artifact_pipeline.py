#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Generate and verify a Kernarium Android 17 native AOT artifact from an actual release.

Never edits accepted-aot.env or asserts a measurable FPS gain. Upstream owns
release acceptance; "describe" prints a candidate descriptor for review.
"""
from __future__ import annotations
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

EXPECTED = ('tools/aot/rewrite.py', 'tools/aot/release_artifact.py',
            'tools/aot/libraries.txt', 'darwin/cpu/arm64/aot/CMakeLists.txt',
            'android/lineage-24/metadata/lineage.env')


def plan(kernarium: Path, release: Path, fsck: Path, destination: Path, jobs: int = 0,
         archive_candidate: bool = False) -> list[list[str]]:
    root = kernarium.resolve()
    for rel in EXPECTED:
        if not (root / rel).is_file():
            raise ValueError('Missing upstream AOT source: ' + rel)
    if "LINEAGE24_ANDROID_MAJOR=17" not in (root / EXPECTED[-1]).read_text():
        raise ValueError('Target source is not the pinned Android 17 product')
    if not release.is_dir():
        raise ValueError('A real, installed Android 17 release directory is required')
    if not fsck.is_file():
        raise ValueError('fsck.erofs executable is required (with zstd support)')
    if not fsck.stat().st_mode & 0o111:
        raise ValueError('fsck.erofs file is not executable')
    if destination.exists():
        raise ValueError('AOT output already exists; refusing to overwrite verified artifacts')
    if jobs < 0 or jobs > 256:
        raise ValueError('AOT build jobs must be from 0 to 256')
    tool = str(root / 'tools/aot/release_artifact.py')
    build = [sys.executable, '-B', tool, 'build', '--release', str(release.resolve()),
             '--fsck-erofs', str(fsck.resolve()), '--out', str(destination.resolve())]
    if jobs:
        build.extend(['--jobs', str(jobs)])
    verify = [sys.executable, '-B', tool, 'verify', '--artifact', str(destination.resolve()),
              '--release', str(release.resolve())]
    describe = [sys.executable, '-B', tool, 'describe', '--artifact', str(destination.resolve()),
                '--archives', 'yes' if archive_candidate else 'no']
    return [build, verify, describe]


REQUIRED_DESCRIPTOR = (
    'LINEAGE24_ACCEPTED_AOT_SCHEMA',
    'LINEAGE24_ACCEPTED_AOT_RELEASE_ID',
    'LINEAGE24_ACCEPTED_AOT_ARTIFACT_SHA256',
    'LINEAGE24_ACCEPTED_AOT_BLOB_SHA256',
    'LINEAGE24_ACCEPTED_AOT_BLOB_VERSION',
    'LINEAGE24_ACCEPTED_AOT_ARCHIVES',
)


def validate_candidate(text: str, *, archive_candidate: bool) -> dict[str, str]:
    """Reject a truncated or contradictory AOT acceptance descriptor.

    This is NOT upstream acceptance; it checks the file before handing it to
    the official `verify --accepted` command for a matching release.
    """
    fields: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        if '=' not in line:
            raise ValueError('AOT descriptor contains an invalid record')
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip().strip('\"').strip("'")
        if key not in REQUIRED_DESCRIPTOR or key in fields:
            raise ValueError('AOT descriptor has an unknown or duplicated key')
        fields[key] = value
    if set(fields) != set(REQUIRED_DESCRIPTOR):
        raise ValueError('AOT descriptor is missing required fields')
    for key in ('LINEAGE24_ACCEPTED_AOT_ARTIFACT_SHA256', 'LINEAGE24_ACCEPTED_AOT_BLOB_SHA256'):
        if not re.fullmatch('[0-9a-f]{64}', fields[key]):
            raise ValueError('AOT descriptor has an invalid artifact digest')
    if not re.fullmatch('[a-z0-9][a-z0-9._-]{0,63}', fields['LINEAGE24_ACCEPTED_AOT_RELEASE_ID']):
        raise ValueError('AOT descriptor has an invalid release ID')
    if not fields['LINEAGE24_ACCEPTED_AOT_SCHEMA'].isdigit() or not fields['LINEAGE24_ACCEPTED_AOT_BLOB_VERSION'].isdigit():
        raise ValueError('AOT descriptor has invalid numeric version fields')
    requested = 'yes' if archive_candidate else 'no'
    if fields['LINEAGE24_ACCEPTED_AOT_ARCHIVES'] != requested:
        raise ValueError('AOT descriptor archive policy differs from requested build')
    return fields


def validate_against_upstream(kernarium: Path, artifact: Path, release: Path, candidate: Path) -> None:
    """Use Kernarium's actual verifier before retaining a generated candidate."""
    tool = kernarium / 'tools/aot/release_artifact.py'
    command = [sys.executable, '-B', str(tool), 'verify', '--artifact', str(artifact),
               '--release', str(release), '--accepted', str(candidate)]
    result = subprocess.run(command, cwd=kernarium, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError('Upstream rejected AOT candidate: ' + result.stderr[-2000:])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kernarium', required=True, type=Path)
    parser.add_argument('--release', required=True, type=Path)
    parser.add_argument('--fsck-erofs', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--jobs', type=int, default=0)
    parser.add_argument('--run', action='store_true', help='Actually build and verify AOT native code')
    parser.add_argument('--archive-candidate', action='store_true',
                        help='Emit reviewed-candidate descriptor allowing archive AOT; never installs or accepts it')
    arguments = parser.parse_args()
    commands = plan(arguments.kernarium, arguments.release,
                    arguments.fsck_erofs, arguments.out, arguments.jobs, arguments.archive_candidate)
    if not arguments.run:
        print(json.dumps({'status':'PLAN ONLY; native AOT not built', 'commands':commands,
                          'archives_candidate_requested':arguments.archive_candidate,
                          'archives_enabled':False}, indent=2))
        return
    for number, command in enumerate(commands):
        completed = subprocess.run(command, cwd=arguments.kernarium, capture_output=True, text=True)
        if completed.returncode:
            raise SystemExit('AOT command failed: ' + ' '.join(command) + '\n' + completed.stderr[-3000:])
        if number == 2:
            target = arguments.out.with_suffix('.accepted-aot.candidate.env')
            try:
                validate_candidate(completed.stdout, archive_candidate=arguments.archive_candidate)
                # Exclusive creation, not an existence-then-write race.
                with target.open('x', encoding='utf-8') as candidate:
                    candidate.write(completed.stdout)
                # Only keep the candidate when upstream accepts the identity
                # and digest linkage against the same installed release.
                try:
                    validate_against_upstream(arguments.kernarium.resolve(),
                                              arguments.out.resolve(), arguments.release.resolve(), target.resolve())
                except Exception:
                    target.unlink(missing_ok=True)
                    raise
            except (ValueError, OSError, RuntimeError) as error:
                raise SystemExit('AOT acceptance candidate rejected: ' + str(error)) from error
            print('AOT artifact verified; descriptor verified by upstream, candidate ONLY: ' + str(target))
        else:
            print(completed.stdout.strip())
    print('AOT artifact is VERIFIED, not accepted. Upstream release and archive checks still required;')
    print('the candidate descriptor was not copied into metadata/accepted-aot.env.')

if __name__ == '__main__': main()
