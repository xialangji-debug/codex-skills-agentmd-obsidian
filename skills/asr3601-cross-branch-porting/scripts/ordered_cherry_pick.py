#!/usr/bin/env python3
"""Plan or perform an ordered cherry-pick integration with conflict-stop."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
from pathlib import Path


def run(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and result.returncode:
        raise SystemExit(result.stderr.strip() or result.stdout.strip() or f"git {' '.join(args)} failed")
    return result


def output(repo: Path, *args: str) -> str:
    return run(repo, *args).stdout.strip()


def parse_commits(value: str) -> list[str]:
    commits = []
    for item in re.split(r"[,，\s]+", value.strip()):
        if item and item not in commits:
            commits.append(item)
    if not commits:
        raise SystemExit("--commits must contain at least one commit")
    return commits


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--start-point", required=True)
    parser.add_argument("--new-branch", required=True)
    parser.add_argument("--commits", required=True)
    parser.add_argument("--backup-branch")
    parser.add_argument("--fetch", action="store_true", help="Run git fetch origin before verification")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    repo = Path(output(Path(args.repo).resolve(), "rev-parse", "--show-toplevel")).resolve()
    dirty = output(repo, "status", "--porcelain")
    if dirty:
        raise SystemExit("Worktree is not clean; preserve or commit existing changes before integration")
    if args.fetch:
        if not args.apply:
            raise SystemExit("--fetch changes remote refs and therefore requires --apply")
        run(repo, "fetch", "origin")

    current_branch = output(repo, "branch", "--show-current") or "detached"
    original_head = output(repo, "rev-parse", "HEAD")
    run(repo, "rev-parse", "--verify", f"{args.start_point}^{{commit}}")
    if run(repo, "show-ref", "--verify", "--quiet", f"refs/heads/{args.new_branch}", check=False).returncode == 0:
        raise SystemExit(f"Target branch already exists: {args.new_branch}")

    commits = parse_commits(args.commits)
    resolved = []
    for commit in commits:
        resolved.append(output(repo, "rev-parse", "--verify", f"{commit}^{{commit}}"))

    stamp = dt.datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    safe_current = re.sub(r"[^A-Za-z0-9._-]+", "-", current_branch).strip("-") or "detached"
    backup = args.backup_branch or f"backup/{safe_current}-{stamp}"
    plan = {
        "repo": str(repo),
        "current_branch": current_branch,
        "original_head": original_head,
        "backup_branch": backup,
        "start_point": args.start_point,
        "new_branch": args.new_branch,
        "commits": resolved,
        "apply": args.apply,
    }
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    if not args.apply:
        return 0

    run(repo, "branch", backup, original_head)
    run(repo, "switch", "-c", args.new_branch, args.start_point)
    completed = []
    for commit in resolved:
        result = run(repo, "cherry-pick", commit, check=False)
        if result.returncode:
            conflicts = output(repo, "diff", "--name-only", "--diff-filter=U")
            state = {
                **plan,
                "status": "conflict",
                "completed": completed,
                "failed_commit": commit,
                "conflicts": conflicts.splitlines() if conflicts else [],
            }
            state_path = Path(output(repo, "rev-parse", "--git-dir")) / "codex-integration-state.json"
            if not state_path.is_absolute():
                state_path = repo / state_path
            state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(state, ensure_ascii=False, indent=2))
            print(f"state={state_path}")
            return 2
        completed.append(commit)

    print(f"completed={len(completed)}")
    print(f"branch={args.new_branch}")
    print(f"backup={backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
