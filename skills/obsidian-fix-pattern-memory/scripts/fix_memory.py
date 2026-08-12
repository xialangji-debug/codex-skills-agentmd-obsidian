#!/usr/bin/env python3
"""Maintain canonical fix-pattern notes and per-target evidence state."""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any


DEFAULT_ROOT = Path.home() / "Documents" / "Obsidian" / "CodexVault" / "Codex" / "fix-patterns"
STATE_START = "<!-- codex-fix-state:start -->"
STATE_END = "<!-- codex-fix-state:end -->"
STATE_PREFIX = "<!-- codex-fix-state-json:"
SCHEMA_VERSION = 2

IMPLEMENTATION_STATES = {"not_applied", "applied", "committed", "superseded", "failed"}
VERIFICATION_STATES = {
    "unverified",
    "static_checked",
    "build_passed",
    "device_verified",
    "platform_verified",
    "qa_verified",
    "needs_review",
}
ZENTAO_STATES = {"unknown", "active", "resolved", "closed", "reactivated"}
RELATION_STATES = {"candidate", "applied", "reference", "not_applicable"}

VERIFICATION_RANK = {
    "needs_review": 0,
    "unverified": 10,
    "static_checked": 20,
    "build_passed": 30,
    "device_verified": 40,
    "platform_verified": 50,
    "qa_verified": 60,
}

EVENT_UPDATES = {
    "fixed": {"implementation": "applied", "verification": "static_checked", "relation": "applied"},
    "build_passed": {"verification": "build_passed"},
    "committed": {"implementation": "committed"},
    "device_verified": {"verification": "device_verified"},
    "platform_verified": {"verification": "platform_verified"},
    "zentao_resolved": {"zentao": "resolved"},
    "zentao_closed": {"zentao": "closed", "verification": "qa_verified"},
    "reactivated_same": {
        "implementation": "failed",
        "verification": "needs_review",
        "zentao": "reactivated",
    },
    "not_applicable": {"implementation": "not_applied", "relation": "not_applicable"},
    "superseded": {"implementation": "superseded"},
}


def now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def today() -> str:
    return dt.date.today().isoformat()


def compact(value: Any) -> str:
    return " ".join(str(value or "").split())


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


def resolve_repo(repo_arg: str) -> Path:
    candidate = Path(repo_arg).expanduser().resolve()
    root = run_git(candidate, "rev-parse", "--show-toplevel")
    return Path(root).resolve() if root else candidate


def normalize_identity(value: str) -> str:
    return compact(value).replace("\\", "/").lower()


def repo_identity(repo: Path, explicit: str = "") -> str:
    if explicit:
        return compact(explicit)
    remote = run_git(repo, "remote", "get-url", "origin")
    source = normalize_identity(remote or str(repo))
    return digest(source, 12)


def parse_variant_value(repo: Path, label: str) -> str:
    path = repo / ".codex-project" / "variant.md"
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    pattern = re.compile(rf"^-\s*{re.escape(label)}\s*[：:]\s*`?([^`\r\n]+)`?\s*$", re.M)
    match = pattern.search(text)
    return compact(match.group(1)) if match else ""


def read_device_version(repo: Path) -> str:
    value = parse_variant_value(repo, "`yl_device_ver`") or parse_variant_value(repo, "yl_device_ver")
    if value:
        return value
    header = repo / "gui" / "lv_watch" / "lv_apps" / "yl" / "yl.h"
    if not header.is_file():
        return ""
    text = header.read_text(encoding="utf-8", errors="replace")
    match = re.search(r'#define\s+yl_device_ver\s+"([^"]+)"', text)
    return compact(match.group(1)) if match else ""


