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
    env = {**os.environ, "USERPROFILE": str(home), "HOME": str(home)}
    note = home / "fix-pattern.md"
    note.write_text("# synthetic fix\n", encoding="utf-8")

    created = run(["init", "--repo", str(repo), "--bugs", "1001,1002", "--delivery", "test", "--release-requested"], env)
    state_path = Path(created.stdout.strip())
    assert state_path.exists()
    initial = json.loads(state_path.read_text(encoding="utf-8"))
    assert initial["schema_version"] == 3
    assert initial["active_bug"] == "1001"
    assert initial["terminal_stage"] == "zentao_resolved"
    blocked_second = run([
        "advance", "--repo", str(repo), "--delivery", "test", "--bug", "1002",
        "--stage", "deep_fetched", "--evidence", "must stay isolated",
    ], env, ok=False)
    assert "Only the active Bug may advance" in (blocked_second.stderr + blocked_second.stdout)
    run(["advance", "--repo", str(repo), "--delivery", "test", "--bug", "1001", "--stage", "verified", "--evidence", "bad order"], env, ok=False)
    for stage in ["deep_fetched", "diagnosed", "fixed", "verified"]:
        run(["advance", "--repo", str(repo), "--delivery", "test", "--bug", "1001", "--stage", stage, "--evidence", stage], env)
    (repo / "file.txt").write_text("bug 1001\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "file.txt"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "bug 1001"], check=True)
    commit_1001 = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    run([
        "advance", "--repo", str(repo), "--delivery", "test", "--bug", "1001",
        "--stage", "committed", "--evidence", "commit", "--commit", commit_1001,
    ], env)
    run([
        "advance", "--repo", str(repo), "--delivery", "test", "--bug", "1001",
        "--stage", "memory_decided", "--evidence", "recorded", "--fix-id", "FP-TEST",
        "--memory-note", str(note), "--target-id", "target-test",
    ], env)
    run(["advance", "--repo", str(repo), "--delivery", "test", "--bug", "1001", "--stage", "zentao_resolved", "--evidence", "resolved"], env)
    repeated = run(["advance", "--repo", str(repo), "--delivery", "test", "--bug", "1001", "--stage", "zentao_resolved", "--evidence", "resolved"], env)
    assert "Already completed" in repeated.stdout
    run(["release", "--repo", str(repo), "--delivery", "test", "--status", "released", "--evidence", "upload"], env, ok=False)
    data = json.loads(state_path.read_text(encoding="utf-8"))
    assert data["bugs"]["1001"]["stage"] == "zentao_resolved"
    assert data["bugs"]["1001"]["commit"] == commit_1001
    assert data["bugs"]["1001"]["memory"]["fix_id"] == "FP-TEST"
    assert data["active_bug"] == "1002"
    assert data["expected_head"] == commit_1001
    assert data["completed_receipts"][0]["bug"] == "1001"

    (repo / "file.txt").write_text("unexpected external change\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "file.txt"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "external"], check=True)
    changed_head = run([
        "advance", "--repo", str(repo), "--delivery", "test", "--bug", "1002",
        "--stage", "deep_fetched", "--evidence", "start",
    ], env, ok=False)
    assert "HEAD changed before Bug 1002" in (changed_head.stderr + changed_head.stdout)

    fast_created = run([
        "init", "--repo", str(repo), "--bugs", "2001", "--delivery", "fast",
        "--release-requested", "--terminal-stage", "memory_decided",
    ], env)
    fast_path = Path(fast_created.stdout.strip())
    for stage in ["deep_fetched", "diagnosed", "fixed", "verified"]:
        run(["advance", "--repo", str(repo), "--delivery", "fast", "--bug", "2001", "--stage", stage, "--evidence", stage], env)
    (repo / "file.txt").write_text("bug 2001\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "file.txt"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "bug 2001"], check=True)
    commit_2001 = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    run([
        "advance", "--repo", str(repo), "--delivery", "fast", "--bug", "2001",
        "--stage", "committed", "--evidence", "commit", "--commit", commit_2001,
    ], env)
    run([
        "advance", "--repo", str(repo), "--delivery", "fast", "--bug", "2001",
        "--stage", "memory_decided", "--evidence", "recorded", "--fix-id", "FP-FAST",
        "--memory-note", str(note), "--target-id", "target-fast",
    ], env)
    fast_data = json.loads(fast_path.read_text(encoding="utf-8"))
    assert fast_data["active_bug"] == ""
    assert fast_data["completed_receipts"][0]["verification"] == "verified"
    beyond_terminal = run([
        "advance", "--repo", str(repo), "--delivery", "fast", "--bug", "2001",
        "--stage", "zentao_resolved", "--evidence", "not requested",
    ], env, ok=False)
    assert "All bugs already reached" in (beyond_terminal.stderr + beyond_terminal.stdout)
    released = run([
        "release", "--repo", str(repo), "--delivery", "fast", "--status", "released",
        "--evidence", "single final controller",
    ], env)
    assert "release=released" in released.stdout

    legacy_path = state_path.parent / "legacy.json"
    legacy = {
        "schema_version": 1,
        "delivery_id": "legacy",
        "repo": str(repo.resolve()),
        "repo_name": repo.name,
        "branch": "master",
        "base_commit": commit_2001[:7],
        "dirty": "",
        "created_at": "test",
        "updated_at": "test",
        "release": {"requested": False, "status": "not_requested", "evidence": ""},
        "bug_order": ["3001"],
        "bugs": {
            "3001": {
                "stage": "pending", "completed": [], "evidence": {}, "commit": "",
                "memory": {"fix_id": "", "note": "", "target_id": ""},
            }
        },
    }
    legacy_path.write_text(json.dumps(legacy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    legacy_status = run(["status", "--repo", str(repo), "--delivery", "legacy"], env)
    assert "active_bug=3001 terminal_stage=zentao_resolved" in legacy_status.stdout

    outcome_created = run([
        "init", "--repo", str(repo), "--bugs", "4001,4002,4003", "--delivery", "outcomes",
        "--release-requested", "--terminal-stage", "memory_decided",
    ], env)
    outcome_path = Path(outcome_created.stdout.strip())
    for bug, outcome in (("4001", "already_fixed"), ("4002", "no_change"), ("4003", "external")):
        finish = ["finish", "--repo", str(repo), "--delivery", "outcomes", "--bug", bug, "--outcome", outcome, "--evidence", "named current source evidence"]
        run(finish, env, ok=False)
        for stage in ("deep_fetched", "diagnosed"):
            run(["advance", "--repo", str(repo), "--delivery", "outcomes", "--bug", bug, "--stage", stage, "--evidence", "checked"], env)
        run([*finish[:-1], " "], env, ok=False)
        run(finish, env)
        run(finish, env)
    outcomes = json.loads(outcome_path.read_text(encoding="utf-8"))
    assert outcomes["active_bug"] == "" and len(outcomes["completed_receipts"]) == 3
    assert all(not row["commit"] and not row["verification"] for row in outcomes["completed_receipts"])
    assert subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip() == commit_2001
    run(["release", "--repo", str(repo), "--delivery", "outcomes", "--status", "released", "--evidence", "owner receipt"], env)
    for stage in ("deep_fetched", "diagnosed"):
        run(["advance", "--repo", str(repo), "--delivery", "legacy", "--bug", "3001", "--stage", stage, "--evidence", "checked"], env)
    required_resolution = ["finish", "--repo", str(repo), "--delivery", "legacy", "--bug", "3001", "--outcome", "external", "--evidence", "platform receipt"]
    blocked = run(required_resolution, env, ok=False)
    assert "resolution-evidence" in blocked.stderr
    run([*required_resolution, "--resolution-evidence", "authorized resolver final-status receipt"], env)
    assert json.loads(legacy_path.read_text(encoding="utf-8"))["schema_version"] == 3

print("delivery state tests passed")
