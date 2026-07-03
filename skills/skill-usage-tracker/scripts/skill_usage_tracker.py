#!/usr/bin/env python3
"""Track Codex skill usage and feedback locally.

This script intentionally uses only Python's standard library. It scans local
Codex JSONL sessions, writes usage signals to SQLite, and records optional
feedback at turn or skill level.
"""

from __future__ import annotations

import argparse
import datetime as dt
import http.server
import hashlib
import json
import re
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Iterable


HOME = Path.home()
CODEX_HOME = Path.home() / ".codex"
DB_PATH = CODEX_HOME / "skill-usage" / "usage.sqlite"
OTEL_JSONL_PATH = CODEX_HOME / "skill-usage" / "otel" / "otlp.jsonl"
SESSION_ROOTS = [
    CODEX_HOME / "sessions",
    CODEX_HOME / "archived_sessions",
]

COMMON_SKILLS = [
    "imagegen",
    "openai-docs",
    "plugin-creator",
    "skill-creator",
    "skill-installer",
    "find-skills",
    "karpathy-guidelines",
    "mermaid-visualizer",
    "pdf",
    "playwright",
    "playwright-interactive",
    "screenshot",
    "speech",
    "transcribe",
    "ui-ux-pro-max",
    "yeet",
    "understand",
    "understand-chat",
    "understand-dashboard",
    "understand-diff",
    "understand-domain",
    "understand-explain",
    "understand-knowledge",
    "understand-onboard",
    "browser",
    "chrome",
    "documents",
    "presentations",
    "spreadsheets",
    "skill-usage-tracker",
]

SKIP_TEXT_MARKERS = [
    "<skills_instructions>",
    "### Available skills",
    "The following is the Codex agent history",
    "approval assessment",
    "TRANSCRIPT",
    "Handoff Summary",
    "Another language model started",
    "skill_usage_tracker.py",
    "Skill Usage Tracker",
    "skill-usage-tracker",
    "COMMAND_EVIDENCE",
    "TASK_ALIASES",
]

TASK_ALIASES: dict[str, list[re.Pattern[str]]] = {
    "documents": [re.compile(r"\.docx\b", re.I), re.compile(r"word\s*文档", re.I)],
    "pdf": [re.compile(r"\.pdf\b", re.I)],
    "spreadsheets": [re.compile(r"\.xlsx\b", re.I), re.compile(r"\bExcel\b", re.I)],
    "presentations": [re.compile(r"\.pptx\b", re.I), re.compile(r"\bPPT\b", re.I), re.compile(r"PowerPoint", re.I)],
    "screenshot": [re.compile(r"截图", re.I)],
    "imagegen": [re.compile(r"生成图片", re.I), re.compile(r"画一张", re.I), re.compile(r"做一张图", re.I)],
    "mermaid-visualizer": [re.compile(r"流程图", re.I), re.compile(r"```mermaid", re.I)],
    "speech": [re.compile(r"文字转语音", re.I), re.compile(r"配音", re.I)],
    "transcribe": [re.compile(r"转录", re.I), re.compile(r"音频转文字", re.I), re.compile(r"语音转文字", re.I)],
}

COMMAND_EVIDENCE: dict[str, re.Pattern[str]] = {
    "understand": re.compile(r"\.understand-anything|understand-anything|knowledge-graph\.json", re.I),
    "playwright": re.compile(r"\bplaywright\b|playwright-cli", re.I),
    "pdf": re.compile(r"\b(pdfplumber|pypdf|reportlab|pdftoppm|pdftocairo)\b", re.I),
    "documents": re.compile(r"\b(render_docx\.py|python-docx)\b", re.I),
    "presentations": re.compile(r"\b(python-pptx|render_pptx)\b", re.I),
    "spreadsheets": re.compile(r"\b(openpyxl|xlsxwriter)\b", re.I),
    "speech": re.compile(r"text_to_speech\.py", re.I),
    "transcribe": re.compile(r"\bwhisper\b|diarization|transcribe", re.I),
    "mermaid-visualizer": re.compile(r"```mermaid", re.I),
}

CLEANUP_PROTECTED_SKILLS = {
    "asr3601-cross-branch-porting",
    "asr3601-fix-verifier",
    "asr3601-lvgl-firmware-triage",
    "browser",
    "catstudio-log-extractor",
    "chrome",
    "documents",
    "find-skills",
    "github",
    "imagegen",
    "karpathy-guidelines",
    "obsidian-fix-pattern-memory",
    "openai-docs",
    "pdf",
    "playwright",
    "playwright-interactive",
    "plugin-creator",
    "presentations",
    "skill-creator",
    "skill-installer",
    "skill-usage-tracker",
    "spreadsheets",
    "understand",
    "understand-chat",
    "understand-dashboard",
    "understand-diff",
    "understand-domain",
    "understand-explain",
    "understand-knowledge",
    "understand-onboard",
}

CLEANUP_PROTECTED_PREFIXES = (
    "asr3601-",
    "github:",
    "latex:",
    "understand-",
    "understand-anything:",
)

OTEL_NON_USAGE_STATUSES = {
    "blocked",
    "cancelled",
    "canceled",
    "disabled",
    "error",
    "failed",
    "failure",
    "missing",
    "not_found",
    "rejected",
    "skipped",
    "truncated",
}

RATING_ALIASES = {
    "useful": "useful",
    "good": "useful",
    "helpful": "useful",
    "有用": "useful",
    "好": "useful",
    "ok": "ok",
    "okay": "ok",
    "neutral": "ok",
    "一般": "ok",
    "还行": "ok",
    "not-useful": "not_useful",
    "not_useful": "not_useful",
    "bad": "not_useful",
    "useless": "not_useful",
    "没用": "not_useful",
    "无用": "not_useful",
    "不行": "not_useful",
    "unneeded": "unneeded",
    "unnecessary": "unneeded",
    "没必要": "unneeded",
    "不需要": "unneeded",
}


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def iso_days_ago(now: dt.datetime, days: int) -> str:
    return (now - dt.timedelta(days=days)).isoformat(timespec="seconds").replace("+00:00", "Z")


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    init_db(con)
    return con


