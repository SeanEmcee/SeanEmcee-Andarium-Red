#!/usr/bin/env python3
"""Offline, safe test of bounded compiler diagnostics and redaction."""
import importlib.util
from pathlib import Path
import tempfile
spec=importlib.util.spec_from_file_location("telemetry",Path(__file__).with_name("android17_build_telemetry.py"))
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
with tempfile.TemporaryDirectory() as tmp:
    p=Path(tmp)
    (p/"resource-samples.log").write_text("Swap: 9215 9120 95\n")
    (p/"andarium-build-complete.log").write_text(
        "a"*16000+"\nerror: clipboard module issue\n"
        "GITHUB_TOKEN=ghp_ABCDEFGHIJKLMNOPQRSTABCDEFGHIJKLMNOPQRST\n")
    out=module.summary(p,"test")
    assert "Swap: 9215 9120 95" in out
    assert "error: clipboard module issue" in out
    assert "ghp_" not in out
    assert len(out)<10000
print("PASS: bounded telemetry, redaction, resource metrics and error preservation")
