#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Fast comprehensive source/build contract checks before 1200-project AOSP sync.
# Does not claim Android image, iOS IPA, or device compatibility is verified.
set -euo pipefail
cd "$(dirname "$0")/.."
echo 'CHECKPOINT=python_syntax'
python3 -B - <<'PY'
import pathlib
for folder in ('scripts', 'tests', 'tools'):
    for item in pathlib.Path(folder).rglob('*.py'):
        compile(item.read_bytes(), str(item), 'exec')
for filename in ('install_source_overlay.py','integrate_andarium.py',
                 'red_runtime_overlay.py','host_firstboot.py'):
    item=pathlib.Path(filename)
    compile(item.read_bytes(),str(item),'exec')
print('PASS: all Python files parse')
PY
echo 'CHECKPOINT=bash_syntax'
while IFS= read -r -d '' item; do
    bash -n "$item"
done < <(find scripts -type f -name '*.sh' -print0)
bash -n scripts/android17_soong_env_wrapper
echo 'PASS: all shell scripts parse'
echo 'CHECKPOINT=android_manifests_resources_and_blueprints'
python3 -B - <<'PY'
from pathlib import Path
import re
import xml.etree.ElementTree as ET
for root in ('launcher_src','guest_clipboard'):
    for xml in Path(root).rglob('*.xml'):
        ET.parse(xml)
        print('PARSED_XML='+str(xml))
bp=(Path('guest_clipboard')/'Android.bp').read_text()
assert 'name: "TwoyiRedClipboard"' in bp
assert re.search(r'\bsdk_version:\s*"system_current"',bp)
assert not re.search(r'(?m)^\s*platform_apis:\s*true',bp)
assert 'product_specific: true' in bp
assert 'certificate: "platform"' in bp
print('PASS: Android XML and product SDK properties')
PY
echo 'CHECKPOINT=guest_java_compile'
bash scripts/preflight_android_guest_java.sh
echo 'CHECKPOINT=reversible_soong_host_memory'
python3 -B scripts/test_soong_host_runtime_patch.py
echo 'CHECKPOINT=reversible_vendor_verifier_order'
python3 -B scripts/test_verified_soong_driver.py
echo 'CHECKPOINT=pinned_repo_sync_recovery'
python3 -B scripts/test_verified_repo_sync_driver.py
echo 'CHECKPOINT=source_checkpoint'
python3 -B scripts/test_android17_source_checkpoint.py
echo 'CHECKPOINT=clipboard_policy'
python3 -B tests/test_guest_clipboard_soong_sdk.py
echo 'CHECKPOINT=full_source_test_suite'
python3 -B -m unittest discover -s tests -p 'test_*.py' -v
echo 'PASS: all locally reproducible host, Java, XML, Blueprint and source tests'