def init_db(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        create table if not exists usage_events (
            event_id text primary key,
            detected_at text not null,
            event_ts text,
            session_id text,
            turn_id text,
            source_file text,
            skill text not null,
            signal text not null,
            confidence integer not null,
            snippet text
        );

        create index if not exists idx_usage_skill on usage_events(skill);
        create index if not exists idx_usage_turn on usage_events(turn_id);
        create index if not exists idx_usage_ts on usage_events(event_ts);

        create table if not exists turn_feedback (
            feedback_id integer primary key autoincrement,
            created_at text not null,
            turn_id text not null,
            session_id text,
            rating text not null,
            note text,
            best_skill text,
            unneeded_skill text
        );

        create index if not exists idx_turn_feedback_turn on turn_feedback(turn_id);

        create table if not exists skill_feedback (
            feedback_id integer primary key autoincrement,
            created_at text not null,
            turn_id text not null,
            skill text not null,
            rating text not null,
            note text
        );

        create index if not exists idx_skill_feedback_skill on skill_feedback(skill);
        create index if not exists idx_skill_feedback_turn on skill_feedback(turn_id);

        create table if not exists otel_metric_points (
            point_id text primary key,
            seen_at text not null,
            metric text not null,
            series_key text not null,
            time_unix_nano integer,
            value real not null,
            temporality integer,
            delta real not null
        );

        create index if not exists idx_otel_metric_series on otel_metric_points(series_key, time_unix_nano);
        """
    )
    con.commit()


def discover_skills() -> list[str]:
    skills = set(COMMON_SKILLS)
    roots = [
        CODEX_HOME / "skills",
        CODEX_HOME / "plugins" / "cache",
        HOME / "plugins",
    ]
    for root in roots:
        if not root.exists():
            continue
        for skill_md in root.rglob("SKILL.md"):
            name = skill_md.parent.name.strip().lower()
            if name:
                skills.add(name)
    return sorted(skills, key=lambda value: (-len(value), value))


def discover_skill_md_paths(skills: Iterable[str]) -> list[tuple[str, str]]:
    known = set(skills)
    paths: list[tuple[str, str]] = []
    roots = [
        CODEX_HOME / "skills",
        CODEX_HOME / "plugins" / "cache",
        HOME / "plugins",
    ]
    for root in roots:
        if not root.exists():
            continue
        for skill_md in root.rglob("SKILL.md"):
            name = skill_md.parent.name.strip().lower()
            if name in known:
                paths.append((name, normalize_path(skill_md)))
    return paths


def discover_skill_path_map() -> dict[str, list[str]]:
    skills = discover_skills()
    path_map: dict[str, list[str]] = {skill: [] for skill in skills}
    for skill, path in discover_skill_md_paths(skills):
        path_map.setdefault(skill, []).append(path)
    return path_map


def skill_source_label(paths: list[str]) -> str:
    labels: set[str] = set()
    for path in paths:
        if "/.codex/skills/.system/" in path:
            labels.add("system")
        elif "/.codex/plugins/cache/openai-" in path:
            labels.add("bundled-plugin")
        elif "/.codex/plugins/cache/personal/" in path:
            labels.add("personal-plugin")
        elif "/.codex/skills/" in path:
            labels.add("local")
        elif "/plugins/" in path:
            labels.add("plugin")
        else:
            labels.add("other")
    return "+".join(sorted(labels)) if labels else "common"


def is_managed_skill_path(path: str) -> bool:
    return "/.codex/skills/.system/" in path or "/.codex/plugins/cache/openai-" in path


def is_cleanup_protected(skill: str, paths: list[str]) -> bool:
    if skill in CLEANUP_PROTECTED_SKILLS:
        return True
    if any(skill.startswith(prefix) for prefix in CLEANUP_PROTECTED_PREFIXES):
        return True
    return bool(paths) and all(is_managed_skill_path(path) for path in paths)


def normalize_path(path: Path | str) -> str:
    return str(path).replace("\\", "/").lower()


def should_skip_text(text: str) -> bool:
    if not text:
        return True
    return any(marker in text for marker in SKIP_TEXT_MARKERS)


def should_skip_tool_payload(text: str) -> bool:
    """Avoid counting this tracker building/updating itself as skill usage."""
    normalized = text.replace("\\", "/")
    markers = [
        "/plugins/skill-usage-tracker/",
        "skill_usage_tracker.py",
        "Skill Usage Tracker",
        "COMMAND_EVIDENCE",
        "TASK_ALIASES",
        "scan_sessions(",
        "discover_skill_md_paths(",
    ]
    return any(marker in normalized for marker in markers)


def explicit_skills_from_user(text: str, skills: list[str]) -> set[str]:
    found: set[str] = set()
    for skill in skills:
        escaped = re.escape(skill)
        patterns = [
            rf"\${escaped}\b",
            rf"\[@?{escaped}\]",
            rf"@{escaped}\b",
            rf"plugin://{escaped}\b",
            rf"/{escaped}\b",
        ]
        if skill not in {"documents", "browser", "chrome", "pdf", "speech", "understand"}:
            patterns.append(rf"(?<![A-Za-z0-9_-]){escaped}(?![A-Za-z0-9_-])")
        if skill == "browser":
            patterns += [r"Browser Use", r"@browser-use"]
        if skill == "chrome":
            patterns += [r"Chrome Agent"]
        if skill == "imagegen":
            patterns += [r"Image Gen"]
        if skill == "understand":
            patterns += [r"Understand-Anything"]
        if any(re.search(pattern, text, re.I) for pattern in patterns):
            found.add(skill)
    return found


def assistant_declared_skills(text: str, skills: list[str]) -> set[str]:
    if any(
        marker in text
        for marker in [
            "你现在**已安装**的技能",
            "这些技能你不用自己点开",
            "技能主要有这些",
        ]
    ):
        return set()
    found: set[str] = set()
    for skill in skills:
        escaped = re.escape(skill)
        patterns = [
            rf"(?:我会|我将|这次我会|我准备用|I will|Using)\s*(?:用|使用|按)?\s*`?{escaped}`?",
            rf"`?{escaped}`?\s*(?:技能|skill)\s*(?:来|用于)?",
        ]
        if any(re.search(pattern, text, re.I) for pattern in patterns):
            found.add(skill)
    return found


def make_event_id(
    session_id: str,
    turn_id: str,
    timestamp: str,
    skill: str,
    signal: str,
    raw_id: str,
    snippet: str,
) -> str:
    payload = "|".join([session_id, turn_id, timestamp, skill, signal, raw_id, snippet[:160]])
    return hashlib.sha256(payload.encode("utf-8", errors="replace")).hexdigest()


def add_event(
    events: list[dict[str, Any]],
    *,
    timestamp: str,
    session_id: str,
    turn_id: str,
    source_file: Path,
    skill: str,
    signal: str,
    confidence: int,
    raw_id: str,
    snippet: str = "",
) -> None:
    clean_snippet = " ".join(str(snippet).split())[:300]
    events.append(
        {
            "event_id": make_event_id(session_id, turn_id, timestamp, skill, signal, raw_id, clean_snippet),
            "detected_at": utc_now(),
            "event_ts": timestamp,
            "session_id": session_id,
            "turn_id": turn_id,
            "source_file": str(source_file),
            "skill": skill,
            "signal": signal,
            "confidence": confidence,
            "snippet": clean_snippet,
        }
    )


def iter_session_files() -> Iterable[Path]:
    for root in SESSION_ROOTS:
        if not root.exists():
            continue
        yield from root.rglob("*.jsonl")


def scan_sessions(since: str | None = None) -> list[dict[str, Any]]:
    skills = discover_skills()
    skill_md_paths = discover_skill_md_paths(skills)
    events: list[dict[str, Any]] = []

    for file_path in iter_session_files():
        session_id = ""
        current_turn = ""
        try:
            handle = file_path.open("r", encoding="utf-8", errors="replace")
        except OSError:
            continue
        with handle:
            for line in handle:
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                timestamp = obj.get("timestamp") or ""
                if since and timestamp and timestamp < since:
                    continue
                payload = obj.get("payload") or {}
                record_type = obj.get("type")
                payload_type = payload.get("type")

                if record_type == "session_meta":
                    session_id = payload.get("id") or session_id
                    continue

                if record_type == "event_msg" and payload_type == "task_started":
                    current_turn = payload.get("turn_id") or current_turn
                    continue
                if record_type == "event_msg" and payload_type == "task_complete":
                    continue

                turn_id = payload.get("turn_id") or current_turn or session_id
                raw_session_id = session_id or "unknown-session"
                raw_turn_id = turn_id or "unknown-turn"

                if record_type == "event_msg" and payload_type == "user_message":
                    text = payload.get("message") or ""
                    if should_skip_text(text):
                        continue
                    for skill in explicit_skills_from_user(text, skills):
                        add_event(
                            events,
                            timestamp=timestamp,
                            session_id=raw_session_id,
                            turn_id=raw_turn_id,
                            source_file=file_path,
                            skill=skill,
                            signal="user_named",
                            confidence=50,
                            raw_id="user-message",
                            snippet=text,
                        )
                    for skill, patterns in TASK_ALIASES.items():
                        if any(pattern.search(text) for pattern in patterns):
                            add_event(
                                events,
                                timestamp=timestamp,
                                session_id=raw_session_id,
                                turn_id=raw_turn_id,
                                source_file=file_path,
                                skill=skill,
                                signal="task_alias",
                                confidence=40,
                                raw_id="task-alias",
                                snippet=text,
                            )

                elif record_type == "event_msg" and payload_type == "agent_message":
                    text = payload.get("message") or ""
                    if should_skip_text(text):
                        continue
                    for skill in assistant_declared_skills(text, skills):
                        add_event(
                            events,
                            timestamp=timestamp,
                            session_id=raw_session_id,
                            turn_id=raw_turn_id,
                            source_file=file_path,
                            skill=skill,
                            signal="assistant_declared",
                            confidence=70,
                            raw_id="assistant-message",
                            snippet=text,
                        )

                elif record_type == "response_item" and payload_type in {"function_call", "custom_tool_call"}:
                    call_id = payload.get("call_id") or payload.get("id") or str(hash(line))
                    text = json.dumps(payload, ensure_ascii=False)
                    if should_skip_tool_payload(text):
                        continue
                    normalized_text = text.replace("\\", "/").lower()

                    for skill, skill_md_path in skill_md_paths:
                        if skill_md_path in normalized_text:
                            add_event(
                                events,
                                timestamp=timestamp,
                                session_id=raw_session_id,
                                turn_id=raw_turn_id,
                                source_file=file_path,
                                skill=skill,
                                signal="skill_md_read",
                                confidence=95,
                                raw_id=call_id,
                                snippet=text,
                            )
                    for skill in skills:
                        fallback = rf"/skills/(?:\.system/)?{re.escape(skill.lower())}/skill\.md"
                        if re.search(fallback, normalized_text):
                            add_event(
                                events,
                                timestamp=timestamp,
                                session_id=raw_session_id,
                                turn_id=raw_turn_id,
                                source_file=file_path,
                                skill=skill,
                                signal="skill_md_read",
                                confidence=95,
                                raw_id=f"{call_id}-fallback",
                                snippet=text,
                            )

                    namespace = (payload.get("namespace") or "").lower()
                    name = (payload.get("name") or "").lower()
                    for skill in ["browser", "documents", "presentations", "spreadsheets"]:
                        if skill in namespace or name == skill:
                            add_event(
                                events,
                                timestamp=timestamp,
                                session_id=raw_session_id,
                                turn_id=raw_turn_id,
                                source_file=file_path,
                                skill=skill,
                                signal="plugin_tool_call",
                                confidence=95,
                                raw_id=call_id,
                                snippet=text,
                            )

                    for skill, pattern in COMMAND_EVIDENCE.items():
                        if pattern.search(text):
                            add_event(
                                events,
                                timestamp=timestamp,
                                session_id=raw_session_id,
                                turn_id=raw_turn_id,
                                source_file=file_path,
                                skill=skill,
                                signal="command_evidence",
                                confidence=60,
                                raw_id=call_id,
                                snippet=text,
                            )

                elif record_type == "event_msg" and payload_type in {"image_generation_call", "image_generation_end"}:
                    call_id = payload.get("call_id") or payload.get("id") or timestamp
                    add_event(
                        events,
                        timestamp=timestamp,
                        session_id=raw_session_id,
                        turn_id=raw_turn_id,
                        source_file=file_path,
                        skill="imagegen",
                        signal="system_tool_call",
                        confidence=95,
                        raw_id=call_id,
                        snippet=json.dumps(payload, ensure_ascii=False),
                    )

                elif record_type == "event_msg" and payload_type in {"mcp_tool_call_begin", "mcp_tool_call_end"}:
                    call_id = payload.get("call_id") or timestamp
                    invocation = payload.get("invocation") or {}
                    server = (invocation.get("server") or "").lower()
                    tool = (invocation.get("tool") or "").lower()
                    text = json.dumps(payload, ensure_ascii=False)
                    for skill in ["browser", "documents", "presentations", "spreadsheets"]:
                        if skill in server or skill in tool:
                            add_event(
                                events,
                                timestamp=timestamp,
                                session_id=raw_session_id,
                                turn_id=raw_turn_id,
                                source_file=file_path,
                                skill=skill,
                                signal="plugin_tool_call",
                                confidence=95,
                                raw_id=call_id,
                                snippet=text,
                            )
                    if "setupBrowserRuntime" in text or "plugins/cache/openai-bundled/browser" in text.replace("\\", "/"):
                        add_event(
                            events,
                            timestamp=timestamp,
                            session_id=raw_session_id,
                            turn_id=raw_turn_id,
                            source_file=file_path,
                            skill="browser",
                            signal="plugin_tool_call",
                            confidence=90,
                            raw_id=f"{call_id}-browser-runtime",
                            snippet=text,
                        )

    return events


def store_events(con: sqlite3.Connection, events: list[dict[str, Any]]) -> tuple[int, int]:
    inserted = 0
    for event in events:
        before = con.total_changes
        con.execute(
            """
            insert or ignore into usage_events (
                event_id, detected_at, event_ts, session_id, turn_id, source_file,
                skill, signal, confidence, snippet
            ) values (
                :event_id, :detected_at, :event_ts, :session_id, :turn_id, :source_file,
                :skill, :signal, :confidence, :snippet
            )
            """,
            event,
        )
        if con.total_changes > before:
            inserted += 1
    con.commit()
    return inserted, len(events)


def otel_value(value: dict[str, Any] | None) -> Any:
    if not isinstance(value, dict):
        return None
    for key in ["stringValue", "intValue", "doubleValue", "boolValue"]:
        if key in value:
            return value[key]
    if "arrayValue" in value:
        values = value.get("arrayValue", {}).get("values") or []
        return [otel_value(item) for item in values]
    if "kvlistValue" in value:
        return otel_attrs_to_dict(value.get("kvlistValue", {}).get("values") or [])
    return None


def otel_attrs_to_dict(attrs: Iterable[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for attr in attrs or []:
        key = attr.get("key")
        if key:
            result[str(key)] = otel_value(attr.get("value"))
    return result


def otel_ns_to_iso(value: Any, fallback: str) -> str:
    try:
        ns = int(value)
    except (TypeError, ValueError):
        return fallback
    if ns <= 0:
        return fallback
    return dt.datetime.fromtimestamp(ns / 1_000_000_000, dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def otel_numeric_value(point: dict[str, Any]) -> float | None:
    if "asInt" in point:
        return float(point["asInt"])
    if "asDouble" in point:
        return float(point["asDouble"])
    return None


def otel_status_is_usage(status: Any) -> bool:
    normalized = str(status or "").strip().lower().replace("-", "_")
    return normalized not in OTEL_NON_USAGE_STATUSES


def otel_series_key(metric: str, attrs: dict[str, Any], start_time: Any) -> str:
    payload = {
        "metric": metric,
        "attrs": sorted((str(key), str(value)) for key, value in attrs.items()),
        "start_time_unix_nano": str(start_time or ""),
    }
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def otel_point_id(metric: str, series_key: str, point: dict[str, Any], value: float) -> str:
    payload = {
        "metric": metric,
        "series_key": series_key,
        "start": str(point.get("startTimeUnixNano") or ""),
        "time": str(point.get("timeUnixNano") or ""),
        "value": value,
    }
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def metric_point_delta(
    con: sqlite3.Connection,
    *,
    point_id: str,
    series_key: str,
    metric: str,
    time_ns: int,
    value: float,
    temporality: int | None,
    seen_at: str,
) -> int:
    if con.execute("select 1 from otel_metric_points where point_id = ?", (point_id,)).fetchone():
        return 0
    previous = con.execute(
        """
        select value from otel_metric_points
        where series_key = ? and time_unix_nano < ?
        order by time_unix_nano desc
        limit 1
        """,
        (series_key, time_ns),
    ).fetchone()
    if temporality == 1:
        delta = max(0.0, value)
    elif previous:
        delta = max(0.0, value - float(previous["value"]))
    else:
        delta = max(0.0, value)
    con.execute(
        """
        insert into otel_metric_points (
            point_id, seen_at, metric, series_key, time_unix_nano, value, temporality, delta
        ) values (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (point_id, seen_at, metric, series_key, time_ns, value, temporality, delta),
    )
    return int(delta)


def iter_otel_resource_metrics(payload: dict[str, Any]) -> Iterable[tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]]:
    for resource_metric in payload.get("resourceMetrics") or []:
        resource_attrs = otel_attrs_to_dict((resource_metric.get("resource") or {}).get("attributes") or [])
        for scope_metric in resource_metric.get("scopeMetrics") or []:
            scope_attrs = otel_attrs_to_dict((scope_metric.get("scope") or {}).get("attributes") or [])
            for metric in scope_metric.get("metrics") or []:
                yield resource_attrs, scope_attrs, metric, scope_metric


