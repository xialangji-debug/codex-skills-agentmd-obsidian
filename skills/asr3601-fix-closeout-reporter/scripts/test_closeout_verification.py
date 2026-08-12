#!/usr/bin/env python3
"""Offline regression tests for integrated ASR360x verification."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PREFLIGHT = SCRIPT_DIR / "lvgl_i18n_preflight.py"
CLOSEOUT = SCRIPT_DIR / "closeout_snapshot.py"


def load_preflight():
    spec = importlib.util.spec_from_file_location("lvgl_i18n_preflight", PREFLIGHT)
    if spec is None or spec.loader is None:
        raise AssertionError("cannot load lvgl_i18n_preflight.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


preflight = load_preflight()
sample = ['lv_label_set_text(label, "中文");']
assert not any(
    finding.rule == "hardcoded-cjk"
    for finding in preflight.text_findings("sample.c", sample, "unspecified")
), "unspecified locale must not assume a non-Chinese project"
assert any(
    finding.rule == "hardcoded-cjk"
    for finding in preflight.text_findings("sample.c", sample, "vi")
), "an explicitly selected non-Chinese locale should enable the hard-coded CJK check"

with tempfile.TemporaryDirectory(prefix="closeout-staged-diff-") as temp:
    repo = Path(temp)
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "test@example.invalid"],
        check=True,
    )
    source = repo / "sample.c"
    source.write_text("int value = 0;\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "sample.c"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "base"], check=True)
    source.write_text("int value = 1;  \n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "sample.c"], check=True)

    result = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            str(CLOSEOUT),
            "--repo",
            str(repo),
            "--skip-i18n-preflight",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    assert result.returncode != 0, "staged whitespace error must fail verification"
    assert "git diff --cached --check (exit" in result.stdout
    assert "trailing whitespace" in result.stdout

print("closeout verification tests passed")
