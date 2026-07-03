#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def run(command: list[str] | str, cwd: Path, shell: bool = False, timeout: int = 120) -> tuple[int, str]:
    try:
        result = subprocess.run(
            command,
            cwd=str(cwd),
            shell=shell,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        return result.returncode, result.stdout.strip()
    except Exception as exc:
        return 999, f"{type(exc).__name__}: {exc}"


def section(title: str, body: str, limit: int = 4000) -> str:
    body = body.strip() or "(empty)"
    if len(body) > limit:
        body = body[:limit] + "\n... (truncated)"
    return f"## {title}\n\n```text\n{body}\n```"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run non-destructive ASR3601 firmware fix verification checks.")
    parser.add_argument("--repo", default=".", help="Repository path. Default: current directory.")
    parser.add_argument("--rg", action="append", default=[], help="Pattern to search with rg. Can be repeated.")
    parser.add_argument("--build-command", action="append", default=[], help="Optional build command. Can be repeated.")
    parser.add_argument("--build-timeout", type=int, default=900, help="Timeout per build command in seconds.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = Path(args.repo).resolve()
    failures = 0
    print(f"# ASR3601 Fix Verification\n\n项目路径：{repo}\n")

    git_code, git_inside = run(["git", "rev-parse", "--is-inside-work-tree"], repo, timeout=60)
    if git_code != 0 or git_inside.strip().lower() != "true":
        print(section("git repository", "不可用：当前路径不是 Git 仓库"))
        print("\n结论：无法执行 Git/diff/build 前置验证")
        return 1

    checks: list[tuple[str, list[str] | str, bool, int]] = [
        ("git status --short", ["git", "status", "--short"], False, 60),
        ("git branch --show-current", ["git", "branch", "--show-current"], False, 60),
        ("git rev-parse --short HEAD", ["git", "rev-parse", "--short", "HEAD"], False, 60),
        ("git diff --check", ["git", "diff", "--check"], False, 120),
    ]

    for title, command, shell, timeout in checks:
        code, output = run(command, repo, shell=shell, timeout=timeout)
        if code != 0 and title != "git status --short":
            failures += 1
        print(section(f"{title} (exit {code})", output))
        print()

    for pattern in args.rg:
        code, output = run(["rg", "-n", pattern], repo, timeout=120)
        if code not in (0, 1):
            failures += 1
        print(section(f"rg {pattern!r} (exit {code})", output))
        print()

    for command in args.build_command:
        code, output = run(command, repo, shell=True, timeout=args.build_timeout)
        if code != 0:
            failures += 1
        print(section(f"build: {command} (exit {code})", output, limit=8000))
        print()

    print(f"结论：{'存在失败项' if failures else '基础检查通过'}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
