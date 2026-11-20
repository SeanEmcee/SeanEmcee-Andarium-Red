# Andarium Red portable Git source-object cache

This independent free GitHub Actions workflow retrieves the source-object
cache saved before the previous Soong failure and publishes checksum-verified
chunks as a GitHub Release. Each chunk is below GitHub's 2 GB single-asset
limit. The archive contains public Git object stores only, NOT the whole
100+ GiB Android checkout, a Soong build output, an IPA, or a bootable VM.

To restore in an alternate Linux CI service: download all
`andarium-source-seed.part-*` files and `SHA256SUMS`, run
`sha256sum -c SHA256SUMS`, then on a Btrfs source workspace run
`cat andarium-source-seed.part-* | zstd -dc | tar -xf - -C "$AOSP_WORKSPACE"`.
Run `scripts/prepare_pinned_repo_seed.py restore` with the
`--workspace "$AOSP_WORKSPACE" --cache "$AOSP_WORKSPACE/.andarium-repo-seed"`
arguments, followed by normal pinned Repo sync and upstream verification.

Blacksmith offers a 3,000-minute free monthly allowance without a credit
card, and an OSS sponsorship program, but ongoing unlimited free compute
requires approval. Andarium Red currently has no LICENSE or established
open-source community; do not assume sponsorship eligibility.
