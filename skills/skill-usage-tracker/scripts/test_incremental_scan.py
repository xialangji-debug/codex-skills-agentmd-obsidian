#!/usr/bin/env python3
"""Offline regression tests for incremental session scanning."""

from __future__ import annotations

import importlib.util
import json
import sqlite3
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).with_name("skill_usage_tracker.py")
SPEC = importlib.util.spec_from_file_location("skill_usage_tracker_under_test", SCRIPT)
assert SPEC and SPEC.loader
tracker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tracker)


def append(path: Path, item: dict) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(item, ensure_ascii=False) + "\n")


with tempfile.TemporaryDirectory(prefix="skill-usage-incremental-") as temp:
    root = Path(temp)
    session = root / "session.jsonl"
    db = root / "usage.sqlite"
    append(session, {"timestamp": "2026-07-16T00:00:00Z", "type": "session_meta", "payload": {"id": "s1"}})
    append(session, {"timestamp": "2026-07-16T00:00:01Z", "type": "event_msg", "payload": {"type": "task_started", "turn_id": "t1"}})
    append(session, {"timestamp": "2026-07-16T00:00:02Z", "type": "event_msg", "payload": {"type": "user_message", "message": "$zentao-bug-triage 抓 bug"}})

    tracker.SESSION_ROOTS = [root]
    tracker.discover_skills = lambda: ["zentao-bug-triage"]
    tracker.discover_skill_md_paths = lambda _skills: []
    con = tracker.connect(db)

    events, states, resets = tracker.scan_sessions(con)
    assert len(events) == 1
    assert events[0]["skill"] == "zentao-bug-triage"
    tracker.store_events(con, events, commit=False)
    tracker.store_scan_state(con, states, resets)
    con.commit()

    events, states, resets = tracker.scan_sessions(con)
    assert events == []
    assert states == []
    assert resets == []

    append(session, {"timestamp": "2026-07-16T00:00:03Z", "type": "event_msg", "payload": {"type": "task_started", "turn_id": "t2"}})
    append(session, {"timestamp": "2026-07-16T00:00:04Z", "type": "event_msg", "payload": {"type": "user_message", "message": "使用 $zentao-bug-triage"}})
    events, states, resets = tracker.scan_sessions(con)
    assert len(events) == 1
    assert events[0]["turn_id"] == "t2"
    tracker.store_events(con, events, commit=False)
    tracker.store_scan_state(con, states, resets)
    con.commit()

    assert con.execute("select count(*) from usage_events").fetchone()[0] == 2
    state = con.execute("select byte_offset, file_size from session_scan_state").fetchone()
    assert state[0] == state[1] == session.stat().st_size

    session.write_text("", encoding="utf-8")
    append(session, {"timestamp": "2026-07-16T00:00:05Z", "type": "session_meta", "payload": {"id": "s2"}})
    append(session, {"timestamp": "2026-07-16T00:00:06Z", "type": "event_msg", "payload": {"type": "task_started", "turn_id": "t3"}})
    append(session, {"timestamp": "2026-07-16T00:00:07Z", "type": "event_msg", "payload": {"type": "user_message", "message": "$zentao-bug-triage refreshed"}})
    events, states, resets = tracker.scan_sessions(con)
    assert len(events) == 1 and resets == [str(session)]
    for source_file in resets:
        con.execute("delete from usage_events where source_file = ?", (source_file,))
    tracker.store_events(con, events, commit=False)
    tracker.store_scan_state(con, states, [])
    con.commit()
    assert con.execute("select count(*) from usage_events").fetchone()[0] == 1
    con.close()

print("incremental scan tests passed")
