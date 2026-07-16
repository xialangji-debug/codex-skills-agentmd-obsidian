#!/usr/bin/env python3
"""Offline tests for memory_trust.py."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).with_name("memory_trust.py")


with tempfile.TemporaryDirectory(prefix="memory-trust-") as temp:
    root = Path(temp) / "fix-patterns"
    root.mkdir()
    note = root / "sample.md"
    note.write_text("# Sample\n\n## 元信息\n\n- 验证状态：未验证\n\n## 症状\n\n- sample\n", encoding="utf-8")
    verify = subprocess.run([sys.executable, str(SCRIPT), "verify", "--root", str(root), "--note", str(note), "--evidence", "device passed", "--write"], capture_output=True, text=True)
    assert verify.returncode == 0, verify.stderr
    text = note.read_text(encoding="utf-8")
    assert "验证状态：已验证" in text and "可信度：高" in text
    reactivate = subprocess.run([sys.executable, str(SCRIPT), "reactivate", "--root", str(root), "--note", str(note), "--bug", "1001", "--evidence", "tester reproduced", "--write"], capture_output=True, text=True)
    assert reactivate.returncode == 0, reactivate.stderr
    text = note.read_text(encoding="utf-8")
    assert "验证状态：待复核" in text and "复测激活 Bug：1001" in text

print("memory trust tests passed")
