#!/usr/bin/env python3
"""Persist bounded, redacted Android17 compiler snapshots as a neutral GitHub check.

This does not create a build artifact. Checks remain completed/neutral even
if a hosted worker disappears; snapshots survive ephemeral runner shutdowns.
"""
import datetime
import json
import os
from pathlib import Path
import re
import sys
import urllib.request

def clean(s):
    s = re.sub(r"(?i)github_pat_[A-Za-z0-9_]{15,}|gh[pousr]_[A-Za-z0-9_]{15,}", "[REDACTED]", s)
    return re.sub(r"(?i)(?:token|secret|password|authorization|api_key)\s*[:=]\s*\S+", "[REDACTED]", s)

def readtail(path, limit=6500):
    if not path.is_file() or path.is_symlink():
        return "No file yet."
    with path.open("rb") as f:
        f.seek(0, 2)
        f.seek(max(0, f.tell()-2*limit))
        return clean(f.read().decode("utf8", errors="replace")[-limit:])

def summary(root, phase):
    sample=readtail(root/"resource-samples.log", 2600)
    log=readtail(root/"andarium-build-complete.log", 6500)
    run=os.environ.get("GITHUB_RUN_ID", "")
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    return ("Run "+run+" | "+phase+" | "+now+
            "\nThis is a diagnostic snapshot, not a completed Android image.\n\n"
            "RESOURCE TAIL:\n"+sample+"\n\nCOMPILER TAIL:\n"+log)

def api(method, path, body):
    token=os.environ.get("GITHUB_TOKEN", "")
    repo=os.environ.get("GITHUB_REPOSITORY", "")
    if not token or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise SystemExit("ERROR: missing GitHub Actions token/repo")
    if not path.startswith("/repos/"+repo+"/"):
        raise SystemExit("ERROR: invalid check-run API path")
    req=urllib.request.Request(
        "https://api.github.com"+path,
        data=json.dumps(body).encode(), method=method,
        headers={"Authorization":"Bearer "+token,
                 "Accept":"application/vnd.github+json",
                 "X-GitHub-Api-Version":"2022-11-28",
                 "Content-Type":"application/json",
                 "User-Agent":"AndariumRedBuildTelemetry"})
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.load(response)

def main():
    if len(sys.argv)!=2 or sys.argv[1] not in ("start","update","finish"):
        raise SystemExit("usage: android17_build_telemetry.py start|update|finish")
    action=sys.argv[1]
    folder=Path("diagnostics")
    folder.mkdir(parents=True,exist_ok=True)
    marker=folder/"telemetry-check-id"
    repo=os.environ["GITHUB_REPOSITORY"]
    run=os.environ["GITHUB_RUN_ID"]
    phase={"start":"started","update":"compiling","finish":"completed"}[action]
    content={"title":"Andarium Red compiler checkpoint: "+phase,
             "summary":summary(folder,phase)}
    if action=="start":
        if marker.exists():
            raise SystemExit("ERROR: telemetry check already exists")
        sha=os.environ["GITHUB_SHA"]
        if not re.fullmatch(r"[0-9a-f]{40}",sha):
            raise SystemExit("ERROR: invalid source revision")
        data=api("POST","/repos/"+repo+"/check-runs",
                 {"name":"Andarium Red compile telemetry #"+run,
                  "head_sha":sha,"status":"completed","conclusion":"neutral",
                  "output":content})
        check_id=data.get("id")
        if not isinstance(check_id,int) or check_id<1:
            raise SystemExit("ERROR: invalid check id")
        marker.write_text(str(check_id)+"\n")
    else:
        if not marker.is_file():
            raise SystemExit("ERROR: missing telemetry check id")
        check_id=marker.read_text().strip()
        if not re.fullmatch(r"[0-9]{4,20}",check_id):
            raise SystemExit("ERROR: invalid telemetry check id")
        api("PATCH","/repos/"+repo+"/check-runs/"+check_id,{"output":content})
    print("ANDARIUM_TELEMETRY_"+action.upper()+"_OK")

if __name__=="__main__":
    main()
