"""Resumable Android source snapshot orchestration.
The GitHub runner only starts an independent Sandbox and exits.
A separate function finalizes the snapshot after copy verification.
No operation modifies the original Android source checkout.
"""
import hashlib
import json
import os
from pathlib import Path

import modal

app = modal.App("andarium-red-snapshot-recovery")
volume = modal.Volume.from_name("andarium-red-cache")
image = modal.Image.debian_slim(python_version="3.11").apt_install(
    "git", "git-lfs", "rsync", "ca-certificates"
)

STATE = Path("/mnt/source/andarium-snapshot")
MANIFEST_SHA256 = "23b230a34a672b664c6f7e7d1d69b3aa503339acc2330471a4bcf2be3020c6dc"
ZLIB_SHA = "8731e6760935ad5289fd64c37d28155a0fa289e3"

COPY_SCRIPT = r"""
set -Eeuo pipefail
LOGDIR=/mnt/source/andarium-snapshot
mkdir -p "$LOGDIR" /work/aosp17
exec > "$LOGDIR/transfer.log" 2>&1
trap 'code=$?; echo "TRANSFER_FAILED exit=$code $(date -u)"; sync /mnt/source || true; exit "$code"' ERR
echo "SOURCE_COPY_STARTED $(date -u)"
df -h /work
rsync -a --no-owner --no-group --stats --exclude='/out/' \
  /mnt/source/aosp17/ /work/aosp17/
echo "SOURCE_COPY_COMPLETE $(date -u)"
python3 - <<'CHECK'
from pathlib import Path
import hashlib
import subprocess
import xml.etree.ElementTree as ET
root = Path("/work/aosp17").resolve()
manifest = Path("/mnt/source/AndariumRed/.build/Kernarium/android/lineage-24/metadata/base-manifest.xml")
expected = "23b230a34a672b664c6f7e7d1d69b3aa503339acc2330471a4bcf2be3020c6dc"
assert hashlib.sha256(manifest.read_bytes()).hexdigest() == expected
pins = {}
for p in ET.parse(manifest).getroot().iter("project"):
    path = p.get("path") or p.get("name")
    commit = p.get("revision", "")
    assert path and path not in pins and len(commit) == 40
    pins[path] = commit
assert len(pins) == 1239
for n, (path, commit) in enumerate(pins.items(), 1):
    work = root / path
    got = subprocess.check_output(
        ["git", "-C", str(work), "rev-parse", "HEAD"],
        text=True, timeout=120
    ).strip()
    assert got == commit, (path, got, commit)
    gitdir = Path(subprocess.check_output(
        ["git", "-C", str(work), "rev-parse", "--absolute-git-dir"],
        text=True, timeout=120
    ).strip()).resolve()
    assert gitdir.is_relative_to(root), (path, gitdir)
    if n % 100 == 0:
        print("VERIFIED_GIT_PROJECTS", n, flush=True)
print("ALL_1239_PINNED_GIT_REVISIONS_VERIFIED", flush=True)
assert (root / ".repo/manifest.xml").exists()
CHECK
printf 'complete\n' > /work/.andarium-copy-verified
echo "SOURCE_COPY_AND_PINS_VERIFIED $(date -u)"
sync /mnt/source
echo "BACKGROUND_COPY_COMPLETE_SANDBOX_READY $(date -u)"
exec sleep infinity
"""


def _read_json(path):
    return json.loads(path.read_text()) if path.is_file() else None


def _write_json(path, payload):
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    os.replace(tmp, path)


def _last_log():
    log = STATE / "transfer.log"
    if not log.is_file():
        return "Transfer log not yet present"
    with log.open("rb") as handle:
        handle.seek(max(0, log.stat().st_size - 1600))
        return handle.read().decode(errors="replace")


def _inspect(sandbox):
    if sandbox.poll() is not None:
        return False
    p = sandbox.exec("sh", "-c", "test -f /work/.andarium-copy-verified")
    return p.wait() == 0


@app.function(image=image, timeout=240)
def detached_app_persistence_probe():
    """Create a tiny Sandbox to test app detachment, with no Android copying."""
    sb = modal.Sandbox.create(
        "sleep", "infinity", app=app, image=image,
        cpu=1, memory=512, timeout=600
    )
    print("PERSISTENCE_PROBE_SANDBOX_ID", sb.object_id, flush=True)
    sb.detach()


