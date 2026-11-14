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
        if delivery in {".", ".."} or any(char in delivery for char in "/\\:"):
            raise SystemExit("--delivery must be a delivery ID, not a path")
        path = directory / f"{delivery}.json"
    else:
        candidates = sorted(directory.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
        if not candidates:
            raise SystemExit("No delivery state found; run init first")
        path = candidates[0]
    if not path.exists():
        raise SystemExit(f"Delivery state not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if os.path.normcase(str(Path(data["repo"]).resolve())) != os.path.normcase(str(repo.resolve())):
        raise SystemExit("Delivery state belongs to another repository")
    return path, data


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


def require_checkout(repo: Path, data: dict, *, check_head: bool = True) -> None:
    branch = git(repo, "branch", "--show-current") or "detached"
    if branch != data["branch"]:
        raise SystemExit(f"Branch changed: expected={data['branch']} live={branch}")
    expected = data.get("expected_head") or data.get("base_commit", "")
    if check_head and not head_matches_expected(repo, expected):
        raise SystemExit(f"HEAD changed before Bug {active_bug(data) or '-'}: expected={expected} live={git(repo, 'rev-parse', '--short', 'HEAD')}")


def require_running(data: dict) -> None:
    if data.get("stopped", False):
        raise SystemExit("Delivery continuation was stopped by a scope change; read status and use the latest request")


def command_init(args: argparse.Namespace) -> None:
    context = repo_context(args.repo)
    repo = Path(context["repo"])
    bugs = parse_bugs(args.bugs)
    stamp = dt.datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    delivery_id = args.delivery or f"{stamp}_{'-'.join(bugs)}"
    if delivery_id in {".", ".."} or any(char in delivery_id for char in "/\\:"):
        raise SystemExit("--delivery must be a delivery ID, not a path")
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
    print(f"continuation={'stopped' if data.get('stopped', False) else 'active'}")
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
    require_running(data)
    require_checkout(repo, data, check_head=args.stage != "committed")
    if args.commit and args.stage != "committed":
        raise SystemExit("--commit may be recorded only at the committed stage")
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
        expected = data.get("expected_head") or data.get("base_commit", "")
        previous = git(repo, "rev-parse", "--verify", f"{expected}^{{commit}}")
        if commit_full == previous or git(repo, "merge-base", previous, commit_full) != previous:
            raise SystemExit("Committed stage requires a new commit descending from the recorded expected HEAD")
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
    require_running(data)
    require_checkout(repo, data)
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
    require_running(data)
    # The owner already checked checkout identity and may have committed its
    # release header. Record its exact receipt without repeating source gates.
    if data["release"]["status"] == "released":
        if args.status != "released" or args.evidence.strip() != data["release"]["evidence"]:
            raise SystemExit("A completed release and its receipt cannot be rewritten")
        print("Already recorded: release=released")
        return
    if not data["release"]["requested"]:
        raise SystemExit("Release is not part of the current recorded scope")
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


def command_narrow(args: argparse.Namespace) -> None:
    """Withdraw pending work without erasing completed actions or receipts."""
    repo = resolve_repo(args.repo)
    path, data = latest_state(repo, args.delivery)
    if not args.evidence.strip():
        raise SystemExit("--evidence must describe the latest user scope change")
    if not (args.cancel_release or args.no_zentao or args.stop):
        raise SystemExit("Select --cancel-release, --no-zentao, or --stop")
    changes = {}
    if args.cancel_release and data["release"]["requested"]:
        previous_release = dict(data["release"])
        data["release"]["requested"] = False
        # A previous successful publication remains a fact. Preserve any failure
        # receipt too; only an unperformed release changes to cancelled.
        if data["release"]["status"] != "released":
            data["release"]["status"] = "cancelled"
        changes["release"] = {"before": previous_release, "after": dict(data["release"])}
    if args.no_zentao and terminal_stage(data) != "memory_decided":
        changes["terminal_stage"] = {"before": terminal_stage(data), "after": "memory_decided"}
        data["terminal_stage"] = "memory_decided"
        receipts = data.setdefault("completed_receipts", [])
        for bug in data["bug_order"]:
            item = data["bugs"][bug]
            if stage_reached(item["stage"], "memory_decided") and not any(row.get("bug") == bug for row in receipts):
                receipts.append({
                    "bug": bug, "commit": item.get("commit", ""),
                    "verification": item.get("evidence", {}).get("verified", ""),
                    "fix_id": item.get("memory", {}).get("fix_id", ""),
                    "target_id": item.get("memory", {}).get("target_id", ""),
                    "completed_at": now(), "completion_reason": "scope_narrowed",
                })
        data["active_bug"] = active_bug({**data, "active_bug": ""})
    if args.stop and not data.get("stopped", False):
        changes["stopped"] = {"before": False, "after": True}
        data["stopped"] = True
    if not changes:
        print("Recorded scope is already as narrow as requested")
        return
    data["schema_version"] = max(4, data.get("schema_version", 1))
    data.setdefault("scope_changes", []).append({"at": now(), "evidence": args.evidence.strip(), "changes": changes})
    data["updated_at"] = now()
    atomic_write(path, data)
    print(f"scope narrowed: {', '.join(changes)}")
    print(path)


def command_resume(args: argparse.Namespace) -> None:
    """Resume the retained narrower scope after an explicit continuation request."""
    repo = resolve_repo(args.repo)
    path, data = latest_state(repo, args.delivery)
    if not args.evidence.strip():
        raise SystemExit("--evidence must describe the user's explicit continuation request")
    require_checkout(repo, data)
    if not data.get("stopped", False):
        print("Delivery continuation is already active")
        return
    data["stopped"] = False
    data.setdefault("scope_changes", []).append({
        "at": now(), "evidence": args.evidence.strip(),
        "changes": {"stopped": {"before": True, "after": False}},
    })
    data["updated_at"] = now()
    atomic_write(path, data)
    print("Delivery resumed; withdrawn release/resolution scope remains withdrawn")
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
        default="memory_decided",
        help="Per-Bug completion stage; zentao_resolved requires explicit resolution scope",
    )
    init.set_defaults(func=command_init)
    status = sub.add_parser("status")
    status.add_argument("--repo", default=".")
    status.add_argument("--delivery")
    status.set_defaults(func=command_status)
    advance = sub.add_parser("advance")
    advance.add_argument("--repo", default=".")
    advance.add_argument("--delivery", required=True)
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
    finish.add_argument("--delivery", required=True)
    finish.add_argument("--bug", required=True)
    finish.add_argument("--outcome", required=True, choices=NO_CHANGE_OUTCOMES)
    finish.add_argument("--evidence", required=True)
    finish.add_argument("--resolution-evidence", default="")
    finish.set_defaults(func=command_finish)
    release = sub.add_parser("release")
    release.add_argument("--repo", default=".")
    release.add_argument("--delivery", required=True)
    release.add_argument("--status", choices=["pending", "released", "blocked"], required=True)
    release.add_argument("--evidence", default="")
    release.set_defaults(func=command_release)
    narrow = sub.add_parser("narrow", help="Withdraw pending stages under the latest user request")
    narrow.add_argument("--repo", default=".")
    narrow.add_argument("--delivery", required=True)
    narrow.add_argument("--cancel-release", action="store_true")
    narrow.add_argument("--no-zentao", action="store_true")
    narrow.add_argument("--stop", action="store_true", help="Stop this plan's continuation; keep all stage evidence")
    narrow.add_argument("--evidence", required=True)
    narrow.set_defaults(func=command_narrow)
    resume = sub.add_parser("resume", help="Explicitly resume the retained scope of a stopped plan")
    resume.add_argument("--repo", default=".")
    resume.add_argument("--delivery", required=True)
    resume.add_argument("--evidence", required=True)
    resume.set_defaults(func=command_resume)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
