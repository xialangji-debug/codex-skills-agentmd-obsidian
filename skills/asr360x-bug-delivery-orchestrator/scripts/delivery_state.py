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
TERMINAL_STAGES = ["memory_decided", "zentao_resolved"]
NO_CHANGE_OUTCOMES = ["already_fixed", "no_change", "external"]


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


def resolve_repo(repo_arg: str) -> Path:
    repo = Path(repo_arg).resolve()
    return Path(git(repo, "rev-parse", "--show-toplevel")).resolve()


def repo_context(repo_arg: str) -> dict[str, str]:
    root = resolve_repo(repo_arg)
    return {
        "repo": str(root),
        "repo_name": root.name,
        "branch": git(root, "branch", "--show-current") or "detached",
        "base_commit": git(root, "rev-parse", "--short", "HEAD"),
        "dirty": git(root, "status", "--short"),
    }


def repo_key(repo: str) -> str:
    return hashlib.sha256(os.path.normcase(repo).encode("utf-8")).hexdigest()[:16]


def state_dir(repo: Path) -> Path:
    return ROOT / repo_key(str(repo))


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


def latest_state(repo: Path, delivery: str | None) -> tuple[Path, dict]:
    directory = state_dir(repo)
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


def stage_reached(current: str, target: str) -> bool:
    if current == "finished":
        return target in TERMINAL_STAGES
    if current == "pending":
        return False
    return STAGES.index(current) >= STAGES.index(target)


def terminal_stage(data: dict) -> str:
    value = data.get("terminal_stage", "zentao_resolved")
    if value not in TERMINAL_STAGES:
        raise SystemExit(f"Invalid terminal stage in delivery state: {value}")
    return value


def active_bug(data: dict) -> str:
    terminal = terminal_stage(data)
    recorded = data.get("active_bug", "")
    if recorded and recorded in data["bugs"] and not stage_reached(data["bugs"][recorded]["stage"], terminal):
        return recorded
    for bug in data["bug_order"]:
        if not stage_reached(data["bugs"][bug]["stage"], terminal):
            return bug
    return ""


def head_matches_expected(repo: Path, expected: str) -> bool:
    live = git(repo, "rev-parse", "HEAD")
    return bool(expected) and (live.startswith(expected) or expected.startswith(live))


def command_init(args: argparse.Namespace) -> None:
    context = repo_context(args.repo)
    repo = Path(context["repo"])
    bugs = parse_bugs(args.bugs)
    stamp = dt.datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    delivery_id = args.delivery or f"{stamp}_{'-'.join(bugs)}"
    path = state_dir(repo) / f"{delivery_id}.json"
    if path.exists():
        raise SystemExit(f"Delivery already exists: {path}")
    data = {
        "schema_version": 3,
        "delivery_id": delivery_id,
        **context,
        "created_at": now(),
        "updated_at": now(),
        "terminal_stage": args.terminal_stage,
        "active_bug": bugs[0],
        "expected_head": context["base_commit"],
        "completed_receipts": [],
        "release": {
            "requested": bool(args.release_requested),
            "status": "pending" if args.release_requested else "not_requested",
            "evidence": "",
        },
        "bug_order": bugs,
        "bugs": {
            bug: {
                "stage": "pending",
                "completed": [],
                "evidence": {},
                "commit": "",
                "memory": {"fix_id": "", "note": "", "target_id": ""},
            }
            for bug in bugs
        },
    }
    atomic_write(path, data)
    print(path)


def command_status(args: argparse.Namespace) -> None:
    repo = resolve_repo(args.repo)
    path, data = latest_state(repo, args.delivery)
    print(f"delivery={data['delivery_id']}")
    print(f"repo={data['repo']}")
    print(f"branch={data['branch']} base_commit={data['base_commit']}")
    print(
        f"active_bug={active_bug(data) or '-'} terminal_stage={terminal_stage(data)} "
        f"expected_head={data.get('expected_head') or data.get('base_commit') or '-'}"
    )
    for bug in data["bug_order"]:
        item = data["bugs"][bug]
        print(f"bug={bug} stage={item['stage']} outcome={item.get('outcome') or '-'} commit={item.get('commit') or '-'}")
    release = data["release"]
    print(f"release={release['status']} requested={release['requested']}")
    print(f"state={path}")


