#!/usr/bin/env python3
"""Apply data-driven C10 Bug presets to CATStudio attachment logs."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parent.parent
EXTRACTOR = SKILL_ROOT / "scripts" / "extract_catstudio_logs.py"
PRESETS_PATH = SKILL_ROOT / "profiles" / "c10-bugs.json"


def load_presets(path: Path = PRESETS_PATH) -> dict[str, dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("C10 preset file must contain an object")
    return data


def newest_snapshot_attachments() -> Path | None:
    snapshot_root = Path(os.path.expandvars(r"%USERPROFILE%\.codex\zentao-bug-triage\snapshots"))
    candidates = [path / "attachments" for path in snapshot_root.glob("*") if (path / "attachments").is_dir()]
    return max(candidates, key=lambda path: path.parent.stat().st_mtime) if candidates else None


def find_zips(bug_dir: Path) -> list[Path]:
    return sorted(path for path in bug_dir.iterdir() if path.is_file() and path.suffix.lower() == ".zip")


def extract(bug_id: str, zip_path: Path, keywords: list[str], output_dir: Path) -> Path | None:
    per_bug_output = output_dir / f"bug-{bug_id}"
    per_bug_output.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable, "-X", "utf8", str(EXTRACTOR), str(zip_path),
        "--profile", "custom", "--output-dir", str(per_bug_output),
    ]
    for keyword in keywords:
        command.extend(["--keyword", keyword])
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}"
        raise RuntimeError(f"bug-{bug_id} extractor failed: {message}")
    outputs = sorted(per_bug_output.glob("*_catstudio_custom.tsv"))
    return outputs[0] if outputs else None


def summarize(tsv_path: Path | None, bug_id: str) -> str:
    if not tsv_path or not tsv_path.exists():
        return f"[bug-{bug_id}] no log records produced"
    records: list[str] = []
    total = 0
    with tsv_path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if line.startswith("#") or line.startswith("Index\t"):
                continue
            total += 1
            columns = line.rstrip("\n").split("\t")
            cat3 = columns[5] if len(columns) > 5 else ""
            payload = columns[12] if len(columns) > 12 else ""
            if payload.strip():
                records.append(f"  [{cat3}] {payload.strip()[:200]}")
    shown = records[:8]
    if not shown:
        return f"[bug-{bug_id}] 0 decoded keyword records (total records {total})"
    return f"[bug-{bug_id}] {total} keyword-matched records (first {len(shown)}):\n" + "\n".join(shown)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply C10 Bug presets to CATStudio attachment logs")
    parser.add_argument("--bugs", help="comma-separated preset IDs, for example 4003,4045")
    parser.add_argument("--attachments", help="selected snapshot attachments directory")
    parser.add_argument("--output-dir", help="evidence output directory")
    parser.add_argument("--keywords", help="override comma-separated keywords for every selected Bug")
    parser.add_argument("--list-presets", action="store_true", help="list available presets and exit")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    presets = load_presets()
    if args.list_presets:
        for bug_id, preset in presets.items():
            print(f"{bug_id}: {preset.get('title', '')} [{preset.get('evidence', 'log')}]")
        return 0
    if not args.bugs:
        print("ERROR: --bugs is required unless --list-presets is used", file=sys.stderr)
        return 2

    bug_ids = [value.strip() for value in args.bugs.split(",") if value.strip()]
    unknown = [bug_id for bug_id in bug_ids if bug_id not in presets]
    if unknown:
        print(f"ERROR: unknown preset(s): {', '.join(unknown)}", file=sys.stderr)
        return 2

    attachments = Path(args.attachments) if args.attachments else newest_snapshot_attachments()
    if not attachments or not attachments.is_dir():
        print("ERROR: no snapshot attachments directory found", file=sys.stderr)
        return 2

    custom_keywords = [value.strip() for value in (args.keywords or "").split(",") if value.strip()]
    output_dir = Path(args.output_dir) if args.output_dir else Path(tempfile.gettempdir()) / (
        "c10_bug_evidence_" + "_".join(bug_ids)
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_lines: list[str] = []
    files_written: list[tuple[str, str]] = []
    for bug_id in bug_ids:
        preset = presets[bug_id]
        bug_dir = attachments / f"bug-{bug_id}"
        if not bug_dir.is_dir():
            summary_lines.append(f"[bug-{bug_id}] attachment directory missing: {bug_dir}")
            continue
        zip_paths = find_zips(bug_dir)
        if not zip_paths:
            if preset.get("evidence") == "video":
                summary_lines.append(f"[bug-{bug_id}] video/image only; {preset.get('hint', 'inspect visual evidence')}")
            else:
                summary_lines.append(f"[bug-{bug_id}] no .zip log found in {bug_dir}")
            files_written.append((bug_id, "NONE"))
            continue
        keywords = custom_keywords or list(preset.get("keywords", []))
        for zip_path in zip_paths:
            try:
                tsv_path = extract(bug_id, zip_path, keywords, output_dir)
                summary_lines.append(summarize(tsv_path, bug_id))
                if tsv_path:
                    files_written.append((bug_id, str(tsv_path)))
            except RuntimeError as error:
                summary_lines.append(f"[bug-{bug_id}] {error}")

    summary_path = output_dir / "evidence_summary.md"
    summary_path.write_text(
        "# C10 Bug Log Evidence Summary\n\n"
        f"- attachment dir: {attachments}\n"
        f"- output dir: {output_dir}\n\n"
        + "\n".join(summary_lines)
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote summary: {summary_path}")
    for bug_id, file_path in files_written:
        print(f"  bug-{bug_id}: {file_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
