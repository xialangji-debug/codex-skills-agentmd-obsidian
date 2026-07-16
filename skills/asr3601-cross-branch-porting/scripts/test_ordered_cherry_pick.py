#!/usr/bin/env python3
"""Offline smoke test for ordered_cherry_pick.py."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).with_name("ordered_cherry_pick.py")


with tempfile.TemporaryDirectory(prefix="ordered-cherry-pick-") as temp:
    repo = Path(temp) / "repo"
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.invalid"], check=True)
    (repo / "base.txt").write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "base"], check=True)
    base = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    subprocess.run(["git", "-C", str(repo), "switch", "-q", "-c", "source"], check=True)
    (repo / "one.txt").write_text("one\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "one"], check=True)
    one = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    (repo / "two.txt").write_text("two\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "two"], check=True)
    two = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    subprocess.run(["git", "-C", str(repo), "switch", "-q", "main"], check=True)
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--repo", str(repo), "--start-point", base, "--new-branch", "integrated", "--commits", f"{one},{two}", "--apply"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert (repo / "one.txt").exists() and (repo / "two.txt").exists()
    assert subprocess.check_output(["git", "-C", str(repo), "branch", "--show-current"], text=True).strip() == "integrated"

print("ordered cherry-pick tests passed")