def command_advance(args: argparse.Namespace) -> None:
    repo = resolve_repo(args.repo)
    path, data = latest_state(repo, args.delivery)
    if args.bug not in data["bugs"]:
        raise SystemExit(f"Bug {args.bug} is not part of delivery {data['delivery_id']}")
    target_index = STAGES.index(args.stage)
    item = data["bugs"][args.bug]
    if item["stage"] == args.stage:
        print(f"Already completed: bug={args.bug} stage={args.stage}")
        return
    current_active = active_bug(data)
    if not current_active:
        raise SystemExit("All bugs already reached the configured terminal stage")
    if args.bug != current_active:
        raise SystemExit(f"Only the active Bug may advance: active={current_active} requested={args.bug}")
    terminal = terminal_stage(data)
    if target_index > STAGES.index(terminal):
        raise SystemExit(f"Stage {args.stage} is beyond configured terminal stage {terminal}")
    expected = STAGES[target_index - 1] if target_index else "pending"
    if item["stage"] != expected:
        raise SystemExit(f"Invalid transition: current={item['stage']} expected={expected} target={args.stage}")
    if item["stage"] == "pending":
        expected_head = data.get("expected_head") or data.get("base_commit", "")
        if not head_matches_expected(repo, expected_head):
            live_head = git(repo, "rev-parse", "--short", "HEAD")
            raise SystemExit(f"HEAD changed before Bug {args.bug}: expected={expected_head} live={live_head}")
    if not args.evidence.strip():
        raise SystemExit("--evidence is required for every transition")
    if args.stage == "committed" and not args.commit:
        raise SystemExit("--commit is required for committed stage")
    if args.stage == "memory_decided":
        if not args.fix_id or not args.memory_note:
            raise SystemExit("--fix-id and --memory-note are required for memory_decided")
        note = Path(args.memory_note).expanduser().resolve()
        if not note.is_file() or note.suffix.lower() != ".md":
            raise SystemExit(f"Fix-pattern note not found: {note}")
        item["memory"] = {
            "fix_id": args.fix_id.strip(),
            "note": str(note),
            "target_id": args.target_id.strip(),
        }
    if args.commit:
        commit_full = git(repo, "rev-parse", "--verify", f"{args.commit}^{{commit}}")
        live_head = git(repo, "rev-parse", "HEAD")
        if commit_full != live_head:
            raise SystemExit(f"Committed stage must record current HEAD: commit={commit_full} head={live_head}")
        item["commit"] = args.commit
        data["expected_head"] = live_head
    item["completed"].append(args.stage)
    item["stage"] = args.stage
    item["evidence"][args.stage] = args.evidence.strip()
    if args.stage == terminal:
        receipt = {
            "bug": args.bug,
            "commit": item.get("commit", ""),
            "verification": item.get("evidence", {}).get("verified", ""),
            "fix_id": item.get("memory", {}).get("fix_id", ""),
            "target_id": item.get("memory", {}).get("target_id", ""),
            "completed_at": now(),
        }
        receipts = data.setdefault("completed_receipts", [])
        receipts[:] = [existing for existing in receipts if existing.get("bug") != args.bug]
        receipts.append(receipt)
        data["active_bug"] = active_bug({**data, "active_bug": ""})
    data["updated_at"] = now()
    atomic_write(path, data)
    print(f"advanced bug={args.bug} stage={args.stage}")
    print(f"active_bug={active_bug(data) or '-'}")
    print(path)


def command_finish(args: argparse.Namespace) -> None:
    repo = resolve_repo(args.repo)
    path, data = latest_state(repo, args.delivery)
    item = data["bugs"].get(args.bug)
    if item is None:
        raise SystemExit(f"Bug {args.bug} is not part of this delivery")
    if item["stage"] == "finished":
        if item.get("outcome") != args.outcome:
            raise SystemExit("A finished Bug cannot be silently reclassified")
        print(f"Already finished: bug={args.bug} outcome={args.outcome}")
        return
    if args.bug != active_bug(data) or item["stage"] != "diagnosed":
        raise SystemExit("Only the active diagnosed Bug may finish without a code change")
    if not args.evidence.strip():
        raise SystemExit("--evidence is required for the diagnosed outcome")
    if terminal_stage(data) == "zentao_resolved" and not args.resolution_evidence.strip():
        raise SystemExit("This delivery requires --resolution-evidence from the authorized resolver")
    expected_head = data.get("expected_head") or data.get("base_commit", "")
    if not head_matches_expected(repo, expected_head) or (git(repo, "branch", "--show-current") or "detached") != data["branch"]:
        raise SystemExit("Checkout changed before the no-change outcome was recorded")
    item["stage"] = "finished"
    item["outcome"] = args.outcome
    item["evidence"]["outcome"] = args.evidence.strip()
    item["evidence"]["resolution"] = args.resolution_evidence.strip()
    item["completed"].append("finished")
    data.setdefault("completed_receipts", []).append({
        "bug": args.bug, "outcome": args.outcome, "commit": "", "verification": "",
        "evidence": args.evidence.strip(), "resolution_evidence": args.resolution_evidence.strip(),
        "completed_at": now(),
    })
    if data.get("schema_version", 1) < 3:
        print(f"schema_upgraded={data.get('schema_version', 1)}->3 for explicit finish")
        data["schema_version"] = 3
    data["active_bug"] = active_bug({**data, "active_bug": ""})
    data["updated_at"] = now()
    atomic_write(path, data)
    print(f"finished bug={args.bug} outcome={args.outcome} active_bug={active_bug(data) or '-'}")


def command_release(args: argparse.Namespace) -> None:
    repo = resolve_repo(args.repo)
    path, data = latest_state(repo, args.delivery)
    if not data["release"]["requested"]:
        raise SystemExit("Release was not explicitly requested when this delivery was initialized")
    terminal = terminal_stage(data)
    if any(not stage_reached(data["bugs"][bug]["stage"], terminal) for bug in data["bug_order"]):
        raise SystemExit(f"All bugs must reach {terminal} before release")
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
    init.add_argument(
        "--terminal-stage",
        choices=TERMINAL_STAGES,
        default="zentao_resolved",
        help="Per-Bug completion stage; use memory_decided when Zentao resolution was not requested",
    )
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
    advance.add_argument("--fix-id", default="")
    advance.add_argument("--memory-note", default="")
    advance.add_argument("--target-id", default="")
    advance.set_defaults(func=command_advance)
    finish = sub.add_parser("finish", help="Record a diagnosed outcome requiring no new code change")
    finish.add_argument("--repo", default=".")
    finish.add_argument("--delivery")
    finish.add_argument("--bug", required=True)
    finish.add_argument("--outcome", required=True, choices=NO_CHANGE_OUTCOMES)
    finish.add_argument("--evidence", required=True)
    finish.add_argument("--resolution-evidence", default="")
    finish.set_defaults(func=command_finish)
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
