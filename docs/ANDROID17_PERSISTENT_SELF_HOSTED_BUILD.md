# Persistent Andarium Red Android 17 builder

Full hosted run [44891057722](https://github.com/SeanEmcee/SeanEmcee-Andarium-Red/actions/runs/44891057722)
reached **49,371/226,728 Ninja tasks** before GitHub's hard six-hour
hosted-runner cutoff. At that point it had 104/110 GiB of its temporary
Android Btrfs workspace allocated (96%) and ~12 GiB free on the host disk.
The CPU/RAM snapshot did not show memory exhaustion; GitHub imposed
the execution limit. No valid Android image or IPA was produced.

GitHub free caches contain verified kernel, Kernarium, accessibility,
and a small pinned 3 GiB Git-object seed. They contain **no compiler
output or complete AOSP tree** and cannot resume the discarded 21%.

GitHub self-hosted Linux x64 Actions on this public repository can run
free on an authorized user's own machine, with up to 5 days per job.
The persistent Ubuntu filesystem keeps *both* complete pinned
`aosp17` and its Ninja `out/andarium-red-userdebug` between runs.
A second job on the *same commit* resumes the existing verified source
checkpoint and recompiles only stale/missing Ninja outputs.

## Host requirements

A Linux x86-64 filesystem (native ext4 or WSL2 Ubuntu's ext4, **not
`/mnt/c`**), adequate physical disk, and sufficient RAM/swap. Google
recommends **400 GB free and 64 GB RAM** for modern AOSP builds.
The project's preflight experimentally permits 300 GiB initial free
and 80 GiB headroom for resumption, with a minimum 16 GiB of visible
RAM; these lower values may still prove insufficient. The user's
machine should be checked before enrolling.

Install GitHub's Linux x64 self-hosted runner through repository
Settings → Actions → Runners → New self-hosted runner, and follow the
current GitHub-generated enrollment commands inside Ubuntu. Add the
custom label `andarium-aosp17`; do not share the generated token.
Install Linux dependencies such as `git`, `git-lfs`, `repo`, Python,
Java 17, `zip`, `unzip`, `jq`, `flock` and AOSP build essentials.
Set up WSL2 memory/swap appropriately if running under Windows.
Keep the WSL Linux VHDX on an SSD with ample actual host disk space.

The new workflow is `Andarium Red - persistent free self-hosted
Android 17`. It is **not triggered automatically** by the earlier
hosted build requests. Once the tagged runner is online, trigger it
from Actions on the branch `feature/andd-memory-tuning`, or push
`build-requests/persistent-android17-execute-<unique>.txt`.

The build will provision the unchanged pinned Kernarium and kernel
once, prepare and validate a source checkpoint, then compile using
`--use-prepared-source --jobs 2`. It never deletes the prior Ninja
`out` directory on failure. The exact Git commit, build number and
variant must match to reuse the source. If source files change, keep
the old workspace and create a separate working directory for the
new revision rather than mixing unverifiable outputs.

The complete image and Xcode IPA are **not built yet**. Self-hosted
compilation and artifact upload still require a live runner and
enough actual storage; the workflow is only prepared and tested.
