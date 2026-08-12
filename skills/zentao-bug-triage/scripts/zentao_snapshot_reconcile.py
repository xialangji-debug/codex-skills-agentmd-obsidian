#!/usr/bin/env python3
"""Reconcile current Zentao snapshots with exact-target local state."""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


DEFAULT_STATE_ROOT = Path.home() / ".codex" / "zentao-bug-triage" / "state"
FIX_MEMORY = Path.home() / ".codex" / "skills" / "obsidian-fix-pattern-memory" / "scripts" / "fix_memory.py"
SCHEMA_VERSION = 1
REPORT_START = "<!-- codex-zentao-reconcile:start -->"
REPORT_END = "<!-- codex-zentao-reconcile:end -->"


def now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def compact(value: Any) -> str:
    return " ".join(str(value or "").split())


def bug_display_label(bug_id: Any, title: Any) -> str:
    normalized_id = compact(bug_id).lstrip("#") or "ID未获取"
    normalized_title = compact(title) or "标题未获取"
    return f"{normalized_id.replace('|', '/')} {normalized_title.replace('|', '/')}"


def normalize_identity(value: str) -> str:
    return compact(value).replace("\\", "/").lower()


def digest(value: str, length: int) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()[:length]


def run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=8,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def repo_id(repo_value: str) -> str:
    repo = Path(repo_value).expanduser().resolve()
    remote = run_git(repo, "remote", "get-url", "origin")
    return digest(normalize_identity(remote or str(repo)), 12)


def normalize_status(value: Any) -> str:
    status = compact(value).lower()
    if status in {"active", "opened", "open", "激活", "激活中", "未解决"}:
        return "active"
    if status in {"resolved", "已解决", "解决"}:
        return "resolved"
    if status in {"closed", "已关闭", "关闭"}:
        return "closed"
    return "unknown"


def normalize_symptom(value: Any) -> str:
    text = str(value or "").lower()
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", text)


def symptom_parts(bug: dict[str, Any]) -> tuple[str, str]:
    title = normalize_symptom(bug.get("title"))
    latest = bug.get("lastActivation") or {}
    detail = normalize_symptom(
        " ".join(
            [
                compact(bug.get("actual")),
                compact(bug.get("expected")),
                compact(latest.get("note")),
            ]
        )
    )
    return title, detail


def same_symptom(previous: dict[str, Any], current: dict[str, Any]) -> bool:
    old_title = previous.get("title_fingerprint", "")
    old_detail = previous.get("detail_fingerprint", "")
    new_title, new_detail = symptom_parts(current)
    title_ratio = difflib.SequenceMatcher(None, old_title, new_title).ratio() if old_title and new_title else 0.0
    if title_ratio < 0.85:
        return False
    if not old_detail or not new_detail:
        return True
    detail_ratio = difflib.SequenceMatcher(None, old_detail, new_detail).ratio()
    return detail_ratio >= 0.45


def context_from_payload(payload: dict[str, Any]) -> dict[str, str]:
    context = payload.get("context") or {}
    resolution = payload.get("projectResolution") or {}
    repo = compact(context.get("repo"))
    branch = compact(context.get("branch")) or "detached"
    version = compact(context.get("deviceVer")) or "unknown"
    variant = compact(context.get("productName")) or compact(resolution.get("productName")) or compact(context.get("projectName"))
    repository_id = repo_id(repo)
    variant_id = digest(normalize_identity(variant), 12) if variant else ""
    target_id = digest("|".join([repository_id, branch, version, variant_id]), 16)
    return {
        "repo_id": repository_id,
        "branch": branch,
        "version": version,
        "variant_id": variant_id,
        "target_id": target_id,
    }


def state_path(payload: dict[str, Any], state_root: Path = DEFAULT_STATE_ROOT) -> Path:
    context = context_from_payload(payload)
    return state_root / f"{context['target_id']}.json"


