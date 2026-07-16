#!/usr/bin/env python3
"""Offline tests for delivery_state.py."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).with_name("delivery_state.py")


def run(args: list[str], env: dict[str, str], ok: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, env=env)
    if ok and result.returncode:
        raise AssertionError(result.stderr or result.stdout)
    if not ok and result.returncode == 0:
        raise AssertionError("command unexpectedly succeeded")
    return result


with tempfile.TemporaryDirectory(prefix="delivery-state-") as temp:
    root = Path(temp)
    repo = root / "repo"
    home = root / "home"
    repo.mkdir()
    home.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.invalid"], check=True)
    (repo / "file.txt").write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "file.txt"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "base"], check=True)
    commit = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"], text=True).strip()
    env = {**os.environ, "USERPROFILE": str(home), "HOME": str(home)}

    created = run(["init", "--repo", str(repo), "--bugs", "1001,1002", "--delivery", "test", "--release-requested"], env)
    state_path = Path(created.stdout.strip())
    assert state_path.exists()
    run(["advance", "--repo", str(repo), "--delivery", "test", "--bug", "1001", "--stage", "verified", "--evidence", "bad order"], env, ok=False)
    for stage in ["deep_fetched", "diagnosed", "fixed", "verified"]:
        run(["advance", "--repo", str(repo), "--delivery", "test", "--bug", "1001", "--stage", stage, "--evidence", stage], env)
    run(["advance", "--repo", str(repo), "--delivery", "test", "--bug", "1001", "--stage", "committed", "--evidence", "commit", "--commit", commit], env)
    for stage in ["memory_decided", "zentao_resolved"]:
        run(["advance", "--repo", str(repo), "--delivery", "test", "--bug", "1001", "--stage", stage, "--evidence", stage], env)
    run(["release", "--repo", str(repo), "--delivery", "test", "--status", "released", "--evidence", "upload"], env, ok=False)
    data = json.loads(state_path.read_text(encoding="utf-8"))
    assert data["bugs"]["1001"]["stage"] == "zentao_resolved"
    assert data["bugs"]["1001"]["commit"] == commit

print("delivery state tests passed")
