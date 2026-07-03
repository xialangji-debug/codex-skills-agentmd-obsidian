#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
from datetime import datetime
from pathlib import Path


VAULT_ROOT = Path(r"C:\Users\84365\Documents\Obsidian\CodexVault\Codex")
FIX_PATTERNS = VAULT_ROOT / "fix-patterns"


def run_git(args: list[str], cwd: Path) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False,
        )
    except Exception:
        return "不可用"
    value = result.stdout.strip()
    return value if result.returncode == 0 and value else "不可用"


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:80].strip("-") or datetime.now().strftime("fix-pattern-%Y%m%d-%H%M%S")


def build_note(args: argparse.Namespace, cwd: Path) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    branch = run_git(["branch", "--show-current"], cwd)
    commit = run_git(["rev-parse", "--short", "HEAD"], cwd)
    source = args.source_branch or "不可用"
    target = args.target_branch or branch
    validation = args.validation or "未验证"
    title = args.title.strip()
    return f"""# {title}

## 元信息

- 记录时间：{now}
- 项目路径：{cwd}
- 当前分支：{branch}
- 当前提交：{commit}
- 来源分支：{source}
- 目标分支：{target}
- 验证状态：{validation}

## 关键词

- TODO

## 适用范围

- TODO

## 症状

- TODO

## 根因

- TODO

## 关键文件和函数

- TODO

## 修复思路

- TODO

## 验证方法

- TODO

## 注意事项

- TODO
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create an Obsidian fix-pattern Markdown template.")
    parser.add_argument("--title", required=True, help="Human-readable note title.")
    parser.add_argument("--slug", help="File slug under fix-patterns/. Defaults to title-derived ASCII slug.")
    parser.add_argument("--cwd", default=".", help="Project path used for Git metadata. Default: current directory.")
    parser.add_argument("--source-branch", help="Source branch/version for cross-branch ports.")
    parser.add_argument("--target-branch", help="Target branch/version for cross-branch ports.")
    parser.add_argument("--validation", choices=["已验证", "未验证", "仅推测"], default="未验证")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite an existing note.")
    parser.add_argument("--dry-run", action="store_true", help="Print note without writing.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cwd = Path(args.cwd).resolve()
    slug = slugify(args.slug or args.title)
    path = FIX_PATTERNS / f"{slug}.md"
    note = build_note(args, cwd)
    if args.dry_run:
        print(note)
        return 0
    if path.exists() and not args.overwrite:
        print(f"Refusing to overwrite existing note: {path}")
        return 1
    FIX_PATTERNS.mkdir(parents=True, exist_ok=True)
    path.write_text(note, encoding="utf-8", newline="\n")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