@app.function(image=image, timeout=480, volumes={"/mnt/source": volume})
def start_snapshot_copy():
    """Start at most one cloud-side copy, then exit; no 25-minute GitHub dependency."""
    if _read_json(STATE / "snapshot_verified.json"):
        print("SNAPSHOT_ALREADY_VERIFIED", flush=True)
        return
    if _read_json(STATE / "snapshot_created.json"):
        print("SNAPSHOT_ALREADY_CREATED; use finalize, not a new copy", flush=True)
        return

    old = _read_json(STATE / "sandbox.json")
    if old:
        prior = modal.Sandbox.from_id(old["id"])
        exitcode = prior.poll()
        print("PREVIOUS_SANDBOX", old["id"], "EXIT", exitcode, flush=True)
        if exitcode is None:
            print("COPY_ALREADY_ACTIVE", old["id"], flush=True)
            return
        archived = STATE / ("sandbox-terminated-" + old["id"] + ".json")
        assert not archived.exists(), "Previous Sandbox history already exists; inspect manually"
        os.replace(STATE / "sandbox.json", archived)
        log = STATE / "transfer.log"
        if log.is_file():
            os.replace(log, STATE / ("transfer-terminated-" + old["id"] + ".log"))
        volume.commit()

    aosp = Path("/mnt/source/aosp17")
    manifest = Path("/mnt/source/AndariumRed/.build/Kernarium/android/lineage-24/metadata/base-manifest.xml")
    assert (aosp / ".repo/manifest.xml").exists(), "Existing source checkout missing"
    assert hashlib.sha256(manifest.read_bytes()).hexdigest() == MANIFEST_SHA256
    print("ORIGINAL_PINNED_SOURCE_CONFIRMED", flush=True)

    sb = modal.Sandbox.create(
        "bash", "-lc", COPY_SCRIPT,
        app=app, image=image,
        volumes={"/mnt/source": volume},
        cpu=2, memory=4096, timeout=79200
    )
    _write_json(STATE / "sandbox.json", {"id": sb.object_id, "status": "independent_copy"})
    volume.commit()
    print("INDEPENDENT_COPY_SANDBOX_STARTED", sb.object_id, flush=True)
    print("GH_RUNNER_CAN_EXIT_WITHOUT_TERMINATING_COPY", flush=True)
    sb.detach()


@app.function(image=image, timeout=300, volumes={"/mnt/source": volume})
def inspect_snapshot_copy():
    if _read_json(STATE / "snapshot_verified.json"):
        print("SNAPSHOT_ALREADY_VERIFIED", flush=True)
        return
    record = _read_json(STATE / "sandbox.json")
    if not record:
        print("NO_ACTIVE_COPY_RECORDED", flush=True)
        return
    sb = modal.Sandbox.from_id(record["id"])
    code = sb.poll()
    print("SOURCE_SANDBOX", record["id"], "EXIT", code, flush=True)
    if code is None:
        print("COPY_COMPLETE", _inspect(sb), flush=True)
    print("TRANSFER_LOG_TAIL_BEGIN\n" + _last_log() + "\nTRANSFER_LOG_TAIL_END", flush=True)


@app.function(image=image, timeout=14400, cpu=0.5, memory=512,
              volumes={"/mnt/source": volume})
def finalize_snapshot_copy():
    if _read_json(STATE / "snapshot_verified.json"):
        print("ANDROID17_SNAPSHOT_ALREADY_VERIFIED", flush=True)
        return
    if _read_json(STATE / "snapshot_finalize_error.json"):
        print("FINALIZATION_BLOCKED_PENDING_REVIEW", flush=True)
        return

    record = _read_json(STATE / "sandbox.json")
    if not record:
        print("NO_COPY_SANDBOX_YET", flush=True)
        return

    sb = modal.Sandbox.from_id(record["id"])
    code = sb.poll()
    if code is not None:
        print("COPY_SANDBOX_TERMINATED", code, flush=True)
        print("TRANSFER_LOG_TAIL_BEGIN\n" + _last_log() + "\nTRANSFER_LOG_TAIL_END", flush=True)
        raise RuntimeError("Source Sandbox exited before snapshot could be verified")

    if not _inspect(sb):
        print("COPY_STILL_IN_PROGRESS", record["id"], flush=True)
        print("TRANSFER_LOG_TAIL_BEGIN\n" + _last_log() + "\nTRANSFER_LOG_TAIL_END", flush=True)
        return

    print("SOURCE_COPY_PIN_VERIFIED_READY_FOR_SNAPSHOT", flush=True)
    restored = None
    try:
        created = _read_json(STATE / "snapshot_created.json")
        if created:
            sid = created["image_id"]
            snapshot = modal.Image.from_id(sid)
            print("REUSING_PREVIOUS_SNAPSHOT", sid, flush=True)
        else:
            print("CREATING_DIRECTORY_SNAPSHOT", flush=True)
            snapshot = sb.snapshot_directory("/work/aosp17", timeout=7200, ttl=None)
            sid = snapshot.object_id
            _write_json(STATE / "snapshot_created.json", {"image_id": sid})
            volume.commit()
            print("SNAPSHOT_IMAGE_ID", sid, flush=True)

        restored = modal.Sandbox.create(
            "sleep", "infinity", app=app,
            image=image, cpu=1, memory=2048, timeout=900
        )
        restored.mount_image("/work/aosp17", snapshot)
        check = restored.exec(
            "bash", "-lc",
            'test -e /work/aosp17/.repo/manifest.xml && '
            'test "$(git -C /work/aosp17/external/zlib rev-parse HEAD)" = '
            + ZLIB_SHA
        )
        assert check.wait() == 0, "Restored source snapshot did not pass sanity check"

        _write_json(STATE / "snapshot_verified.json", {
            "image_id": sid, "manifest_projects_verified_before_snapshot": 1239,
            "restore_sample_verified": "external/zlib"
        })
        volume.commit()
        print("ANDROID17_SANDBOX_SNAPSHOT_VERIFIED", sid, flush=True)
        try:
            sb.terminate()
            print("SOURCE_SANDBOX_CLEANED_UP", flush=True)
        except Exception as error:
            print("SOURCE_SANDBOX_CLEANUP_WARNING", repr(error), flush=True)
    except Exception as error:
        print("SNAPSHOT_FINALIZATION_ERROR", repr(error), flush=True)
        _write_json(STATE / "snapshot_finalize_error.json", {
            "error": repr(error), "sandbox_id": record["id"]
        })
        volume.commit()
        raise
    finally:
        if restored is not None:
            try:
                restored.terminate()
            except Exception:
                pass