def load_payload(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_state(path: Path, context: dict[str, str]) -> dict[str, Any]:
    if not path.is_file():
        return {
            "schema_version": SCHEMA_VERSION,
            "context": context,
            "created_at": now(),
            "updated_at": now(),
            "bugs": {},
        }
    state = json.loads(path.read_text(encoding="utf-8"))
    if state.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"Unsupported reconciliation schema: {state.get('schema_version')}")
    if state.get("context", {}).get("target_id") != context["target_id"]:
        raise ValueError("Reconciliation state target does not match current snapshot")
    return state


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def compact_bug(bug: dict[str, Any]) -> dict[str, Any]:
    title_fp, detail_fp = symptom_parts(bug)
    return {
        "id": compact(bug.get("id")).lstrip("#"),
        "title": compact(bug.get("title")),
        "status": normalize_status(bug.get("status")),
        "activation_count": int(bug.get("activationCount") or 0),
        "title_fingerprint": title_fp,
        "detail_fingerprint": detail_fp,
        "last_seen_at": now(),
    }


def prepare_refresh(snapshot: Path, state_root: Path = DEFAULT_STATE_ROOT) -> dict[str, Any]:
    payload = load_payload(snapshot)
    context = context_from_payload(payload)
    path = state_path(payload, state_root)
    state = load_state(path, context)
    current_ids = {compact(bug.get("id")).lstrip("#") for bug in payload.get("bugs") or []}
    refresh = []
    for bug_id, previous in state.get("bugs", {}).items():
        if bug_id not in current_ids and previous.get("status") in {"active", "resolved"}:
            refresh.append(bug_id)
    return {
        "baseline": not path.exists(),
        "state_path": str(path),
        "target_id": context["target_id"],
        "refresh_ids": sorted(refresh, key=lambda value: (not value.isdigit(), value)),
    }


def merged_bugs(current: dict[str, Any], refresh_payloads: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    bugs = {compact(bug.get("id")).lstrip("#"): bug for bug in current.get("bugs") or []}
    for payload in refresh_payloads:
        for bug in payload.get("bugs") or []:
            bug_id = compact(bug.get("id")).lstrip("#")
            if bug_id and bug_id not in bugs:
                bugs[bug_id] = bug
    return bugs


def transition(previous: dict[str, Any], current: dict[str, Any]) -> str:
    old_status = previous.get("status", "unknown")
    new_status = normalize_status(current.get("status"))
    old_activations = int(previous.get("activation_count") or 0)
    new_activations = int(current.get("activationCount") or 0)
    reactivated = new_activations > old_activations or (
        new_status == "active" and old_status in {"resolved", "closed"}
    )
    if reactivated:
        return "reactivated_same" if same_symptom(previous, current) else "reactivated_variant"
    if new_status == "resolved" and old_status != "resolved":
        return "zentao_resolved"
    if new_status == "closed" and old_status != "closed":
        return "zentao_closed"
    return "unchanged"


def event_evidence(bug_id: str, previous: dict[str, Any], current: dict[str, Any], event: str) -> str:
    label = bug_display_label(bug_id, current.get("title") or previous.get("title"))
    return (
        f"Bug {label}: {previous.get('status', 'unknown')} -> "
        f"{normalize_status(current.get('status'))}; event={event}; activation="
        f"{previous.get('activation_count', 0)}->{int(current.get('activationCount') or 0)}"
    )


def render_report(events: list[dict[str, Any]], baseline: bool, refresh_ids: list[str]) -> str:
    lines = [REPORT_START, "## 与上次禅道快照对比", ""]
    if baseline:
        lines.append("- 本次建立精确目标基线，没有历史状态可比较。")
    else:
        lines.append(f"- 状态变化：{len(events)} 个；补查详情：{len(refresh_ids)} 个。")
    if events:
        lines.extend([
            "",
            "| Bug（ID + 标题） | 上次 | 当前 | 判断 | 记忆动作 |",
            "|---|---|---|---|---|",
        ])
        labels = {
            "zentao_resolved": "已解决，等待 QA",
            "zentao_closed": "QA/禅道已关闭",
            "reactivated_same": "同目标同症状重新激活",
            "reactivated_variant": "变体或症状变化，待人工判断",
        }
        actions = {
            "zentao_resolved": "更新为 resolved，不升级 QA 验证",
            "zentao_closed": "升级为 qa_verified",
            "reactivated_same": "降级为 failed + needs_review",
            "reactivated_variant": "不改旧记忆，列为同步/调查候选",
        }
        for event in events:
            label = bug_display_label(event["bug_id"], event.get("title"))
            lines.append(
                f"| {label} | {event['previous_status']} | {event['current_status']} | "
                f"{labels[event['event']]} | {actions[event['event']]} |"
            )
    elif not baseline:
        lines.append("- 未发现确定性的状态变化。")
    lines.append(REPORT_END)
    return "\n".join(lines) + "\n"


def append_report(chat_summary: Path, report: str) -> None:
    if not chat_summary.is_file():
        return
    text = chat_summary.read_text(encoding="utf-8", errors="replace")
    pattern = re.compile(rf"{re.escape(REPORT_START)}[\s\S]*?{re.escape(REPORT_END)}\s*", re.M)
    text = pattern.sub("", text).rstrip() + "\n\n" + report
    chat_summary.write_text(text, encoding="utf-8", newline="\n")


def apply_memory_events(events_path: Path, write: bool) -> dict[str, Any]:
    if not events_path.is_file() or not FIX_MEMORY.is_file():
        return {"skipped": "fix-memory script or event file missing"}
    command = [sys.executable, "-X", "utf8", str(FIX_MEMORY), "apply-events", "--events", str(events_path)]
    if write:
        command.append("--write")
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "fix-memory apply-events failed")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"output": result.stdout.strip()}