def otel_metric_events(
    con: sqlite3.Connection,
    payload: dict[str, Any],
    *,
    received_at: str,
    source_file: Path,
    since: str | None,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for resource_attrs, scope_attrs, metric_obj, _scope_metric in iter_otel_resource_metrics(payload):
        metric_name = str(metric_obj.get("name") or "")
        if "skill.injected" not in metric_name:
            continue
        sum_obj = metric_obj.get("sum") or {}
        temporality = sum_obj.get("aggregationTemporality")
        for point in sum_obj.get("dataPoints") or []:
            value = otel_numeric_value(point)
            if value is None:
                continue
            point_attrs = otel_attrs_to_dict(point.get("attributes") or [])
            attrs = {**resource_attrs, **scope_attrs, **point_attrs}
            skill = str(attrs.get("skill") or attrs.get("skill.name") or "").strip()
            if not skill:
                continue
            status = attrs.get("status")
            if not otel_status_is_usage(status):
                continue
            event_ts = otel_ns_to_iso(point.get("timeUnixNano"), received_at)
            if since and event_ts and event_ts < since:
                continue
            try:
                time_ns = int(point.get("timeUnixNano") or 0)
            except (TypeError, ValueError):
                time_ns = 0
            series_key = otel_series_key(metric_name, attrs, point.get("startTimeUnixNano"))
            point_id = otel_point_id(metric_name, series_key, point, value)
            delta = metric_point_delta(
                con,
                point_id=point_id,
                series_key=series_key,
                metric=metric_name,
                time_ns=time_ns,
                value=value,
                temporality=int(temporality) if temporality is not None else None,
                seen_at=received_at,
            )
            for index in range(delta):
                snippet = {
                    "metric": metric_name,
                    "status": status,
                    "value": value,
                    "delta": delta,
                    "source": "official_otel_metric",
                }
                add_event(
                    events,
                    timestamp=event_ts,
                    session_id=str(attrs.get("conversation_id") or attrs.get("session_id") or "official-otel"),
                    turn_id=f"official-otel:{point_id}:{index + 1}",
                    source_file=source_file,
                    skill=skill,
                    signal="official_otel_skill_injected",
                    confidence=100,
                    raw_id=f"{point_id}:{index + 1}",
                    snippet=json.dumps(snippet, ensure_ascii=False),
                )
    return events


def iter_otel_log_records(payload: dict[str, Any]) -> Iterable[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]]:
    for resource_log in payload.get("resourceLogs") or []:
        resource_attrs = otel_attrs_to_dict((resource_log.get("resource") or {}).get("attributes") or [])
        for scope_log in resource_log.get("scopeLogs") or []:
            scope_attrs = otel_attrs_to_dict((scope_log.get("scope") or {}).get("attributes") or [])
            for record in scope_log.get("logRecords") or []:
                yield resource_attrs, scope_attrs, record


