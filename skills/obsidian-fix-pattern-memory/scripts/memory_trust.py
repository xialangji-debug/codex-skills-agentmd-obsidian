#!/usr/bin/env python3
"""Preview or update explicit trust metadata in one fix-pattern note."""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import subprocess
from pathlib import Path


DEFAULT_ROOT = Path.home() / "Documents" / "Obsidian" / "CodexVault" / "Codex" / "fix-patterns"


def git_value(name: str) -> str:
    args = ["git", "rev-parse", "--short", "HEAD"] if name == "commit" else ["git", "branch", "--show-current"]
    result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return result.stdout.strip() if result.returncode == 0 and result.stdout.strip() else "不可用"


def set_field(text: str, key: str, value: str) -> str:
    pattern = re.compile(rf"^-\s*{re.escape(key)}\s*[:：].*$", re.M)
    replacement = f"- {key}：{value}"
    if pattern.search(text):
        return pattern.sub(replacement, text, count=1)
    heading = re.search(r"^##\s+元信息\s*$", text, re.M)
    if heading:
        insert_at = heading.end()
        return text[:insert_at] + "\n" + replacement + text[insert_at:]
    title = re.search(r"^#\s+.+$", text, re.M)
    insert_at = title.end() if title else 0
    block = f"\n\n## 元信息\n\n{replacement}"
    return text[:insert_at] + block + text[insert_at:]


def inside(note: Path, root: Path) -> bool:
    try:
        note.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["verify", "reactivate"])
    parser.add_argument("--note", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--bug", default="")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    note = args.note.resolve()
    if not note.exists() or note.suffix.lower() != ".md":
        raise SystemExit(f"Fix-pattern note not found: {note}")
    if not inside(note, args.root):
        raise SystemExit(f"Refusing to edit note outside fix-pattern root: {note}")
    evidence = " ".join(args.evidence.split())
    if not evidence:
        raise SystemExit("--evidence cannot be empty")
    text = note.read_text(encoding="utf-8", errors="replace")
    timestamp = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    if args.action == "verify":
        for key, value in [
            ("验证状态", "已验证"),
            ("可信度", "高"),
            ("最近验证", timestamp),
            ("验证分支", git_value("branch")),
            ("验证提交", git_value("commit")),
            ("验证证据", evidence),
        ]:
            text = set_field(text, key, value)
    else:
        if not args.bug:
            raise SystemExit("--bug is required for reactivate")
        for key, value in [
            ("验证状态", "待复核"),
            ("可信度", "待复核"),
            ("复测激活 Bug", args.bug.lstrip("#")),
            ("复测激活时间", timestamp),
            ("待复核原因", evidence),
        ]:
            text = set_field(text, key, value)
    if args.write:
        temp = note.with_suffix(note.suffix + ".tmp")
        temp.write_text(text.rstrip() + "\n", encoding="utf-8")
        os.replace(temp, note)
        print(f"updated={note}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
