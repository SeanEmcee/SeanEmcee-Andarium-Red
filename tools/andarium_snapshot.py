import json
import modal
from pathlib import Path

app = modal.App("andarium-red-snapshot")
volume = modal.Volume.from_name("andarium-red-cache")
image = modal.Image.debian_slim(python_version="3.11").apt_install(
    "git", "git-lfs", "rsync", "ca-certificates"
)

COPY_SCRIPT = r"""
set -Eeuo pipefail
LOGDIR=/mnt/source/andarium-snapshot
mkdir -p "$LOGDIR" /work/aosp17
exec > "$LOGDIR/transfer.log" 2>&1
trap 'code=$?; echo "TRANSFER_FAILED exit=$code"; exit "$code"' ERR
echo "SOURCE_COPY_STARTED $(date -u)"
df -h /work
rsync -a --no-owner --no-group --stats --exclude='/out/' \
  /mnt/source/aosp17/ /work/aosp17/
echo "SOURCE_COPY_COMPLETE $(date -u)"
python3 - <<'CHECK'
from pathlib import Path
import hashlib, subprocess, xml.etree.ElementTree as ET
root = Path("/work/aosp17").resolve()
manifest = Path("/mnt/source/AndariumRed/.build/Kernarium/android/lineage-24/metadata/base-manifest.xml")
expected = "23b230a34a672b664c6f7e7d1d69b3aa503339acc2330471a4bcf2be3020c6dc"
assert hashlib.sha256(manifest.read_bytes()).hexdigest() == expected
pins = {}
for p in ET.parse(manifest).getroot().iter("project"):
    path = p.get("path") or p.get("name")
    commit = p.get("revision", "")
    assert path and len(commit) == 40 and path not in pins
    pins[path] = commit
assert len(pins) == 1239
for n, (path, commit) in enumerate(pins.items(), 1):
    target = root / path
    got = subprocess.check_output(
        ["git", "-C", str(target), "rev-parse", "HEAD"], text=True, timeout=120
    ).strip()
    assert got == commit, (path, got, commit)
    gitdir = Path(subprocess.check_output(
        ["git", "-C", str(target), "rev-parse", "--absolute-git-dir"],
        text=True, timeout=120
    ).strip()).resolve()
    assert gitdir.is_relative_to(root), (path, gitdir)
    if n % 100 == 0:
        print("VERIFIED_GIT_PROJECTS", n, flush=True)
print("ALL_1239_PINNED_GIT_REVISIONS_VERIFIED", flush=True)
assert (root / ".repo/manifest.xml").exists()
CHECK
echo "SOURCE_COPY_AND_PINS_VERIFIED $(date -u)"
"""

@app.function(image=image, timeout=300, volumes={"/mnt/source": volume})
def snapshot_sdk_probe():
    import modal as active_modal
    import sys
    print("REMOTE_PYTHON", sys.version.split()[0], flush=True)
    print("REMOTE_MODAL", getattr(active_modal, "__version__", "unknown"), flush=True)
    assert hasattr(active_modal.Sandbox, "snapshot_directory")
    sandbox = active_modal.Sandbox.create(
        "true", app=app, image=image, cpu=1, memory=512, timeout=120
    )
    try:
        result = sandbox.wait()
        assert result == 0, result
        print("SNAPSHOT_SDK_AND_SANDBOX_PROBE_PASSED", flush=True)
    finally:
        sandbox.terminate()

@app.function(image=image, timeout=84000, cpu=0.5, memory=512,
              volumes={"/mnt/source": volume})
def snapshot_all_sources():
    import modal as active_modal
    if not hasattr(active_modal.Sandbox, "snapshot_directory"):
        raise RuntimeError("Remote SDK does not implement directory snapshots")

    state = Path("/mnt/source/andarium-snapshot")
    state.mkdir(exist_ok=True)
    if (state / "snapshot_verified.json").exists():
        print("SNAPSHOT_ALREADY_VERIFIED; no new snapshot created", flush=True)
        return
    if (state / "sandbox.json").exists():
        raise RuntimeError("Prior sandbox state exists. Inspect before retrying; do not duplicate billing.")
    if not Path("/mnt/source/aosp17/.repo/manifest.xml").exists():
        raise RuntimeError("Pinned Android source workspace missing")

    sb = active_modal.Sandbox.create(
        "sleep", "infinity", app=app, image=image,
        volumes={"/mnt/source": volume},
        cpu=2, memory=4096, timeout=79200
    )
    (state / "sandbox.json").write_text(json.dumps({"id": sb.object_id}) + "\n")
    volume.commit()
    print("SANDBOX_ID", sb.object_id, flush=True)

    restored = None
    try:
        process = sb.exec("bash", "-lc", COPY_SCRIPT)
        print("COPY_STARTED; see andarium-snapshot/transfer.log", flush=True)
        process.wait()
        if process.returncode != 0:
            raise RuntimeError("Source transfer or pin check failed; inspect transfer.log")

        print("LOCAL_1239_SOURCE_COPY_VERIFIED", flush=True)
        print("CREATING_DIRECTORY_SNAPSHOT", flush=True)
        snapshot = sb.snapshot_directory("/work/aosp17", timeout=7200, ttl=None)
        sid = snapshot.object_id
        (state / "snapshot_created.json").write_text(
            json.dumps({"image_id": sid}) + "\n"
        )
        volume.commit()
        print("SNAPSHOT_IMAGE_ID", sid, flush=True)

        restored = active_modal.Sandbox.create(
            "sleep", "infinity", app=app, image=image, cpu=1, memory=2048,
            timeout=900
        )
        restored.mount_image("/work/aosp17", snapshot)
        verify = restored.exec(
            "bash", "-lc",
            'test -f /work/aosp17/.repo/manifest.xml && '
            'test "$(git -C /work/aosp17/external/zlib rev-parse HEAD)" = '
            '8731e6760935ad5289fd64c37d28155a0fa289e3'
        )
        verify.wait()
        if verify.returncode != 0:
            raise RuntimeError("Snapshot restore check failed; image ID saved")

        (state / "snapshot_verified.json").write_text(json.dumps({
            "image_id": sid, "manifest_projects": 1239
        }, indent=2) + "\n")
        volume.commit()
        print("ANDROID17_SANDBOX_SNAPSHOT_VERIFIED", sid, flush=True)
    except Exception as error:
        print("SNAPSHOT_ERROR", repr(error), flush=True)
        raise
    finally:
        if restored is not None:
            try:
                restored.terminate()
            except Exception:
                pass
        try:
            sb.terminate()
        except Exception:
            pass
