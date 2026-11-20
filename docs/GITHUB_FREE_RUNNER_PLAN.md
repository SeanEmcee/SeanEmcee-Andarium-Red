# Free GitHub Actions feasibility and real Andarium Red build

The public repository has access to standard free GitHub Actions runners.
GitHub's 2026 documentation specifies 4 vCPUs, 16 GB RAM, and only 14 GB
SSD for ubuntu-24.04. LineageOS 24 / Android 17 source and Soong output
requires substantially more. CircleCI build 17 exhausted 145 GB
uncompressed disk; the compressed workspace got into Soong bootstrap
but build 21 timed out at its one-hour maximum.

## What the new workflow really does

1. Commits named build-requests/github-probe-*.txt with a commit message
   containing [github-probe] run a free GitHub x86_64 disk/RAM probe.
   It saves inspectable diagnostic evidence and skips Android source sync
   if the capacity cannot fit the real 150 GiB workspace. No fake IPA.
2. The full producer has the labels self-hosted, linux, x64, and
   andarium-aosp17. It is only triggered via an explicit GitHub request
   commit named build-requests/github-real-*.txt with message [github-real],
   or workflow_dispatch if the workflow becomes available on default branch.
   It will stay queued if that runner is not online: do not trigger it
   without provisioned hardware.
3. A compatible Linux x86_64 computer needs at least 150 GiB free,
   OpenJDK 17, git-lfs, repo, Python3, zip and unzip. A Windows 11 PC can
   use Ubuntu through WSL2 if it has sufficient free SSD and resources.
   Use elevated PowerShell: wsl --install -d Ubuntu-24.04.
   Register a GitHub Actions Linux x64 runner using the instructions
   under this repository's Settings > Actions > Runners and add the
   andarium-aosp17 custom label. Do not publish runner registration tokens.
4. This mode downloads the previously verified public ABI29 kernel,
   reruns Kernarium's independent original verifier, compiles the genuine
   pinned LineageOS 24 image and modified HOME/clipboard payload, then
   uploads the verified unsigned guest proof.
5. After the guest proof really succeeds, run the existing Xcode 27
   andarium-first-compile.yml phase red-ipa using its GitHub Actions run ID
   as guest_proof_run_id. That phase already rejects missing or unverified
   guest proof and must pass before claiming a full unsigned IPA.

Builds in separate ephemeral GitHub-hosted jobs cannot magically share
large Soong state. A persistent self-hosted workspace under
$HOME/andarium-red-aosp17 keeps downloaded Git objects between runs.
The existing original source and integrity checks remain mandatory.

GitHub cannot create an oversized cloud machine for free on demand.
This workflow makes that limitation explicit rather than promising an
unrealistic cloud-only build. No Nexaris source or jobs are involved.

## GitHub-hosted compressed build experiment

The live probe on run 44696453263 measured a real 145G root filesystem
with approximately 89G free, despite standard published runner specs.
A second, explicitly verified probe deletes only unrelated preinstalled
toolchains on a disposable hosted Ubuntu VM. If it recovers at least
122 GiB usable before the build, the compressed-source producer can be
triggered by an explicit commit under build-requests/github-hosted-*.txt
whose message contains [github-hosted]. The hosted build has a 360-minute
limit and uses the same verified kernel, pinned sources and source caches.
No full guest build is triggered before the capacity probe passes.

This experiment can still fail from insufficient storage or memory;
do not claim a working image or successful IPA until its real artifacts pass.


## Source-sync checkpoints after GitHub runner shutdown at Soong bootstrap

Run 44699590700 failed after a host shutdown signal, not a demonstrated
Soong compiler error. The Soong 99% display was only its bootstrap
296-step stage. Previously only Kernarium, the ABI29 kernel and the three
accessibility checkouts were cached; all AOSP Repo and Soong state was lost.

The hosted job now has an explicit source-preparation checkpoint **before**
the long Soong compilation. The original Kernarium accessibility, Mesa and
AOSP patch verifiers must all pass before it proceeds. An optional cache
captures up to 3 GiB apparent size of *selected bare Git object stores*,
copy-on-write within the compressed Btrfs workspace. Next run restores
those objects before the ordinary pinned Repo sync, which must still fetch
and verify everything missing. This does not cache 100+ GiB AOSP worktree
or the Soong intermediates, so it cannot guarantee a dramatic speedup.

The cache key is tied to the reviewed Kernarium SHA and pinned LineageOS 24
tag. GitHub's standard 10 GB total free repository cache allowance is
respected; exceeding it requires paid cache storage. Full AOSP caching
and incremental Soong compilations require a persistent adequately sized
runner rather than a disposable free hosted VM.

The hosted build also prints cgroup memory events, memory pressure and
disk usage every 45 seconds during Soong so an abrupt runner shutdown
has pre-stop diagnostics even when an after-failure action cannot execute.
