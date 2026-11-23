"""Read-only Andarium source-copy status from GitHub's Modal API token.

Must run from the GitHub runner (not in a different ephemeral Modal Function).
No Android source writes, new Sandboxes, or billing-heavy operations.
"""
import json
import modal


def text_file(volume, name):
    return b"".join(volume.read_file(name)).decode("utf-8", "replace")


def main():
    volume = modal.Volume.from_name("andarium-red-cache")
    saved = json.loads(text_file(volume, "andarium-snapshot/sandbox.json"))
    sandbox_id = saved["id"]
    print("SOURCE_SANDBOX_ID", sandbox_id, flush=True)

    for name in ["snapshot_created.json", "snapshot_verified.json"]:
        try:
            print("SNAPSHOT_STATE", name, text_file(volume, "andarium-snapshot/" + name)[:500], flush=True)
        except FileNotFoundError:
            print("SNAPSHOT_STATE_NOT_PRESENT", name, flush=True)

    sandbox = modal.Sandbox.from_id(sandbox_id)
    status = sandbox.poll()
    print("SOURCE_SANDBOX_EXIT_CODE", status, flush=True)
    print("SOURCE_SANDBOX_ACTIVE", status is None, flush=True)
    if status is None:
        process = sandbox.exec(
            "sh", "-c",
            "test -f /work/.andarium-copy-verified"
        )
        complete = process.wait() == 0
        print("COPY_COMPLETE", complete, flush=True)
        if not complete:
            check = sandbox.exec(
                "sh", "-c",
                "pgrep -c -x rsync || true"
            )
            count = check.stdout.read().strip()
            print("ACTIVE_RSYNC_PROCESSES", count, flush=True)
    else:
        print("COPY_SANDBOX_STOPPED; inspect transfer log before retrying", flush=True)

    try:
        log = text_file(volume, "andarium-snapshot/transfer.log")
        print("TRANSFER_LOG_TAIL_BEGIN\n" + log[-2200:] + "\nTRANSFER_LOG_TAIL_END", flush=True)
    except FileNotFoundError:
        print("TRANSFER_LOG_NOT_VISIBLE", flush=True)


if __name__ == "__main__":
    main()
