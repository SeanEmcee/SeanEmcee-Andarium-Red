# Andarium Red first-build handoff (v15)

**Current private repository:** SeanEmcee/SeanEmcee-Andarium-Red. Branch: feature/andd-memory-tuning. No need to create or publicize a new repository. **GitHub Actions are intentionally not used.**

This repository is a *source overlay*, not the full Kernarium host tree, accepted Android image, Apple runtime XCFrameworks or a signed IPA. It does not contain proprietary APKs, signing credentials, or prebuilt guest binaries.

## Exact source basis

Upstream: imxieyi/Kernarium at **fbe12ee72d195f0241c4fc24090a98b259026604**. Review integration on this revision; the script rejects a different real Git revision rather than attempting to patch unknown APIs. Xcode 27 is required to read the current JSON xcproj project. iOS RAM entitlement declarations are upstream, but successful signing depends on Apple's effective code-signing profile.

## First-build sequence (macOS and configured dependencies)

```sh
# Clone the upstream and use the exact reviewed revision:
git clone https://github.com/imxieyi/Kernarium.git
cd Kernarium
git checkout --detach fbe12ee72d195f0241c4fc24090a98b259026604
cd ..

# From the Andarium Red private source checkout:
bash scripts/first_build.sh /absolute/path/to/Kernarium
bash scripts/first_build.sh /absolute/path/to/Kernarium --build
```

The first command applies and tests the host/guest source overlays without compiling a runtime. The second additionally packages the iOS runtime, stages an already accepted Android release and asks Xcode to attempt a **non-signed Release compile**, not a device install. If accepted image/runtime artifacts or Mac/Xcode are missing, the workflow exits with the failing prerequisite. Do not mark it green from source checks alone.

The native Android Red launcher, privileged clipboard provider and any root integration need a *new* Android 17 image built on an appropriate Android build machine, then staged via upstream's unsigned-proof procedure for development. An upstream release image will not contain the modified guest modules. Actual signed-device tests, Magisk-managed root, AOT performance and full parity remain separate gates.

## Checks

```sh
python3 -m unittest discover -s tests -q
python3 tools/first_build_gate.py --kernarium /absolute/path/to/Kernarium
python3 tools/first_build_gate.py --kernarium /absolute/path/to/Kernarium --require-artifacts
```

The gate checks the real Swift ANDD value code and its test harness, display/memory patch anchors, reviewed checkout revision, entitlement declarations, Xcode target folder membership, Python regressions, and staged binaries when required. The scripts do not use or trigger GitHub Actions and do not claim the application has passed a device build.

---

# Repository handoff without GitHub Actions

Preferred GitHub destination: **private** `SeanEmcee/Andarium-Red`.

The installed Universal GitHub Bridge's current `create_repository` operation uses its GitHub Actions request handler. That path is **not allowed** while the owner forbids GitHub Actions. The connected GitHub integration supports file and commit changes to an existing repository but **not** native `create_repository`. A browser can create the private repository after account sign-in. No public repository is required.

Once the empty private repository exists, import **all source files at the root** (not the containing folder), excluding any signing certificates, credentials, IPAs or proprietary APKs. The provided package contains none of those binaries. Do not enable GitHub Actions workflows.

For local checks on a machine with Python 3, Java JDK and Swift (for Swift tests only):

```sh
python3 -m unittest discover -s tests -q
python3 tools/native_home_stub_compile.py
python3 tools/android_panel_stub_compile.py
python3 tools/clipboard_provider_behavior_test.py
python3 tools/root_probe_java_test.py
python3 tools/accent_store_behavior_test.py
python3 tools/prebuild_parity.py --report PREBUILD_PARITY.json
```

Do not treat these as Android 17 Soong builds, Xcode archives, runtime validation, or a proof that `LiveContainer` can run this app. A real signed iOS build still requires a compatible host framework, authorized iOS signing/entitlements and an Android 17 guest boot test.