def reconcile(
    snapshot: Path,
    refresh_snapshots: list[Path] | None = None,
    state_root: Path = DEFAULT_STATE_ROOT,
    write_memory: bool = True,
) -> dict[str, Any]:
    current = load_payload(snapshot)
    context = context_from_payload(current)
    path = state_path(current, state_root)
    baseline = not path.exists()
    state = load_state(path, context)
    initial_plan = prepare_refresh(snapshot, state_root)
    refresh_payloads = [load_payload(item) for item in (refresh_snapshots or [])]
    bugs = merged_bugs(current, refresh_payloads)
    events: list[dict[str, Any]] = []

    for bug_id, bug in bugs.items():
        previous = state.get("bugs", {}).get(bug_id)
        if previous:
            name = transition(previous, bug)
            if name != "unchanged":
                events.append(
                    {
                        "event": name,
                        "bug_id": bug_id,
                        "title": compact(bug.get("title")) or compact(previous.get("title")) or "标题未获取",
                        "target_id": context["target_id"],
                        "previous_status": previous.get("status", "unknown"),
                        "current_status": normalize_status(bug.get("status")),
                        "previous_activation_count": int(previous.get("activation_count") or 0),
                        "current_activation_count": int(bug.get("activationCount") or 0),
                        "evidence": event_evidence(bug_id, previous, bug, name),
                        "observed_at": now(),
                    }
                )
        state.setdefault("bugs", {})[bug_id] = compact_bug(bug)

    state["updated_at"] = now()
    atomic_json(path, state)
    event_payload = {
        "schema_version": 1,
        "context": context,
        "baseline": baseline,
        "events": events,
    }
    events_path = snapshot.parent / "state-events.json"
    atomic_json(events_path, event_payload)
    report = render_report(events, baseline, initial_plan["refresh_ids"])
    append_report(snapshot.parent / "chat-summary.md", report)
    memory = apply_memory_events(events_path, write_memory) if events else {"events": 0, "matched": 0}
    return {
        "baseline": baseline,
        "state_path": str(path),
        "events_path": str(events_path),
        "events": events,
        "memory": memory,
        "report": report,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--snapshot", type=Path, required=True)
    prepare.add_argument("--state-root", type=Path, default=DEFAULT_STATE_ROOT)
    apply = sub.add_parser("apply")
    apply.add_argument("--snapshot", type=Path, required=True)
    apply.add_argument("--refresh", type=Path, action="append", default=[])
    apply.add_argument("--state-root", type=Path, default=DEFAULT_STATE_ROOT)
    apply.add_argument("--no-memory-write", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "prepare":
        print(json.dumps(prepare_refresh(args.snapshot.resolve(), args.state_root.resolve()), ensure_ascii=False, indent=2))
        return 0
    result = reconcile(
        args.snapshot.resolve(),
        [item.resolve() for item in args.refresh],
        args.state_root.resolve(),
        write_memory=not args.no_memory_write,
    )
    printable = {key: value for key, value in result.items() if key != "report"}
    print(json.dumps(printable, ensure_ascii=False, indent=2))
    print(result["report"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
