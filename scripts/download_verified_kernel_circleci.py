#!/usr/bin/env python3
"""Download an exact authenticated GitHub Actions kernel artifact for CircleCI.

Never display the token or request headers in logs.
"""
import io
import json
import os
import pathlib
import urllib.error
import urllib.request
import zipfile

repo = "SeanEmcee/SeanEmcee-Andarium-Red"
run = os.environ["KERNEL_RUN_ID"]
name = "andarium-pinned-android17-abi29-4k-kernel-" + os.environ["KERNEL_SOURCE_SHA"]
token = os.environ.get("GITHUB_TOKEN", "").strip()
if not token or token.lower().startswith(("your_", "ghp_example", "github_token")):
    raise SystemExit("Missing or placeholder GITHUB_TOKEN. Set a valid fine-grained GitHub token in CircleCI Project Settings > Environment Variables.")
headers = {
    "Authorization": "Bearer " + token,
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

def request(url):
    try:
        return urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=180)
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise SystemExit(
                "GitHub rejected GITHUB_TOKEN (HTTP 401). Replace the CircleCI secret "
                "with a real, unexpired token; repository access to "
                "SeanEmcee-Andarium-Red and Actions: Read are required."
            ) from None
        if exc.code == 403:
            raise SystemExit(
                "GitHub denied artifact access (HTTP 403). Check the token's "
                "repository selection, Actions: Read permission and account policy."
            ) from None
        if exc.code == 404:
            raise SystemExit(
                "GitHub artifact endpoint returned HTTP 404. Verify the producing "
                "run, artifact retention and token repository access."
            ) from None
        raise

with request(f"https://api.github.com/repos/{repo}/actions/runs/{run}/artifacts?per_page=100") as response:
    artifacts = json.load(response)["artifacts"]
matches = [a for a in artifacts if a["name"] == name and not a["expired"]]
if len(matches) != 1:
    raise SystemExit("Expected exactly one unexpired kernel artifact for pinned source SHA")
with request(matches[0]["archive_download_url"]) as response:
    archive = response.read()
dest = pathlib.Path(".build/android-kernel")
dest.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(io.BytesIO(archive)) as z:
    for item in z.infolist():
        p = pathlib.PurePosixPath(item.filename)
        mode = item.external_attr >> 16
        if p.is_absolute() or ".." in p.parts or not p.parts or (mode & 0o170000) == 0o120000:
            raise SystemExit("Unsafe artifact entry rejected")
        z.extract(item, dest)
print("Downloaded original verified kernel artifact ID:", matches[0]["id"])
