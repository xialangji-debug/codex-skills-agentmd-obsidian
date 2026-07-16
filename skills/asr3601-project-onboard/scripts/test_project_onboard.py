#!/usr/bin/env python3
"""Offline smoke test for project onboarding and stale checks."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).with_name("project_onboard.py")


with tempfile.TemporaryDirectory(prefix="project-onboard-") as temp:
    repo = Path(temp) / "lt52_test"
    yl_dir = repo / "gui" / "lv_watch" / "lv_apps" / "yl"
    yl_dir.mkdir(parents=True)
    (yl_dir / "yl.h").write_text(
        '#define yl_device_name "LT52"\n#define yl_device_ver "LT52_TEST"\n#define yl_hw_ver "ASR3602"\n',
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "base"], check=True)
    write = subprocess.run([sys.executable, str(SCRIPT), "--repo", str(repo), "--write"], capture_output=True, text=True)
    assert write.returncode == 0, write.stderr or write.stdout
    for name in ["variant.md", "device.md", "memory.md"]:
        assert (repo / ".codex-project" / name).exists()
    check = subprocess.run([sys.executable, str(SCRIPT), "--repo", str(repo), "--check"], capture_output=True, text=True)
    assert check.returncode == 0, check.stderr or check.stdout
    (repo / "tracked.txt").write_text("next\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "tracked.txt"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "next"], check=True)
    stale = subprocess.run([sys.executable, str(SCRIPT), "--repo", str(repo), "--check"], capture_output=True, text=True)
    assert stale.returncode == 2
    assert "commit:" in stale.stdout and "status=stale" in stale.stdout

print("project onboard tests passed")