def target_context(args: argparse.Namespace) -> dict[str, Any]:
    repo = resolve_repo(getattr(args, "repo", "."))
    repo_id = repo_identity(repo, getattr(args, "repo_id", ""))
    branch = compact(getattr(args, "branch", "")) or run_git(repo, "branch", "--show-current") or "detached"
    version = compact(getattr(args, "version", "")) or read_device_version(repo) or "unknown"
    variant = compact(getattr(args, "variant", ""))
    if not variant:
        variant = parse_variant_value(repo, "禅道产品") or parse_variant_value(repo, "客户/产品变体")
    variant_id = compact(getattr(args, "variant_id", "")) or (digest(normalize_identity(variant), 12) if variant else "")
    project_key = compact(getattr(args, "project_key", "")) or repo.name
    target_source = "|".join([repo_id, branch, version, variant_id])
    return {
        "target_id": digest(target_source, 16),
        "project_key": project_key,
        "repo_id": repo_id,
        "branch": branch,
        "version": version,
        "variant_id": variant_id,
        "bug_ids": [],
        "implementation": "not_applied",
        "verification": "unverified",
        "zentao": "unknown",
        "relation": "candidate",
        "commit": compact(getattr(args, "commit", "")) or run_git(repo, "rev-parse", "--short", "HEAD"),
        "evidence": "",
        "symptom_fingerprint": "",
        "updated_at": now(),
    }


def make_fix_id(title: str) -> str:
    stamp = dt.datetime.now().strftime("%Y%m%d")
    return f"FP-{stamp}-{digest(compact(title).lower() + now(), 8).upper()}"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug[:80] or f"fix-pattern-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}"


def inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def fix_notes(root: Path) -> list[Path]:
    return [note for note in sorted(root.glob("*.md")) if note.name.casefold() != "index.md"]


