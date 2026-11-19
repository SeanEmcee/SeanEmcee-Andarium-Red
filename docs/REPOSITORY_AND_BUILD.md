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
