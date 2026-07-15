#!/usr/bin/env python3
"""Heuristic, read-only LVGL v7 localization and long-text preflight."""

from __future__ import annotations

import argparse
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


TEXT_SUFFIXES = {".c", ".h", ".cpp", ".cc"}


@dataclass(frozen=True)
class Finding:
    severity: str
    rule: str
    path: str
    line: int
    message: str


def git_paths(repo: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=all"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    paths: list[Path] = []
    if result.returncode != 0:
        return paths
    for raw in result.stdout.splitlines():
        if len(raw) < 4:
            continue
        rel = raw[3:].strip()
        if " -> " in rel:
            rel = rel.split(" -> ", 1)[1]
        path = repo / rel
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            paths.append(path.resolve())
    return paths


def expand_paths(repo: Path, values: list[str]) -> list[Path]:
    paths: list[Path] = []
    for value in values:
        candidate = Path(value)
        if not candidate.is_absolute():
            candidate = repo / candidate
        if candidate.is_dir():
            paths.extend(p.resolve() for p in candidate.rglob("*") if p.is_file() and p.suffix.lower() in TEXT_SUFFIXES)
        elif candidate.is_file() and candidate.suffix.lower() in TEXT_SUFFIXES:
            paths.append(candidate.resolve())
    return paths


def label_width_findings(rel: str, lines: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    call = re.compile(r"lv_label_set_long_mode\s*\(\s*([A-Za-z_]\w*)")
    for index, line in enumerate(lines):
        match = call.search(line)
        if not match:
            continue
        var = re.escape(match.group(1))
        start, end = max(0, index - 16), min(len(lines), index + 17)
        width_call = re.compile(rf"lv_obj_set_(?:width|size)\s*\(\s*{var}\b")
        width_lines = [i for i in range(start, end) if width_call.search(lines[i])]
        if not width_lines:
            findings.append(Finding("medium", "long-mode-width", rel, index + 1, f"{match.group(1)} 设置 long mode，但附近没有显式 width/size；多语言文本可能被裁切。"))
        elif min(width_lines) > index:
            findings.append(Finding("high", "long-mode-order", rel, index + 1, f"{match.group(1)} 在设置 width/size 前启用 long mode；LVGL v7 应先定宽再设 long mode。"))
    return findings


def buffer_findings(rel: str, lines: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    declaration = re.compile(r"\bchar\s+([A-Za-z_]\w*)\s*\[\s*(\d+)\s*\]")
    for index, line in enumerate(lines):
        match = declaration.search(line)
        if not match or int(match.group(2)) >= 64:
            continue
        name, size = match.group(1), int(match.group(2))
        window = "\n".join(lines[index : min(len(lines), index + 30)])
        if re.search(rf"\b(?:snprintf|sprintf)\s*\(\s*{re.escape(name)}\b", window):
            findings.append(Finding("medium", "small-format-buffer", rel, index + 1, f"格式化缓冲区 {name}[{size}] 小于 64 字节；第三方语言组合文本需核对最坏长度和结尾空字符。"))
    return findings


def text_findings(rel: str, lines: list[str], language: str) -> list[Finding]:
    findings: list[Finding] = []
    calendar = re.compile(r"WATCH_TEXT_ID_CALENDAR_(?:SUNDAY|MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY)")
    string_literal = re.compile(r'"([^"\\]*(?:\\.[^"\\]*)*)"')
    for index, line in enumerate(lines):
        if "sprintf(" in line and "snprintf(" not in line:
            findings.append(Finding("high", "unsafe-sprintf", rel, index + 1, "UI/语言路径使用 sprintf；长翻译可能溢出，改用带 sizeof 上限的 snprintf。"))
        if calendar.search(line):
            literals = string_literal.findall(line)
            for value in literals:
                if len(value) > 4:
                    findings.append(Finding("medium", "calendar-weekday-width", rel, index + 1, f"日历星期文本 {value!r} 较长；240px 固定七列界面应使用语言认可的短写。"))
        if language.lower() not in {"zh", "zh-cn", "cn"} and re.search(r"lv_label_set_(?:text|text_fmt)", line) and re.search(r"[\u4e00-\u9fff]", line):
            findings.append(Finding("medium", "hardcoded-cjk", rel, index + 1, f"目标语言 {language} 的 UI 路径出现硬编码中文；确认是否应改用 text ID。"))
    return findings


def scan_file(repo: Path, path: Path, language: str) -> list[Finding]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    try:
        rel = path.relative_to(repo).as_posix()
    except ValueError:
        rel = path.as_posix()
    lines = text.splitlines()
    return label_width_findings(rel, lines) + buffer_findings(rel, lines) + text_findings(rel, lines, language)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan changed or selected LVGL source files for localization/long-text risks.")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--path", action="append", default=[], help="Extra file or directory, relative to repo; repeatable.")
    parser.add_argument("--language", default="vi", help="Target locale used for hard-coded-text checks.")
    parser.add_argument("--resolution", default="240x240", help="Informational target resolution.")
    parser.add_argument("--strict", action="store_true", help="Return nonzero when high-severity findings exist.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = Path(args.repo).resolve()
    candidates = git_paths(repo) + expand_paths(repo, args.path)
    unique = sorted(set(candidates), key=lambda p: p.as_posix().lower())
    findings: list[Finding] = []
    for path in unique:
        findings.extend(scan_file(repo, path, args.language))

    print("# LVGL i18n / long-text preflight")
    print(f"\n- repo: `{repo}`")
    print(f"- language: `{args.language}`")
    print(f"- resolution: `{args.resolution}`")
    print(f"- scanned files: `{len(unique)}`")
    print(f"- findings: `{len(findings)}`")
    if not unique:
        print("\n未发现已修改的 C/C++ 文件；可用 `--path` 指定页面或语言资源。")
        return 0
    if findings:
        print("\n| severity | rule | location | message |")
        print("|---|---|---|---|")
        for item in sorted(findings, key=lambda x: ({"high": 0, "medium": 1}.get(x.severity, 2), x.path, x.line, x.rule)):
            message = item.message.replace("|", "\\|")
            print(f"| {item.severity} | {item.rule} | `{item.path}:{item.line}` | {message} |")
    else:
        print("\n未命中已知静态风险；仍需真机检查长文本、日期时间、页面重复进入和真实触摸路径。")
    high = any(item.severity == "high" for item in findings)
    return 1 if args.strict and high else 0


if __name__ == "__main__":
    raise SystemExit(main())
