#!/usr/bin/env python3
"""Maintain resumable local state for ASR360x bug delivery workflows."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
from pathlib import Path


ROOT = Path.home() / ".codex" / "asr360x-delivery" / "states"
STAGES = [
    "deep_fetched",
    "diagnosed",
    "fixed",
    "verified",
    "committed",
    "memory_decided",
    "zentao_resolved",
]


def now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode:
        raise SystemExit(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def repo_context(repo_arg: str) -> dict[str, str]:
    repo = Path(repo_arg).resolve()
    root = Path(git(repo, "rev-parse", "--show-toplevel")).resolve()
    return {
        "repo": str(root),
        "repo_name": root.name,
        "branch": git(root, "branch", "--show-current") or "detached",
        "base_commit": git(root, "rev-parse", "--short", "HEAD"),
        "dirty": git(root, "status", "--short"),
    }


def repo_key(repo: str) -> str:
    return hashlib.sha256(os.path.normcase(repo).encode("utf-8")).hexdigest()[:16]


def state_dir(context: dict[str, str]) -> Path:
    return ROOT / repo_key(context["repo"])


def parse_bugs(value: str) -> list[str]:
    bugs = []
    for raw in value.replace("，", ",").split(","):
        bug = raw.strip().lstrip("#")
        if bug and bug not in bugs:
            bugs.append(bug)
    if not bugs:
        raise SystemExit("--bugs must contain at least one bug ID")
    return bugs


def atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def latest_state(context: dict[str, str], delivery: str | None) -> tuple[Path, dict]:
    directory = state_dir(context)
    if delivery:
        path = directory / f"{delivery}.json"
    else:
        candidates = sorted(directory.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
        if not candidates:
            raise SystemExit("No delivery state found; run init first")
        path = candidates[0]
    if not path.exists():
        raise SystemExit(f"Delivery state not found: {path}")
    return path, json.loads(path.read_text(encoding="utf-8"))


def command_init(args: argparse.Namespace) -> None:
    context = repo_context(args.repo)
    bugs = parse_bugs(args.bugs)
    stamp = dt.datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    delivery_id = args.delivery or f"{stamp}_{'-'.join(bugs)}"
    path = state_dir(context) / f"{delivery_id}.json"
    if path.exists():
        raise SystemExit(f"Delivery already exists: {path}")
    data = {
        "schema_version": 1,
        "delivery_id": delivery_id,
        **context,
        "created_at": now(),
        "updated_at": now(),
        "release": {
            "requested": bool(args.release_requested),
            "status": "pending" if args.release_requested else "not_requested",
            "evidence": "",
        },
        "bug_order": bugs,
        "bugs": {
            bug: {"stage": "pending", "completed": [], "evidence": {}, "commit": ""}
            for bug in bugs
        },
    }
    atomic_write(path, data)
    print(path)


def command_status(args: argparse.Namespace) -> None:
    context = repo_context(args.repo)
    path, data = latest_state(context, args.delivery)
    print(f"delivery={data['delivery_id']}")
    print(f"repo={data['repo']}")
    print(f"branch={data['branch']} base_commit={data['base_commit']}")
    for bug in data["bug_order"]:
        item = data["bugs"][bug]
        print(f"bug={bug} stage={item['stage']} commit={item.get('commit') or '-'}")
    release = data["release"]
    print(f"release={release['status']} requested={release['requested']}")
    print(f"state={path}")


def command_advance(args: argparse.Namespace) -> None:
    context = repo_context(args.repo)
    path, data = latest_state(context, args.delivery)
    if args.bug not in data["bugs"]:
        raise SystemExit(f"Bug {args.bug} is not part of delivery {data['delivery_id']}")
    target_index = STAGES.index(args.stage)
    item = data["bugs"][args.bug]
    expected = STAGES[target_index - 1] if target_index else "pending"
    if item["stage"] == args.stage:
        print(f"Already completed: bug={args.bug} stage={args.stage}")
        return
    if item["stage"] != expected:
        raise SystemExit(f"Invalid transition: current={item['stage']} expected={expected} target={args.stage}")
    if not args.evidence.strip():
        raise SystemExit("--evidence is required for every transition")
    if args.stage == "committed" and not args.commit:
        raise SystemExit("--commit is required for committed stage")
    if args.commit:
        git(Path(context["repo"]), "rev-parse", "--verify", f"{args.commit}^{{commit}}")
        item["commit"] = args.commit
    item["completed"].append(args.stage)
    item["stage"] = args.stage
    item["evidence"][args.stage] = args.evidence.strip()
    data["updated_at"] = now()
    atomic_write(path, data)
    print(f"advanced bug={args.bug} stage={args.stage}")
    print(path)


def command_release(args: argparse.Namespace) -> None:
    context = repo_context(args.repo)
    path, data = latest_state(context, args.delivery)
    if not data["release"]["requested"]:
        raise SystemExit("Release was not explicitly requested when this delivery was initialized")
    if any(data["bugs"][bug]["stage"] != "zentao_resolved" for bug in data["bug_order"]):
        raise SystemExit("All bugs must reach zentao_resolved before release")
    if args.status == "released" and not args.evidence.strip():
        raise SystemExit("--evidence is required when marking released")
    data["release"] = {
        "requested": True,
        "status": args.status,
        "evidence": args.evidence.strip(),
    }
    data["updated_at"] = now()
    atomic_write(path, data)
    print(f"release={args.status}")
    print(path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--repo", default=".")
    init.add_argument("--bugs", required=True)
    init.add_argument("--delivery")
    init.add_argument("--release-requested", action="store_true")
    init.set_defaults(func=command_init)
    status = sub.add_parser("status")
    status.add_argument("--repo", default=".")
    status.add_argument("--delivery")
    status.set_defaults(func=command_status)
    advance = sub.add_parser("advance")
    advance.add_argument("--repo", default=".")
    advance.add_argument("--delivery")
    advance.add_argument("--bug", required=True)
    advance.add_argument("--stage", required=True, choices=STAGES)
    advance.add_argument("--evidence", required=True)
    advance.add_argument("--commit")
    advance.set_defaults(func=command_advance)
    release = sub.add_parser("release")
    release.add_argument("--repo", default=".")
    release.add_argument("--delivery")
    release.add_argument("--status", choices=["pending", "released", "blocked"], required=True)
    release.add_argument("--evidence", default="")
    release.set_defaults(func=command_release)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
