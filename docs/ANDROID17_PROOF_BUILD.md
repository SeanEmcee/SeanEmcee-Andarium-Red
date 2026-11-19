# Andarium Red — reproducible Android 17 proof build handoff

**State:** source and invocation plan verified against pinned upstream public
Kernarium interfaces at `fbe12ee72d195f0241c4fc24090a98b259026604`.
Actual Android/Soong source compilation and image production **not yet run**.
This is NOT a signed Google/Play image and NOT proof of Magisk-managed root.

## Two build environments are required

1. **x86_64 Linux** with a large Android build workspace, pinned Repo checkout,
   Git LFS, a verified upstream Android kernel artifact, and the tools specified
   in Kernarium's `android/lineage-24/README.md`. The Android 17 image producer
   is too large to replace with a mock APK ZIP.
2. **Mac with Xcode 27** to package the iOS guest runtime and host app. iOS
   code-signing, effective entitlements and a real iPhone are subsequent gates.

## Android producer steps

Set actual **absolute local paths**. The AOSP output directory must be inside
the AOSP Repo workspace. The kernel artifact must match upstream's accepted
Android 4 KiB kernel descriptor. Source files in Kernarium must first be
integrated using this project's `integrate_andarium.py`.

```sh
# First, on the machine with the pinned Kernarium/Andarium Red checkouts:
python3 integrate_andarium.py --kernarium /ABS/Kernarium --source . --dry-run
python3 integrate_andarium.py --kernarium /ABS/Kernarium --source .

# On an x86_64 Linux Android builder, with those integrated sources:
cd /ABS/Kernarium
android/lineage-24/build/prepare-sources.sh \
  --aosp-source /ABS/aosp17 --jobs 12
android/lineage-24/build/apply-aosp-patches.sh \
  --aosp-source /ABS/aosp17

android/lineage-24/build/build-aosp.sh \
  --aosp-source /ABS/aosp17 \
  --out /ABS/aosp17/out \
  --kernel-artifact /ABS/accepted-android-kernel-artifact \
  --build-number 1001 --jobs 12

android/lineage-24/build/assemble-image.sh \
  --target-files /ABS/aosp17/out/target/product/andarium/obj/PACKAGING/target_files_intermediates/lineage_andarium-target_files.zip \
  --kernel-artifact /ABS/accepted-android-kernel-artifact \
  --mkbootfs /ABS/aosp17/out/host/linux-x86/bin/mkbootfs \
  --mkbootimg /ABS/aosp17/out/host/linux-x86/bin/mkbootimg \
  --output-dir /ABS/red17-disk

# The final output is a developer-only proof release directory.
python3 /ABS/AndariumRed/tools/create_unsigned_proof.py \
  --kernarium /ABS/Kernarium \
  --target-files /ABS/aosp17/out/target/product/andarium/obj/PACKAGING/target_files_intermediates/lineage_andarium-target_files.zip \
  --disk-dir /ABS/red17-disk \
  --kernel-cmdline /ABS/known-good-kernel-command-line.txt \
  --output /ABS/red17-proof \
  --release-name red-v15-1001
```

The template `1001` and `12` are **examples**, not inferred build
identities or verified resource recommendations. The kernel command line must
come from a compatible, reviewed Android guest configuration; do not invent
boot switches. Locate the actual target-files archive emitted by Soong if
its output directory differs. The proof packager requires that the *compiled*
target-files contain both `TwoyiRedLauncher` and `TwoyiRedClipboard`, that
`SYSTEM/build.prop` identifies Android 17 with a real numeric build
number, and that the assembled GPT system disk matches its own SHA-256
partition layout. It refuses to overwrite existing output.

## iOS consumer of the proof (Mac)

```sh
cd /ABS/AndariumRed
bash scripts/first_build.sh /ABS/Kernarium --preview
bash scripts/first_build.sh /ABS/Kernarium --build \
  --with-apps --guest-proof /ABS/red17-proof
```

The Mac stage verifies the unsigned-proof release through Kernarium's own
`stage-system-image.py --unsigned-proof`, which rejects malformed or
incompatible images. A proof guest needs a fresh/isolated guest instance and
cannot be used for App Store/TestFlight release. The six pinned APK downloads
are optional, independently verified from publisher assets, and installed
during first boot by host ADB code rather than being included in the proof
image. The APK for Magisk **Manager is not the daemon or Magisk root**.

**Additional work before release:** prove a compatible Magisk init/root path
in a booted guest, accept any matching native AOT artifact, test clipboard
platform permissions and two-way transfer, validate APK/keyboard/Play
compatibility, link a genuine Nexaris engine driver, and collect iPhone FPS,
jetsam, heat, persistence and signing evidence. Do not claim those from a
successful proof package or Xcode compile.