def otel_log_events(
    payload: dict[str, Any],
    *,
    received_at: str,
    source_file: Path,
    since: str | None,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for resource_attrs, scope_attrs, record in iter_otel_log_records(payload):
        attrs = {**resource_attrs, **scope_attrs, **otel_attrs_to_dict(record.get("attributes") or [])}
        body = otel_value(record.get("body"))
        text = json.dumps({"body": body, "attributes": attrs}, ensure_ascii=False)
        if "skill.injected" not in text:
            continue
        skill = str(attrs.get("skill") or attrs.get("skill.name") or "").strip()
        if not skill:
            match = re.search(r"skill[\"']?\s*[:=]\s*[\"']?([A-Za-z0-9:_-]+)", text)
            skill = match.group(1) if match else ""
        if not skill:
            continue
        status = attrs.get("status")
        if not otel_status_is_usage(status):
            continue
        event_ts = otel_ns_to_iso(record.get("timeUnixNano") or record.get("observedTimeUnixNano"), received_at)
        if since and event_ts and event_ts < since:
            continue
        raw_id = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()
        add_event(
            events,
            timestamp=event_ts,
            session_id=str(attrs.get("conversation_id") or attrs.get("session_id") or "official-otel"),
            turn_id=str(attrs.get("turn_id") or f"official-otel-log:{raw_id[:16]}"),
            source_file=source_file,
            skill=skill,
            signal="official_otel_skill_log",
            confidence=100,
            raw_id=raw_id,
            snippet=text,
        )
    return events


def import_otel_events(con: sqlite3.Connection, otel_file: Path = OTEL_JSONL_PATH, since: str | None = None) -> tuple[int, int]:
    if not otel_file.exists():
        return 0, 0
    events: list[dict[str, Any]] = []
    try:
        handle = otel_file.open("r", encoding="utf-8", errors="replace")
    except OSError:
        return 0, 0
    with handle:
        for line in handle:
            try:
                envelope = json.loads(line)
            except json.JSONDecodeError:
                continue
            received_at = envelope.get("received_at") or utc_now()
            payload = envelope.get("payload") if isinstance(envelope.get("payload"), dict) else envelope
            if not isinstance(payload, dict):
                continue
            events.extend(otel_metric_events(con, payload, received_at=received_at, source_file=otel_file, since=since))
            events.extend(otel_log_events(payload, received_at=received_at, source_file=otel_file, since=since))
    inserted, total = store_events(con, events)
    con.commit()
    return inserted, total


def sync_usage(con: sqlite3.Connection, args: argparse.Namespace) -> tuple[int, int]:
    source = getattr(args, "source", "auto")
    since = getattr(args, "since", None)
    otel_file = getattr(args, "otel_file", OTEL_JSONL_PATH)
    inserted = 0
    total = 0
    use_official = source in {"official", "both"} or (source == "auto" and otel_file.exists() and otel_file.stat().st_size > 0)
    use_logs = source in {"logs", "both"} or (source == "auto" and not use_official)
    if use_official:
        new_inserted, new_total = import_otel_events(con, otel_file=otel_file, since=since)
        inserted += new_inserted
        total += new_total
    if use_logs:
        new_inserted, new_total = store_events(con, scan_sessions(since=since))
        inserted += new_inserted
        total += new_total
    return inserted, total


def source_predicate(source: str, *, prefix: str = "") -> str:
    column = f"{prefix}signal" if prefix else "signal"
    if source == "official":
        return f"{column} like 'official_otel_%'"
    if source == "logs":
        return f"{column} not like 'official_otel_%'"
    return ""


def cmd_scan(args: argparse.Namespace) -> None:
    con = connect(args.db)
    if args.rebuild:
        con.execute("delete from usage_events")
        con.execute("delete from otel_metric_points")
        con.commit()
    inserted, total = sync_usage(con, args)
    print(f"Source: {args.source}")
    print(f"Scanned events: {total}")
    print(f"New events stored: {inserted}")
    print(f"Database: {args.db}")


def usage_rows(con: sqlite3.Connection, limit: int, source: str = "auto") -> list[sqlite3.Row]:
    source_where = source_predicate(source)
    usage_where = f"where {source_where}" if source_where else ""
    return list(
        con.execute(
            f"""
            with usage as (
                select
                    skill,
                    count(*) as usage_signals,
                    count(distinct turn_id) as usage_turns,
                    max(event_ts) as last_seen,
                    sum(case when signal in ('skill_md_read','plugin_tool_call','system_tool_call','official_otel_skill_injected','official_otel_skill_log') then 1 else 0 end) as actual_signals,
                    sum(case when signal in ('assistant_declared','command_evidence') then 1 else 0 end) as inferred_signals,
                    sum(case when signal in ('user_named','task_alias') then 1 else 0 end) as mention_signals
                from usage_events
                {usage_where}
                group by skill
            ),
            sf as (
                select
                    skill,
                    sum(case when rating = 'useful' then 1 else 0 end) as useful_feedback,
                    sum(case when rating = 'ok' then 1 else 0 end) as ok_feedback,
                    sum(case when rating = 'not_useful' then 1 else 0 end) as not_useful_feedback,
                    sum(case when rating = 'unneeded' then 1 else 0 end) as unneeded_feedback
                from skill_feedback
                group by skill
            )
            select
                usage.skill,
                usage.usage_signals,
                usage.usage_turns,
                usage.actual_signals,
                usage.inferred_signals,
                usage.mention_signals,
                usage.last_seen,
                coalesce(sf.useful_feedback, 0) as useful_feedback,
                coalesce(sf.ok_feedback, 0) as ok_feedback,
                coalesce(sf.not_useful_feedback, 0) as not_useful_feedback,
                coalesce(sf.unneeded_feedback, 0) as unneeded_feedback
            from usage
            left join sf on sf.skill = usage.skill
            order by usage.usage_signals desc, usage.usage_turns desc, usage.skill asc
            limit ?
            """,
            (limit,),
        )
    )


def cmd_report(args: argparse.Namespace) -> None:
    con = connect(args.db)
    if not args.no_scan:
        sync_usage(con, args)
    rows = usage_rows(con, args.limit, args.source)
    if args.json:
        print(json.dumps([dict(row) for row in rows], ensure_ascii=False, indent=2))
        return
    print(f"Database: {args.db}")
    print("Skill usage report")
    print("-" * 96)
    print(f"{'skill':28} {'signals':>7} {'turns':>5} {'actual':>6} {'infer':>5} {'mentions':>8} {'feedback':>18} last_seen")
    print("-" * 96)
    for row in rows:
        feedback = (
            f"+{row['useful_feedback']}/"
            f"~{row['ok_feedback']}/"
            f"-{row['not_useful_feedback']}/"
            f"skip{row['unneeded_feedback']}"
        )
        print(
            f"{row['skill'][:28]:28} "
            f"{row['usage_signals']:7} "
            f"{row['usage_turns']:5} "
            f"{row['actual_signals']:6} "
            f"{row['inferred_signals']:5} "
            f"{row['mention_signals']:8} "
            f"{feedback:18} "
            f"{row['last_seen'] or ''}"
        )
    print()
    print("Feedback format: + useful / ~ ok / - not useful / skip unneeded.")
    print("Overall turn feedback is not copied to every skill unless skill-level feedback is explicit.")


def skill_trend_rows(con: sqlite3.Connection, now: dt.datetime, source: str = "auto") -> tuple[list[dict[str, Any]], dict[str, str]]:
    cut7 = iso_days_ago(now, 7)
    cut14 = iso_days_ago(now, 14)
    cut30 = iso_days_ago(now, 30)
    cut60 = iso_days_ago(now, 60)
    windows = {
        "generated_at": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "cutoff_7d": cut7,
        "cutoff_prev_7d": cut14,
        "cutoff_30d": cut30,
        "cutoff_prev_30d": cut60,
    }
    source_where = source_predicate(source)
    usage_where = f"where {source_where}" if source_where else ""
    raw_rows = list(
        con.execute(
            f"""
            select
                skill,
                count(*) as total_signals,
                count(distinct turn_id) as total_turns,
                max(event_ts) as last_seen,
                sum(case when event_ts >= ? then 1 else 0 end) as signals_7d,
                count(distinct case when event_ts >= ? and turn_id is not null and turn_id <> '' then turn_id end) as turns_7d,
                sum(case when event_ts >= ? and event_ts < ? then 1 else 0 end) as prev_signals_7d,
                count(distinct case when event_ts >= ? and event_ts < ? and turn_id is not null and turn_id <> '' then turn_id end) as prev_turns_7d,
                sum(case when event_ts >= ? then 1 else 0 end) as signals_30d,
                count(distinct case when event_ts >= ? and turn_id is not null and turn_id <> '' then turn_id end) as turns_30d,
                sum(case when event_ts >= ? and event_ts < ? then 1 else 0 end) as prev_signals_30d,
                count(distinct case when event_ts >= ? and event_ts < ? and turn_id is not null and turn_id <> '' then turn_id end) as prev_turns_30d,
                sum(case when event_ts >= ? and signal in ('skill_md_read','plugin_tool_call','system_tool_call','official_otel_skill_injected','official_otel_skill_log') then 1 else 0 end) as actual_30d,
                sum(case when event_ts >= ? and signal in ('assistant_declared','command_evidence') then 1 else 0 end) as inferred_30d,
                sum(case when event_ts >= ? and signal in ('user_named','task_alias') then 1 else 0 end) as mentions_30d
            from usage_events
            {usage_where}
            group by skill
            """,
            (
                cut7,
                cut7,
                cut14,
                cut7,
                cut14,
                cut7,
                cut30,
                cut30,
                cut60,
                cut30,
                cut60,
                cut30,
                cut30,
                cut30,
                cut30,
            ),
        )
    )
    path_map = discover_skill_path_map()
    row_map: dict[str, dict[str, Any]] = {row["skill"]: dict(row) for row in raw_rows}
    all_skills = set(path_map) | set(row_map)
    numeric_fields = [
        "total_signals",
        "total_turns",
        "signals_7d",
        "turns_7d",
        "prev_signals_7d",
        "prev_turns_7d",
        "signals_30d",
        "turns_30d",
        "prev_signals_30d",
        "prev_turns_30d",
        "actual_30d",
        "inferred_30d",
        "mentions_30d",
    ]
    rows: list[dict[str, Any]] = []
    for skill in sorted(all_skills):
        data = row_map.get(skill, {"skill": skill, "last_seen": ""})
        for field in numeric_fields:
            data[field] = int(data.get(field) or 0)
        paths = sorted(path_map.get(skill, []))
        data["last_seen"] = data.get("last_seen") or ""
        data["installed"] = bool(paths)
        data["paths"] = paths
        data["source"] = skill_source_label(paths)
        data["protected"] = is_cleanup_protected(skill, paths)
        data["delta_turns_7d"] = data["turns_7d"] - data["prev_turns_7d"]
        data["delta_signals_7d"] = data["signals_7d"] - data["prev_signals_7d"]
        data["delta_turns_30d"] = data["turns_30d"] - data["prev_turns_30d"]
        data["delta_signals_30d"] = data["signals_30d"] - data["prev_signals_30d"]
        rows.append(data)
    return rows, windows


def trend_sort_key(row: dict[str, Any]) -> tuple[int, int, int, int, str]:
    return (
        -row["signals_30d"],
        -row["turns_30d"],
        -row["signals_7d"],
        -row["total_signals"],
        row["skill"],
    )


def cleanup_suggestions(
    rows: list[dict[str, Any]],
    *,
    stale_days: int,
    now: dt.datetime,
    limit: int,
) -> dict[str, list[dict[str, Any]]]:
    cutoff = iso_days_ago(now, stale_days)
    unused: list[dict[str, Any]] = []
    stale: list[dict[str, Any]] = []
    protected_or_managed: list[dict[str, Any]] = []
    for row in rows:
        if not row["installed"]:
            continue
        last_seen = row["last_seen"]
        never_used = row["total_signals"] == 0
        stale_used = bool(last_seen) and last_seen < cutoff
        if not never_used and not stale_used:
            continue
        reason = "never detected in selected source" if never_used else f"no detected use since {cutoff}"
        item = {
            "skill": row["skill"],
            "source": row["source"],
            "total_turns": row["total_turns"],
            "total_signals": row["total_signals"],
            "last_seen": last_seen,
            "reason": reason,
            "protected": row["protected"],
            "paths": row["paths"],
        }
        if row["protected"]:
            protected_or_managed.append(item)
        elif never_used:
            unused.append(item)
        else:
            stale.append(item)

    unused.sort(key=lambda item: (item["source"], item["skill"]))
    stale.sort(key=lambda item: (item["last_seen"] or "", item["skill"]))
    protected_or_managed.sort(key=lambda item: (item["source"], item["skill"]))
    return {
        "unused_candidates": unused[:limit],
        "stale_candidates": stale[:limit],
        "protected_or_managed": protected_or_managed[:limit],
    }


def format_signed(value: int) -> str:
    if value > 0:
        return f"+{value}"
    return str(value)


def print_cleanup_section(cleanup: dict[str, list[dict[str, Any]]], stale_days: int) -> None:
    print()
    print("Cleanup suggestions (review only; nothing is deleted)")
    print("-" * 96)
    sections = [
        ("Unused installed skills to review", cleanup["unused_candidates"]),
        (f"Cold installed skills to review (no use in {stale_days}d)", cleanup["stale_candidates"]),
        ("Protected or managed unused/cold skills", cleanup["protected_or_managed"]),
    ]
    for title, items in sections:
        print(title + ":")
        if not items:
            print("  none")
            continue
        for item in items:
            last_seen = item["last_seen"] or "never"
            print(
                f"  - {item['skill']} "
                f"[{item['source']}; turns={item['total_turns']}; last={last_seen}] "
                f"{item['reason']}"
            )
    print()
    print("Tip: prefer archiving or disabling reviewed local skills before deleting their folders.")


def cmd_trends(args: argparse.Namespace) -> None:
    con = connect(args.db)
    if not args.no_scan:
        sync_usage(con, args)
    now = dt.datetime.now(dt.timezone.utc)
    rows, windows = skill_trend_rows(con, now, args.source)
    active_rows = [row for row in rows if row["total_signals"] > 0]
    active_rows.sort(key=trend_sort_key)
    cleanup = cleanup_suggestions(rows, stale_days=args.stale_days, now=now, limit=args.cleanup_limit)
    if args.json:
        payload = {
            "database": str(args.db),
            "windows": windows,
            "trends": active_rows[: args.limit],
            "cleanup": cleanup,
            "notes": [
                "Counts are estimates based on local Codex logs.",
                "Cleanup suggestions are review-only and do not delete files.",
            ],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    print(f"Database: {args.db}")
    print("Skill usage trends")
    print(f"Generated: {windows['generated_at']}")
    print(f"Windows: 7d since {windows['cutoff_7d']}; 30d since {windows['cutoff_30d']}")
    print("-" * 112)
    print(
        f"{'skill':30} {'7d sig':>6} {'7d trn':>6} {'7d d':>6} "
        f"{'30d sig':>7} {'30d trn':>7} {'actual':>6} {'infer':>5} {'mentions':>8} {'total':>6} last_seen"
    )
    print("-" * 112)
    for row in active_rows[: args.limit]:
        print(
            f"{row['skill'][:30]:30} "
            f"{row['signals_7d']:6} "
            f"{row['turns_7d']:6} "
            f"{format_signed(row['delta_turns_7d']):>6} "
            f"{row['signals_30d']:7} "
            f"{row['turns_30d']:7} "
            f"{row['actual_30d']:6} "
            f"{row['inferred_30d']:5} "
            f"{row['mentions_30d']:8} "
            f"{row['total_turns']:6} "
            f"{row['last_seen'] or ''}"
        )
    print()
    print("7d d compares the last 7 days against the previous 7 days by distinct turns.")
    print("Counts are estimates based on local logs; actual/infer/mentions split follows scanner confidence.")
    print_cleanup_section(cleanup, args.stale_days)


def latest_turns(con: sqlite3.Connection, limit: int, pending_only: bool = False, source: str = "auto") -> list[sqlite3.Row]:
    where = ""
    if pending_only:
        where = "where not exists (select 1 from turn_feedback tf where tf.turn_id = grouped.turn_id)"
    source_where = source_predicate(source)
    source_and = f"and {source_where}" if source_where else ""
    return list(
        con.execute(
            f"""
            with grouped as (
                select
                    turn_id,
                    session_id,
                    max(event_ts) as last_seen,
                    group_concat(distinct skill) as skills,
                    count(*) as signals
                from usage_events
                where turn_id is not null and turn_id <> ''
                {source_and}
                group by turn_id, session_id
            )
            select * from grouped
            {where}
            order by last_seen desc
            limit ?
            """,
            (limit,),
        )
    )


def cmd_latest(args: argparse.Namespace) -> None:
    con = connect(args.db)
    if not args.no_scan:
        sync_usage(con, args)
    rows = latest_turns(con, args.limit, source=args.source)
    print("Latest detected skill-use turns")
    print("-" * 80)
    for row in rows:
        print(f"{row['last_seen']}  turn={row['turn_id']}  signals={row['signals']}  skills={row['skills']}")


def cmd_pending(args: argparse.Namespace) -> None:
    con = connect(args.db)
    if not args.no_scan:
        sync_usage(con, args)
    rows = latest_turns(con, args.limit, pending_only=True, source=args.source)
    print("Turns with detected skill usage and no turn-level feedback")
    print("-" * 80)
    for row in rows:
        print(f"{row['last_seen']}  turn={row['turn_id']}  signals={row['signals']}  skills={row['skills']}")


def normalize_rating(value: str) -> str:
    key = value.strip().lower()
    normalized = RATING_ALIASES.get(key)
    if not normalized:
        allowed = ", ".join(sorted(set(RATING_ALIASES.values())))
        raise SystemExit(f"Unknown rating '{value}'. Allowed normalized ratings: {allowed}")
    return normalized


def resolve_turn(con: sqlite3.Connection, raw_turn: str | None) -> tuple[str, str | None]:
    if raw_turn and raw_turn != "latest":
        row = con.execute("select session_id from usage_events where turn_id = ? limit 1", (raw_turn,)).fetchone()
        return raw_turn, row["session_id"] if row else None
    row = latest_turns(con, 1)
    if not row:
        raise SystemExit("No skill usage turns found. Run scan first.")
    return row[0]["turn_id"], row[0]["session_id"]


def parse_skill_rating(raw: str) -> tuple[str, str, str | None]:
    if "=" not in raw:
        raise SystemExit(f"Skill rating must look like skill=rating or skill=rating:note, got '{raw}'")
    skill, rest = raw.split("=", 1)
    note = None
    if ":" in rest:
        rating, note = rest.split(":", 1)
    else:
        rating = rest
    return skill.strip(), normalize_rating(rating), note.strip() if note else None


def cmd_feedback(args: argparse.Namespace) -> None:
    con = connect(args.db)
    sync_usage(con, args)
    turn_id, session_id = resolve_turn(con, args.turn)
    rating = normalize_rating(args.rating)
    created_at = utc_now()
    con.execute(
        """
        insert into turn_feedback (
            created_at, turn_id, session_id, rating, note, best_skill, unneeded_skill
        ) values (?, ?, ?, ?, ?, ?, ?)
        """,
        (created_at, turn_id, session_id, rating, args.note, args.best, args.unneeded),
    )
    skill_rows: list[tuple[str, str, str | None]] = []
    for raw in args.skill or []:
        skill_rows.append(parse_skill_rating(raw))
    if args.best:
        skill_rows.append((args.best, "useful", "Marked as best skill for the turn."))
    if args.unneeded:
        skill_rows.append((args.unneeded, "unneeded", "Marked as unnecessary for the turn."))
    for skill, skill_rating, note in skill_rows:
        con.execute(
            """
            insert into skill_feedback (created_at, turn_id, skill, rating, note)
            values (?, ?, ?, ?, ?)
            """,
            (created_at, turn_id, skill, skill_rating, note),
        )
    con.commit()
    print(f"Recorded turn feedback: turn={turn_id}, rating={rating}")
    if skill_rows:
        print("Recorded skill feedback:")
        for skill, skill_rating, note in skill_rows:
            suffix = f" ({note})" if note else ""
            print(f"- {skill}: {skill_rating}{suffix}")
    else:
        print("No skill-level feedback was recorded. Overall feedback stays at turn level.")


def cmd_doctor(args: argparse.Namespace) -> None:
    con = connect(args.db)
    print(f"Codex home: {CODEX_HOME}")
    print(f"Database: {args.db}")
    print(f"Database ok: {con.execute('select count(*) from usage_events').fetchone()[0]} usage events")
    print(f"Official OTel JSONL: {OTEL_JSONL_PATH}")
    print(f"Official OTel JSONL exists: {OTEL_JSONL_PATH.exists()}")
    print(f"Official OTel metric points: {con.execute('select count(*) from otel_metric_points').fetchone()[0]}")
    print("Session roots:")
    for root in SESSION_ROOTS:
        count = sum(1 for _ in root.rglob("*.jsonl")) if root.exists() else 0
        print(f"- {root}: {count} jsonl files")
    print(f"Discovered skills: {len(discover_skills())}")


def cmd_watch(args: argparse.Namespace) -> None:
    con = connect(args.db)
    print(f"Watching skill usage source '{args.source}' every {args.interval} seconds. Press Ctrl+C to stop.")
    try:
        while True:
            inserted, total = sync_usage(con, args)
            if inserted:
                print(f"{utc_now()} stored {inserted} new usage events ({total} scanned)")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("Stopped watcher.")


def cmd_otel_serve(args: argparse.Namespace) -> None:
    output = args.output
    output.parent.mkdir(parents=True, exist_ok=True)

    class OTelHandler(http.server.BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            try:
                length = int(self.headers.get("content-length") or "0")
            except ValueError:
                length = 0
            body = self.rfile.read(length)
            try:
                payload = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                self.send_response(415)
                self.send_header("content-type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error":"expected OTLP/HTTP JSON; set otel exporter protocol to json"}')
                return
            envelope = {
                "received_at": utc_now(),
                "path": self.path,
                "content_type": self.headers.get("content-type"),
                "payload": payload,
            }
            with output.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(envelope, ensure_ascii=False, separators=(",", ":")) + "\n")
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.end_headers()
            self.wfile.write(b"{}")

        def do_GET(self) -> None:
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "output": str(output)}, ensure_ascii=False).encode("utf-8"))

        def log_message(self, format: str, *values: Any) -> None:
            if not args.quiet:
                super().log_message(format, *values)

    server = http.server.ThreadingHTTPServer((args.host, args.port), OTelHandler)
    if not args.quiet:
        print(f"Listening for Codex OTLP JSON on http://{args.host}:{args.port}")
        print(f"Writing raw OTLP payloads to {output}")
        print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        if not args.quiet:
            print("Stopped OTel receiver.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DB_PATH, help="SQLite database path")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_source_args(command: argparse.ArgumentParser, *, include_no_scan: bool = False) -> None:
        command.add_argument(
            "--source",
            choices=["auto", "official", "logs", "both"],
            default="auto",
            help="Usage source: official OTel JSONL, legacy session logs, both, or auto",
        )
        command.add_argument("--otel-file", type=Path, default=OTEL_JSONL_PATH, help="Official OTLP JSONL capture path")
        if include_no_scan:
            command.add_argument("--no-scan", action="store_true", help="Do not scan/import before reporting")

    scan = sub.add_parser("scan", help="Scan Codex session logs into the local database")
    scan.add_argument("--since", help="Only scan events at or after this ISO timestamp")
    scan.add_argument("--rebuild", action="store_true", help="Delete usage events before scanning")
    add_source_args(scan)
    scan.set_defaults(func=cmd_scan)

    report = sub.add_parser("report", help="Show skill usage report")
    report.add_argument("--limit", type=int, default=30)
    report.add_argument("--since", help="Only scan events at or after this ISO timestamp before reporting")
    add_source_args(report, include_no_scan=True)
    report.add_argument("--json", action="store_true", help="Emit JSON")
    report.set_defaults(func=cmd_report)

    trends = sub.add_parser("trends", help="Show 7/30 day trends and unused-skill cleanup suggestions")
    trends.add_argument("--limit", type=int, default=30)
    trends.add_argument("--cleanup-limit", type=int, default=20)
    trends.add_argument("--stale-days", type=int, default=30, help="Days without detected use before suggesting review")
    trends.add_argument("--since", help="Only scan events at or after this ISO timestamp before reporting")
    add_source_args(trends, include_no_scan=True)
    trends.add_argument("--json", action="store_true", help="Emit JSON")
    trends.set_defaults(func=cmd_trends)

    latest = sub.add_parser("latest", help="Show latest turns with skill usage")
    latest.add_argument("--limit", type=int, default=10)
    latest.add_argument("--since", help="Only scan events at or after this ISO timestamp before reporting")
    add_source_args(latest, include_no_scan=True)
    latest.set_defaults(func=cmd_latest)

    pending = sub.add_parser("pending", help="Show turns that have skill usage but no turn feedback")
    pending.add_argument("--limit", type=int, default=10)
    pending.add_argument("--since", help="Only scan events at or after this ISO timestamp before reporting")
    add_source_args(pending, include_no_scan=True)
    pending.set_defaults(func=cmd_pending)

    feedback = sub.add_parser("feedback", help="Record feedback for a turn and optionally specific skills")
    feedback.add_argument("--turn", default="latest", help="Turn id, or latest")
    feedback.add_argument("--rating", required=True, help="useful, ok, not-useful, or Chinese aliases")
    feedback.add_argument("--note", default=None)
    feedback.add_argument("--best", default=None, help="Skill that was most useful")
    feedback.add_argument("--unneeded", default=None, help="Skill that was unnecessary")
    feedback.add_argument("--skill", action="append", help="Skill-level rating: skill=rating or skill=rating:note")
    feedback.add_argument("--since", help="Only scan events at or after this ISO timestamp before recording")
    add_source_args(feedback)
    feedback.set_defaults(func=cmd_feedback)

    watch = sub.add_parser("watch", help="Poll session logs and store newly detected usage events")
    watch.add_argument("--interval", type=int, default=30)
    watch.add_argument("--since", help="Only scan events at or after this ISO timestamp")
    add_source_args(watch)
    watch.set_defaults(func=cmd_watch)

    otel_serve = sub.add_parser("otel-serve", help="Receive official Codex OTLP/HTTP JSON locally")
    otel_serve.add_argument("--host", default="127.0.0.1")
    otel_serve.add_argument("--port", type=int, default=4318)
    otel_serve.add_argument("--output", type=Path, default=OTEL_JSONL_PATH)
    otel_serve.add_argument("--quiet", action="store_true")
    otel_serve.set_defaults(func=cmd_otel_serve)

    doctor = sub.add_parser("doctor", help="Check local paths and database")
    doctor.set_defaults(func=cmd_doctor)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