def frontmatter_value(text: str, key: str) -> str:
    match = re.match(r"\A---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    if not match:
        return ""
    field = re.search(rf"^{re.escape(key)}:\s*(.+?)\s*$", match.group(1), re.M)
    return compact(field.group(1)) if field else ""


def set_frontmatter(text: str, key: str, value: str) -> str:
    match = re.match(r"\A---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    if not match:
        raise ValueError("Fix-pattern note is missing YAML frontmatter")
    yaml = match.group(1)
    pattern = re.compile(rf"^{re.escape(key)}:\s*.*$", re.M)
    replacement = f"{key}: {value}"
    yaml = pattern.sub(replacement, yaml, count=1) if pattern.search(yaml) else yaml.rstrip() + "\n" + replacement
    return "---\n" + yaml + "\n---\n" + text[match.end():]


def empty_state(fix_id: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "fix_id": fix_id,
        "reference_target": None,
        "last_reference_target": None,
        "targets": [],
    }


def encode_state(state: dict[str, Any]) -> str:
    raw = json.dumps(state, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def decode_state(text: str) -> dict[str, Any] | None:
    match = re.search(rf"{re.escape(STATE_PREFIX)}\s*([A-Za-z0-9_=-]+)\s*-->", text)
    if not match:
        return None
    try:
        payload = base64.urlsafe_b64decode(match.group(1).encode("ascii"))
        state = json.loads(payload.decode("utf-8"))
    except (ValueError, json.JSONDecodeError) as error:
        raise ValueError(f"Invalid managed fix state: {error}") from error
    if state.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"Unsupported fix state schema: {state.get('schema_version')}")
    return state


def table_cell(value: Any) -> str:
    return compact(value).replace("|", "/") or "-"


def render_state(state: dict[str, Any]) -> str:
    lines = [
        STATE_START,
        f"{STATE_PREFIX} {encode_state(state)} -->",
        f"- 修复编号：`{state['fix_id']}`",
        f"- 当前参考目标：`{state.get('reference_target') or '无'}`",
        "",
        "| 目标 | 工程别名 | 分支 | 版本 | Bug | 实施 | 验证 | 禅道 | 关系 | 更新时间 |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for target in sorted(state.get("targets", []), key=lambda item: item.get("updated_at", ""), reverse=True):
        row = [
            target.get("target_id"),
            target.get("project_key"),
            target.get("branch"),
            target.get("version"),
            ",".join(target.get("bug_ids") or []),
            target.get("implementation"),
            target.get("verification"),
            target.get("zentao"),
            target.get("relation"),
            target.get("updated_at"),
        ]
        lines.append("| " + " | ".join(table_cell(value) for value in row) + " |")
    lines.extend([STATE_END, ""])
    return "\n".join(lines)


def replace_state_block(text: str, state: dict[str, Any]) -> str:
    block = render_state(state)
    pattern = re.compile(rf"{re.escape(STATE_START)}[\s\S]*?{re.escape(STATE_END)}\s*", re.M)
    if pattern.search(text):
        return pattern.sub(block, text, count=1)
    heading = "\n## 目标应用状态\n\n"
    insert = text.find("\n## 关键词")
    if insert >= 0:
        return text[:insert] + heading + block + text[insert:]
    return text.rstrip() + heading + block


def note_template(title: str, fix_id: str) -> str:
    return f"""---
area: engineering
domains:
  - asr
scope:
  - topic/fix-pattern
kind: fix-pattern
codex_access: manage
trust: working
lifecycle: active
fix_id: {fix_id}
reference_target: none
created: {today()}
updated: {today()}
---

# {title}

## 关键词

-

## 适用范围

-

## 症状

-

## 根因

-

## 关键文件和函数

-

## 修复思路

-

## 验证方法

-

## 注意事项

-
"""


def set_section(text: str, heading: str, values: list[str]) -> str:
    clean = [compact(value) for value in values if compact(value)]
    if not clean:
        return text
    body = "\n".join(f"- {value}" for value in clean)
    pattern = re.compile(
        rf"(^##\s+{re.escape(heading)}\s*$\r?\n)([\s\S]*?)(?=^##\s+|\Z)",
        re.M,
    )
    replacement = rf"\1\n{body}\n\n"
    if pattern.search(text):
        return pattern.sub(replacement, text, count=1)
    return text.rstrip() + f"\n\n## {heading}\n\n{body}\n"


def update_knowledge_sections(text: str, args: argparse.Namespace) -> str:
    fields = [
        ("关键词", getattr(args, "keyword", [])),
        ("适用范围", getattr(args, "scope", [])),
        ("症状", [getattr(args, "symptoms", "")]),
        ("根因", [getattr(args, "root_cause", "")]),
        ("关键文件和函数", getattr(args, "key_file", [])),
        ("修复思路", [getattr(args, "fix", "")]),
        ("验证方法", [getattr(args, "verification_method", "")]),
        ("注意事项", [getattr(args, "caution", "")]),
    ]
    for heading, values in fields:
        text = set_section(text, heading, values)
    return text


def load_note(path: Path, title: str = "") -> tuple[str, dict[str, Any]]:
    if path.exists():
        text = path.read_text(encoding="utf-8", errors="replace")
        state = decode_state(text)
        if state is None:
            fix_id = frontmatter_value(text, "fix_id") or make_fix_id(title or path.stem)
            state = empty_state(fix_id)
        return text, state
    if not title:
        raise ValueError("--title is required when creating a new note")
    fix_id = make_fix_id(title)
    return note_template(title, fix_id), empty_state(fix_id)


def target_by_id(state: dict[str, Any], target_id: str) -> dict[str, Any] | None:
    return next((item for item in state.get("targets", []) if item.get("target_id") == target_id), None)


def choose_reference(state: dict[str, Any]) -> None:
    previous = state.get("reference_target")
    eligible = [
        target for target in state.get("targets", [])
        if target.get("implementation") in {"applied", "committed"}
        and target.get("relation") != "not_applicable"
        and target.get("verification") != "needs_review"
    ]
    eligible.sort(
        key=lambda target: (
            VERIFICATION_RANK.get(target.get("verification", "unverified"), 0),
            target.get("updated_at", ""),
        ),
        reverse=True,
    )
    selected = eligible[0].get("target_id") if eligible else None
    if previous and previous != selected:
        state["last_reference_target"] = previous
    state["reference_target"] = selected
    for target in state.get("targets", []):
        if target.get("relation") in {"not_applicable", "candidate"}:
            continue
        target["relation"] = "reference" if target.get("target_id") == selected else "applied"


def finalize_note(text: str, state: dict[str, Any]) -> str:
    choose_reference(state)
    reference = target_by_id(state, state.get("reference_target") or "")
    trust = "verified" if reference and VERIFICATION_RANK.get(reference.get("verification"), 0) >= 40 else "working"
    text = replace_state_block(text, state)
    text = set_frontmatter(text, "fix_id", state["fix_id"])
    text = set_frontmatter(text, "reference_target", state.get("reference_target") or "none")
    text = set_frontmatter(text, "trust", trust)
    text = set_frontmatter(text, "updated", today())
    return text.rstrip() + "\n"


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temp, path)


def resolve_note(args: argparse.Namespace) -> Path:
    root = Path(args.root).expanduser().resolve()
    note = Path(args.note).expanduser().resolve() if args.note else root / f"{slugify(args.slug or args.title)}.md"
    if not inside(note, root):
        raise SystemExit(f"Refusing to edit note outside fix-pattern root: {note}")
    return note


def apply_updates(target: dict[str, Any], updates: dict[str, Any], args: argparse.Namespace) -> None:
    for key, allowed in [
        ("implementation", IMPLEMENTATION_STATES),
        ("verification", VERIFICATION_STATES),
        ("zentao", ZENTAO_STATES),
        ("relation", RELATION_STATES),
    ]:
        value = updates.get(key)
        if value:
            if value not in allowed:
                raise ValueError(f"Invalid {key}: {value}")
            target[key] = value
    bugs = list(target.get("bug_ids") or [])
    for raw in getattr(args, "bug", []) or []:
        bug = compact(raw).lstrip("#")
        if bug and bug not in bugs:
            bugs.append(bug)
    target["bug_ids"] = bugs
    for key, arg_name in [
        ("commit", "commit"),
        ("evidence", "evidence"),
        ("symptom_fingerprint", "symptom_fingerprint"),
    ]:
        value = compact(getattr(args, arg_name, ""))
        if value:
            target[key] = value
    target["updated_at"] = now()


def upsert_target(state: dict[str, Any], context: dict[str, Any], updates: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    target = target_by_id(state, context["target_id"])
    if target is None:
        target = context
        state.setdefault("targets", []).append(target)
    else:
        for key in ("project_key", "repo_id", "branch", "version", "variant_id"):
            if context.get(key):
                target[key] = context[key]
    apply_updates(target, updates, args)
    return target


def write_or_preview(note: Path, text: str, write: bool) -> None:
    if write:
        atomic_write(note, text)
        print(f"updated={note}")
    else:
        print(text)


def command_upsert(args: argparse.Namespace) -> int:
    note = resolve_note(args)
    creating = not note.exists()
    if creating and args.write and not all([compact(args.symptoms), compact(args.root_cause), compact(args.fix)]):
        raise SystemExit("A new written note requires --symptoms, --root-cause, and --fix")
    text, state = load_note(note, args.title)
    text = update_knowledge_sections(text, args)
    updates = {
        "implementation": args.implementation,
        "verification": args.verification,
        "zentao": args.zentao,
        "relation": args.relation,
    }
    target = upsert_target(state, target_context(args), updates, args)
    result = finalize_note(text, state)
    write_or_preview(note, result, args.write)
    print(f"fix_id={state['fix_id']} target_id={target['target_id']} reference={state.get('reference_target') or 'none'}")
    return 0


def command_event(args: argparse.Namespace) -> int:
    if args.event == "reactivated_variant":
        print("skipped=variant reactivation requires code review before changing canonical memory")
        return 0
    note = resolve_note(args)
    if not note.exists():
        raise SystemExit(f"Fix-pattern note not found: {note}")
    text, state = load_note(note)
    target = upsert_target(state, target_context(args), EVENT_UPDATES[args.event], args)
    result = finalize_note(text, state)
    write_or_preview(note, result, args.write)
    print(f"event={args.event} fix_id={state['fix_id']} target_id={target['target_id']}")
    return 0


def event_target_match(target: dict[str, Any], event: dict[str, Any]) -> bool:
    bug = compact(event.get("bug_id")).lstrip("#")
    return (
        target.get("target_id") == event.get("target_id")
        and bug
        and bug in (target.get("bug_ids") or [])
    )


def apply_event_to_target(target: dict[str, Any], event: dict[str, Any]) -> bool:
    name = event.get("event")
    if name == "reactivated_variant" or name not in EVENT_UPDATES:
        return False
    for key, value in EVENT_UPDATES[name].items():
        target[key] = value
    evidence = compact(event.get("evidence"))
    if evidence:
        target["evidence"] = evidence
    target["updated_at"] = compact(event.get("observed_at")) or now()
    return True


def command_apply_events(args: argparse.Namespace) -> int:
    payload = json.loads(Path(args.events).read_text(encoding="utf-8"))
    events = payload.get("events") or []
    root = Path(args.root).expanduser().resolve()
    changed: list[str] = []
    matched: set[int] = set()
    for note in fix_notes(root):
        text = note.read_text(encoding="utf-8", errors="replace")
        state = decode_state(text)
        if not state:
            continue
        note_changed = False
        for index, event in enumerate(events):
            for target in state.get("targets", []):
                if event_target_match(target, event) and apply_event_to_target(target, event):
                    note_changed = True
                    matched.add(index)
        if note_changed:
            result = finalize_note(text, state)
            if args.write:
                atomic_write(note, result)
            changed.append(str(note))
    summary = {
        "events": len(events),
        "matched": len(matched),
        "unmatched": len(events) - len(matched),
        "changed_notes": changed,
        "write": bool(args.write),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def command_validate(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    errors: list[str] = []
    fix_ids: dict[str, Path] = {}
    managed = 0
    legacy = 0
    for note in fix_notes(root):
        text = note.read_text(encoding="utf-8", errors="replace")
        try:
            state = decode_state(text)
        except ValueError as error:
            errors.append(f"{note.name}: {error}")
            continue
        if not state:
            legacy += 1
            continue
        managed += 1
        fix_id = state.get("fix_id")
        if not fix_id:
            errors.append(f"{note.name}: missing fix_id")
        elif fix_id in fix_ids:
            errors.append(f"{note.name}: duplicate fix_id with {fix_ids[fix_id].name}")
        else:
            fix_ids[fix_id] = note
        target_ids: set[str] = set()
        for target in state.get("targets", []):
            target_id = target.get("target_id")
            if not target_id or target_id in target_ids:
                errors.append(f"{note.name}: missing or duplicate target_id {target_id}")
            target_ids.add(target_id)
    print(json.dumps({"managed": managed, "legacy": legacy, "errors": errors}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


def command_migrate(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    candidates: list[str] = []
    for note in fix_notes(root):
        text = note.read_text(encoding="utf-8", errors="replace")
        if decode_state(text):
            continue
        title_match = re.search(r"^#\s+(.+?)\s*$", text, re.M)
        title = compact(title_match.group(1)) if title_match else note.stem
        fix_id = frontmatter_value(text, "fix_id") or make_fix_id(title)
        state = empty_state(fix_id)
        result = finalize_note(text, state)
        candidates.append(str(note))
        if args.write:
            atomic_write(note, result)
    print(json.dumps({"candidates": candidates, "write": bool(args.write)}, ensure_ascii=False, indent=2))
    return 0


def command_candidates(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    note = Path(args.note).expanduser().resolve()
    if not inside(note, root) or not note.is_file():
        raise SystemExit(f"Fix-pattern note not found under root: {note}")
    text = note.read_text(encoding="utf-8", errors="replace")
    state = decode_state(text)
    if not state:
        raise SystemExit("Fix-pattern note has no managed target state; preview migration first")
    registry_path = Path(args.active_projects).expanduser().resolve()
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    results: list[dict[str, Any]] = []
    for item in registry.get("projects") or []:
        if not item.get("enabled", True):
            continue
        if not args.all_families and item.get("family") != "asr360x":
            continue
        repo = Path(item.get("path", "")).expanduser()
        if not repo.is_dir():
            results.append({"project_key": item.get("project_key", "unknown"), "status": "path_missing"})
            continue
        context_args = argparse.Namespace(
            repo=str(repo), project_key=item.get("project_key", ""), repo_id="", branch="",
            version="", variant="", variant_id="", commit="",
        )
        context = target_context(context_args)
        existing = target_by_id(state, context["target_id"])
        row = {
            "project_key": context["project_key"],
            "branch": context["branch"],
            "version": context["version"],
            "target_id": context["target_id"],
            "status": "recorded" if existing else "unassessed_candidate",
        }
        if existing:
            row.update({
                "implementation": existing.get("implementation"),
                "verification": existing.get("verification"),
                "relation": existing.get("relation"),
            })
        if args.include_recorded or not existing:
            results.append(row)
    print(json.dumps({"fix_id": state["fix_id"], "candidates": results}, ensure_ascii=False, indent=2))
    return 0


def add_context_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo", default=".")
    parser.add_argument("--project-key", default="")
    parser.add_argument("--repo-id", default="")
    parser.add_argument("--branch", default="")
    parser.add_argument("--version", default="")
    parser.add_argument("--variant", default="")
    parser.add_argument("--variant-id", default="")
    parser.add_argument("--bug", action="append", default=[])
    parser.add_argument("--commit", default="")
    parser.add_argument("--evidence", default="")
    parser.add_argument("--symptom-fingerprint", default="")


def add_note_arguments(parser: argparse.ArgumentParser, creating: bool) -> None:
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--note", default="")
    if creating:
        parser.add_argument("--title", default="")
        parser.add_argument("--slug", default="")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    upsert = sub.add_parser("upsert")
    add_note_arguments(upsert, creating=True)
    add_context_arguments(upsert)
    upsert.add_argument("--implementation", choices=sorted(IMPLEMENTATION_STATES), default="applied")
    upsert.add_argument("--verification", choices=sorted(VERIFICATION_STATES), default="static_checked")
    upsert.add_argument("--zentao", choices=sorted(ZENTAO_STATES), default="unknown")
    upsert.add_argument("--relation", choices=sorted(RELATION_STATES), default="applied")
    upsert.add_argument("--write", action="store_true")
    upsert.add_argument("--keyword", action="append", default=[])
    upsert.add_argument("--scope", action="append", default=[])
    upsert.add_argument("--symptoms", default="")
    upsert.add_argument("--root-cause", default="")
    upsert.add_argument("--key-file", action="append", default=[])
    upsert.add_argument("--fix", default="")
    upsert.add_argument("--verification-method", default="")
    upsert.add_argument("--caution", action="append", default=[])
    upsert.set_defaults(func=command_upsert)

    event = sub.add_parser("event")
    add_note_arguments(event, creating=False)
    add_context_arguments(event)
    event.add_argument("--event", choices=sorted([*EVENT_UPDATES, "reactivated_variant"]), required=True)
    event.add_argument("--write", action="store_true")
    event.set_defaults(func=command_event)

    apply_events = sub.add_parser("apply-events")
    apply_events.add_argument("--root", default=str(DEFAULT_ROOT))
    apply_events.add_argument("--events", type=Path, required=True)
    apply_events.add_argument("--write", action="store_true")
    apply_events.set_defaults(func=command_apply_events)

    validate = sub.add_parser("validate")
    validate.add_argument("--root", default=str(DEFAULT_ROOT))
    validate.set_defaults(func=command_validate)

    migrate = sub.add_parser("migrate")
    migrate.add_argument("--root", default=str(DEFAULT_ROOT))
    migrate.add_argument("--write", action="store_true")
    migrate.set_defaults(func=command_migrate)

    candidates = sub.add_parser("candidates")
    candidates.add_argument("--root", default=str(DEFAULT_ROOT))
    candidates.add_argument("--note", required=True)
    candidates.add_argument(
        "--active-projects",
        default=str(Path.home() / ".codex" / "active-projects.json"),
    )
    candidates.add_argument("--include-recorded", action="store_true")
    candidates.add_argument("--all-families", action="store_true")
    candidates.set_defaults(func=command_candidates)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
