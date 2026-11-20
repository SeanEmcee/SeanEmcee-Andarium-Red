# Soong memory recovery — 2026-11-20

The failing run [44722292922](https://github.com/SeanEmcee/SeanEmcee-Andarium-Red/actions/runs/44722292922)
finished source verification and cached the pinned Git object subset, but
the guest build was terminated at the final Soong bootstrap step.

At 12:21 UTC host RAM was almost entirely used and the full 9 GiB swap
was exhausted. Soong/Ninja commands show `env -i "$BUILDER"`,
which discards the workflow's inherited GOMEMLIMIT, GOGC and GOMAXPROCS.
Therefore a job-level Go heap cap alone was not effective.

The updated GitHub-hosted build temporarily replaces *only the disposable
runner's* /usr/bin/env with a transparent, versioned wrapper for the
specific `env -i .../host/linux-x86/bin/soong_build` subprocess.
It delegates all other env invocations to an untouched original binary.
The wrapper injects GOMEMLIMIT=8GiB, GOGC=25 and GOMAXPROCS=2,
logs an explicit invocation marker and Go GC diagnostics.
After the compile step it restores /usr/bin/env.

This was verified by independent smoke test
[44749851635](https://github.com/SeanEmcee/SeanEmcee-Andarium-Red/actions/runs/44749851635).
The test checks that a fake Soong process receives the Go runtime env
despite `env -i` and that unrelated env invocations are unchanged.
This validates the mechanism, **not yet its success with the full AOSP tree**.

# The source checkpoint prepares 1,239 pinned Android Repo projects.
# Four fetch jobs use the hosted four-vCPU runner for parallel I/O, while
# actual Soong/Ninja compilation remains at --jobs 1 with a 8GiB Go limit.

Existing kernels, accessibility and 3.06GB Git-object caches are reused.
The portable cache is also available in the public GitHub Release at
https://github.com/SeanEmcee/SeanEmcee-Andarium-Red/releases/tag/andarium-aosp17-git-object-cache-20261120

No unverified image, Magisk privilege, iPhone boot or IPA completion
should be claimed. If the hosted runner still cannot complete the
Android build, use a larger Linux runner with persistent storage.
