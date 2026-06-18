#!/usr/bin/env python3
"""Track Codex skill usage and feedback locally.

This script intentionally uses only Python's standard library. It scans local
Codex JSONL sessions, writes usage signals to SQLite, and records optional
feedback at turn or skill level.
"""

from __future__ import annotations

import argparse
import datetime as dt
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


def cmd_scan(args: argparse.Namespace) -> None:
    con = connect(args.db)
    if args.rebuild:
        con.execute("delete from usage_events")
        con.commit()
    events = scan_sessions(since=args.since)
    inserted, total = store_events(con, events)
    print(f"Scanned events: {total}")
    print(f"New events stored: {inserted}")
    print(f"Database: {args.db}")


def usage_rows(con: sqlite3.Connection, limit: int) -> list[sqlite3.Row]:
    return list(
        con.execute(
            """
            with usage as (
                select
                    skill,
                    count(*) as usage_signals,
                    count(distinct turn_id) as usage_turns,
                    max(event_ts) as last_seen,
                    sum(case when signal in ('skill_md_read','plugin_tool_call','system_tool_call') then 1 else 0 end) as actual_signals,
                    sum(case when signal in ('assistant_declared','command_evidence') then 1 else 0 end) as inferred_signals,
                    sum(case when signal in ('user_named','task_alias') then 1 else 0 end) as mention_signals
                from usage_events
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
        store_events(con, scan_sessions(since=args.since))
    rows = usage_rows(con, args.limit)
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


def latest_turns(con: sqlite3.Connection, limit: int, pending_only: bool = False) -> list[sqlite3.Row]:
    where = ""
    if pending_only:
        where = "where not exists (select 1 from turn_feedback tf where tf.turn_id = grouped.turn_id)"
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
        store_events(con, scan_sessions(since=args.since))
    rows = latest_turns(con, args.limit)
    print("Latest detected skill-use turns")
    print("-" * 80)
    for row in rows:
        print(f"{row['last_seen']}  turn={row['turn_id']}  signals={row['signals']}  skills={row['skills']}")


def cmd_pending(args: argparse.Namespace) -> None:
    con = connect(args.db)
    if not args.no_scan:
        store_events(con, scan_sessions(since=args.since))
    rows = latest_turns(con, args.limit, pending_only=True)
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
    store_events(con, scan_sessions(since=args.since))
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
    print("Session roots:")
    for root in SESSION_ROOTS:
        count = sum(1 for _ in root.rglob("*.jsonl")) if root.exists() else 0
        print(f"- {root}: {count} jsonl files")
    print(f"Discovered skills: {len(discover_skills())}")


def cmd_watch(args: argparse.Namespace) -> None:
    con = connect(args.db)
    print(f"Watching session logs every {args.interval} seconds. Press Ctrl+C to stop.")
    try:
        while True:
            inserted, total = store_events(con, scan_sessions(since=args.since))
            if inserted:
                print(f"{utc_now()} stored {inserted} new usage events ({total} scanned)")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("Stopped watcher.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DB_PATH, help="SQLite database path")
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="Scan Codex session logs into the local database")
    scan.add_argument("--since", help="Only scan events at or after this ISO timestamp")
    scan.add_argument("--rebuild", action="store_true", help="Delete usage events before scanning")
    scan.set_defaults(func=cmd_scan)

    report = sub.add_parser("report", help="Show skill usage report")
    report.add_argument("--limit", type=int, default=30)
    report.add_argument("--since", help="Only scan events at or after this ISO timestamp before reporting")
    report.add_argument("--no-scan", action="store_true", help="Do not scan before reporting")
    report.add_argument("--json", action="store_true", help="Emit JSON")
    report.set_defaults(func=cmd_report)

    latest = sub.add_parser("latest", help="Show latest turns with skill usage")
    latest.add_argument("--limit", type=int, default=10)
    latest.add_argument("--since", help="Only scan events at or after this ISO timestamp before reporting")
    latest.add_argument("--no-scan", action="store_true")
    latest.set_defaults(func=cmd_latest)

    pending = sub.add_parser("pending", help="Show turns that have skill usage but no turn feedback")
    pending.add_argument("--limit", type=int, default=10)
    pending.add_argument("--since", help="Only scan events at or after this ISO timestamp before reporting")
    pending.add_argument("--no-scan", action="store_true")
    pending.set_defaults(func=cmd_pending)

    feedback = sub.add_parser("feedback", help="Record feedback for a turn and optionally specific skills")
    feedback.add_argument("--turn", default="latest", help="Turn id, or latest")
    feedback.add_argument("--rating", required=True, help="useful, ok, not-useful, or Chinese aliases")
    feedback.add_argument("--note", default=None)
    feedback.add_argument("--best", default=None, help="Skill that was most useful")
    feedback.add_argument("--unneeded", default=None, help="Skill that was unnecessary")
    feedback.add_argument("--skill", action="append", help="Skill-level rating: skill=rating or skill=rating:note")
    feedback.add_argument("--since", help="Only scan events at or after this ISO timestamp before recording")
    feedback.set_defaults(func=cmd_feedback)

    watch = sub.add_parser("watch", help="Poll session logs and store newly detected usage events")
    watch.add_argument("--interval", type=int, default=30)
    watch.add_argument("--since", help="Only scan events at or after this ISO timestamp")
    watch.set_defaults(func=cmd_watch)

    doctor = sub.add_parser("doctor", help="Check local paths and database")
    doctor.set_defaults(func=cmd_doctor)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
