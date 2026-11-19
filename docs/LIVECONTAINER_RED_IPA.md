# Andarium Red → LiveContainer: genuine Android 17 device test

## Which app

The **full `Andarium` target** must be compiled from the pinned Kernarium
base after this repository's `integrate_andarium.py` applies all host and
Android source overlays. That is **our modified Andarium Red**, not the
original unmodified app.

Never give LiveContainer the `AndariumPreview` simulator/mock target. Its UI
does not boot Android. Likewise, a compiler-smoke build of the full host that
stages upstream's accepted image does **not** prove the Red launcher, clipboard
provider or Android-side shortcuts were compiled into the guest.

## How Android 17 is installed

Andarium's current architecture bundles a **compiled Android 17 system image**
inside `Andarium.app/andarium-system`. The app then provisions a writable data
disk when a guest is created. It **does not currently install an arbitrary
downloaded ROM via an in-app Android-image picker**.

To build **our Android 17**, first use a sufficiently provisioned Linux builder
for the pinned source, compile `TwoyiRedLauncher` and `TwoyiRedClipboard` in
the Android target-files, assemble an Android 17 system disk, and create a
verified unsigned Red proof directory using
[`ANDROID17_PROOF_BUILD.md`](ANDROID17_PROOF_BUILD.md).
The Mac host must import the exact compatible accepted Android 4 KiB kernel
artifact and build verified Apple GPU and networking dependencies.

## GitHub pipeline

[Andarium first compile workflow](../.github/workflows/andarium-first-compile.yml)
on `feature/andd-memory-tuning`:

- `source`: real source contract tests only.
- `preview`: simulator UI compile, **no downloadable IPA**.
- `host-unsigned`: genuine full native host compiler smoke; may use the
  **upstream** accepted Android image and therefore **does not publish a Red IPA**.
- `red-ipa`: the only downloadable IPA route. Requires `guest_proof_run_id`
  naming a **completed GitHub Actions run in this same repo** that contains
  an artifact named `andarium-red-android17-proof`. The artifact must unpack
  directly to `release-manifest.json`, `guest/system.img`,
  `guest/partition-layout.json`, `boot/kernel-command-line.txt`.
  This is not yet produced by the cloud preview/host workflows.

The `red-ipa` job verifies the image provenance and disk SHA-256, embeds
the Red image with upstream's `stage-system-image.py --unsigned-proof`,
compiles the full `Andarium` iPhoneOS arm64 target, verifies the resulting
`Andarium.app` bundle and publishes
`AndariumRed-Android17-FullHost-Unsigned.ipa` as an Actions artifact.
It **never** renames a mock preview or upstream image to Red.

## LiveContainer reality check

The IPA is unsigned and still needs to be imported and signed by
LiveContainer's own supported certificate workflow. LiveContainer runs guest
apps with **the host's entitlements**; entitlements declared by the imported
Andarium app are **not automatically granted**. Andarium requires Metal 4,
high virtual-memory capacity, and a compatible execution environment;
a successful host compiler build or a successful IPA import **does not prove
Android 17 boots inside LiveContainer**.

Do not change or bypass iOS entitlements. Test real Android boot, root status,
APK installation, memory pressure, FPS and persistence separately. If
LiveContainer lacks required host capabilities, report the limitation rather
than claim support.

References:
- [LiveContainer signing and import documentation](https://livecontainer.github.io/docs/installation/standalone)
- [LiveContainer guest-entitlement limitations](https://github.com/LiveContainer/LiveContainer#limitations)
