"""Finalize the pinned Android source snapshot from the GitHub-hosted Modal client.

The source Sandbox belongs to a detached App, so Sandbox.from_id() must be
called from the authenticated host rather than an unrelated Modal Function.
No new source copying. Stop the original Sandbox only after verified restore.
"""
import io
import json

import modal

PREFIX = "andarium-snapshot/"
VOLUME_NAME = "andarium-red-cache"
ZLIB_SHA = "8731e6760935ad5289fd64c37d28155a0fa289e3"


def maybe_read(vol, name):
    try:
        return b"".join(vol.read_file(PREFIX + name)).decode("utf-8", "replace")
    except FileNotFoundError:
        return None


def save_json(vol, name, value):
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    with vol.batch_upload(force=True) as batch:
        batch.put_file(io.BytesIO(payload), "/" + PREFIX + name)


def main():
    volume = modal.Volume.from_name(VOLUME_NAME)
    if maybe_read(volume, "snapshot_verified.json"):
        print("ANDROID17_SNAPSHOT_ALREADY_VERIFIED", flush=True)
        return

    previous_error = maybe_read(volume, "snapshot_finalize_error.json")
    if previous_error:
        print("FINALIZATION_BLOCKED_PENDING_REVIEW", previous_error[:1500], flush=True)
        return

    state_raw = maybe_read(volume, "sandbox.json")
    if not state_raw:
        print("NO_SOURCE_COPY_SANDBOX_RECORDED", flush=True)
        return
    sandbox_id = json.loads(state_raw)["id"]
    sandbox = modal.Sandbox.from_id(sandbox_id)
    exit_code = sandbox.poll()
    print("COPY_SANDBOX", sandbox_id, "EXIT", exit_code, flush=True)
    if exit_code is not None:
        print("SOURCE_COPY_SANDBOX_STOPPED; don't create a duplicate", flush=True)
        raise RuntimeError("Original copy Sandbox is no longer running")

    ready = sandbox.exec("sh", "-c", "test -f /work/.andarium-copy-verified")
    if ready.wait() != 0:
        print("COPY_STILL_IN_PROGRESS; snapshot deferred", flush=True)
        return
    print("ALL_1239_SOURCE_PINS_CONFIRMED_FROM_COPY_MARKER", flush=True)

    snapshot = None
    previous_snapshot = maybe_read(volume, "snapshot_created.json")
    if previous_snapshot:
        sid = json.loads(previous_snapshot)["image_id"]
        snapshot = modal.Image.from_id(sid)
        print("REUSING_SNAPSHOT_IMAGE", sid, flush=True)
    else:
        print("CREATING_DIRECTORY_SNAPSHOT", flush=True)
        snapshot = sandbox.snapshot_directory(
            "/work/aosp17", timeout=7200, ttl=None
        )
        sid = snapshot.object_id
        save_json(volume, "snapshot_created.json", {"image_id": sid})
        print("DURABLE_SNAPSHOT_IMAGE_ID", sid, flush=True)

    restored = None
    try:
        host_app = modal.App.lookup(
            "andarium-red-snapshot-validation", create_if_missing=True
        )
        validator_image = modal.Image.debian_slim(
            python_version="3.11"
        ).apt_install("git", "ca-certificates")
        validator_image.build(app=host_app)
        restored = modal.Sandbox.create(
            "sleep", "infinity",
            app=host_app,
            image=validator_image,
            cpu=1, memory=2048, timeout=900
        )
        restored.mount_image("/work/aosp17", snapshot)
        result = restored.exec(
            "bash", "-lc",
            'test -e /work/aosp17/.repo/manifest.xml && '
            'test "$(git -C /work/aosp17/external/zlib rev-parse HEAD)" = '
            + ZLIB_SHA
        )
        assert result.wait() == 0, "Restored snapshot verification failed"

        save_json(volume, "snapshot_verified.json", {
            "image_id": sid,
            "manifest_projects_verified_before_snapshot": 1239,
            "restore_sample_verified": "external/zlib",
        })
        print("ANDROID17_SANDBOX_SNAPSHOT_VERIFIED", sid, flush=True)
        try:
            sandbox.terminate()
            print("SOURCE_SANDBOX_STOPPED_AFTER_VERIFICATION", flush=True)
        except Exception as exc:
            print("SOURCE_SANDBOX_CLEANUP_WARNING", repr(exc), flush=True)
    except Exception as exc:
        print("SNAPSHOT_FINALIZATION_ERROR", repr(exc), flush=True)
        save_json(volume, "snapshot_finalize_error.json", {
            "error": repr(exc),
            "sandbox_id": sandbox_id,
            "snapshot_created": bool(snapshot),
        })
        raise
    finally:
        if restored is not None:
            try:
                restored.terminate()
            except Exception as exc:
                print("RESTORE_SANDBOX_CLEANUP_WARNING", repr(exc), flush=True)


if __name__ == "__main__":
    main()
