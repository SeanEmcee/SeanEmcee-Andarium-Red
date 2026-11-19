# Andarium Red — accepted Android artifact availability, 2026-11-19

## Verified upstream source identities

The pinned and reviewed Kernarium commit
`fbe12ee72d195f0241c4fc24090a98b259026604` declares:

- Accepted LineageOS 24 (Android 17) release:
  `20261115-los24-r28`, directory
  `lineage24-mainline6.18-4k-20261115-los24-r28`.
  Source: `android/lineage-24/metadata/accepted-release.env`.
- Accepted 4 KiB Android kernel artifact:
  `20261119-6.18.60-ca1`, directory
  `android-6.18-arm64-4k-20261119-6.18.60-ca1`.
  Source: `kernel/mainline-6.18/artifacts/accepted-android-4k.env`.

The official public upstream GitHub release
[`1.0b15-release`](https://github.com/imxieyi/Kernarium/releases/tag/1.0b15-release)
publishes the r28 Android system archive
`lineage24-mainline6.18-4k-20261115-los24-r28.tar.gz` but its Android
kernel archive is `android-6.18-arm64-4k-20261117-6.18.60-vd2.tar.gz`
(**vd2**, not the current checkout's accepted **ca1** kernel). The published
r28 system archive SHA-256 is
`1c33d658dca10a5826d11958315ff9421724145a31d22fae1700a8e4e731f529`
as declared by the upstream GitHub release API. The vd2 kernel archive
SHA-256 is
`ec8fe146788cd6b16c2974a04a5b710220a43f11eeed3f61b663c4a3ee52af9b`.

## Build implications

These identities are not interchangeable. Do not bypass the accepted-release
or kernel-artifact verifier, edit the descriptor to pretend an old artifact
matches, fabricate a system image, or claim actual rooted Android guest boot.

An AndariumPreview Xcode compile needs neither artifact and has **passed**
in [public run #44635364654](https://github.com/SeanEmcee/SeanEmcee-Andarium-Red/actions/runs/44635364654).

A complete unsigned iOS host build needs the verified GPU/network/storage
frameworks **and** a release/image/kernel that satisfies the pinned
Kernarium's own artifact checks. A modified Red Android launcher and
clipboard provider additionally require a *newly compiled* Android 17
target-files/product image, not the stock upstream r28 archive.

Potential legitimate resolution: obtain a publisher-verified ca1 kernel
bundle that matches the pinned descriptor, or build and verify the exact
kernel from the accepted pinned source. The already-published vd2 bundle is
not an accepted replacement for ca1. Any future release acquisition must use
authentic hashes and the upstream verifiers; do not silently downgrade the
reviewed source or bypass the accepted artifact contract.

This document is a static factual audit, **not** proof that either archive was
downloaded, installed, or tested.
