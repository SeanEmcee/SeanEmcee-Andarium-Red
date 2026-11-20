#!/usr/bin/env python3
"""Find a prior verified-kernel *upload candidate* from this repository/branch.

Discovery is deliberately not an integrity claim: the downloaded candidate must
pass Kernarium's unchanged descriptor/ELF/config/ABI verifier before reuse.
Only the GitHub Actions artifact metadata endpoint is read; no untrusted names
are executed or used as filesystem paths.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

NAME_PREFIX = "andarium-pinned-android17-abi29-4k-kernel-"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repository", required=True)
    ap.add_argument("--branch", required=True)
    ap.add_argument("--exclude-sha", required=True)
    ap.add_argument("--github-output", type=Path, required=True)
    args = ap.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repository):
        ap.error("invalid repository")
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise SystemExit("GITHUB_TOKEN is required to read workflow artifacts")
    candidates: list[dict] = []
    for page in range(1, 4):
        url = (
            f"https://api.github.com/repos/{args.repository}/actions/artifacts"
            f"?per_page=100&page={page}"
        )
        request = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "Andarium-Red-kernel-cache-discovery",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                document = json.load(response)
        except (OSError, ValueError, urllib.error.HTTPError) as exc:
            raise SystemExit(
                f"cannot inspect prior GitHub kernel artifacts: {type(exc).__name__}"
            ) from exc
        artifacts = document.get("artifacts", [])
        if not isinstance(artifacts, list):
            raise SystemExit("unexpected GitHub Actions artifact metadata")
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                continue
            name = artifact.get("name", "")
            workflow = artifact.get("workflow_run") or {}
            if not isinstance(name, str) or not isinstance(workflow, dict):
                continue
            if not name.startswith(NAME_PREFIX) or artifact.get("expired"):
                continue
            sha = name[len(NAME_PREFIX):]
            if not re.fullmatch(r"[0-9a-f]{40}", sha):
                continue
            if sha == args.exclude_sha or workflow.get("head_sha") != sha:
                continue
            if workflow.get("head_branch") != args.branch:
                continue
            run_id = workflow.get("id")
            if not isinstance(run_id, int) or run_id <= 0:
                continue
            candidates.append(artifact)
        if len(artifacts) < 100:
            break

    candidates.sort(key=lambda a: (a.get("created_at") or "", a["id"]), reverse=True)
    found = bool(candidates)
    with args.github_output.open("a", encoding="utf-8") as out:
        print(f"found={str(found).lower()}", file=out)
        if found:
            selected = candidates[0]
            print(f"run_id={selected['workflow_run']['id']}", file=out)
            print(f"artifact_name={selected['name']}", file=out)
    if found:
        print(
            "Found prior uploaded kernel candidate in run "
            f"{candidates[0]['workflow_run']['id']}; "
            "Kernarium verification is still required"
        )
    else:
        print("No prior uploaded ABI29 kernel artifact; a fresh verified build is required")
    return 0


if __name__ == "__main__":
    sys.exit(main())
