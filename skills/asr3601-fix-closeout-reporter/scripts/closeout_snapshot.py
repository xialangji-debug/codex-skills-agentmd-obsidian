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


def section(title: str, body: str, limit: int = 6000) -> str:
    body = body.strip() or "(empty)"
    if len(body) > limit:
        body = body[:limit] + "\n... (truncated)"
    return f"## {title}\n\n```text\n{body}\n```"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect a non-destructive ASR3601 fix closeout snapshot.")
    parser.add_argument("--repo", default=".", help="Repository path. Default: current directory.")
    parser.add_argument("--rg", action="append", default=[], help="Pattern to search with rg. Can be repeated.")
    parser.add_argument("--build-command", action="append", default=[], help="Optional build/check command. Can be repeated.")
    parser.add_argument("--build-timeout", type=int, default=900, help="Timeout per build/check command in seconds.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = Path(args.repo).resolve()
    failures = 0

    print("# ASR3601 Fix Closeout Snapshot")
    print()
    print(f"项目路径：{repo}")
    print()

    git_code, git_inside = run(["git", "rev-parse", "--is-inside-work-tree"], repo, timeout=60)
    if git_code != 0 or git_inside.strip().lower() != "true":
        print(section("git repository", "不可用：当前路径不是 Git 仓库"))
        print()
        print("结论：无法执行 Git/diff 前置验证")
        return 1

    checks: list[tuple[str, list[str] | str, bool, int, bool]] = [
        ("git status --short", ["git", "status", "--short"], False, 60, False),
        ("git branch --show-current", ["git", "branch", "--show-current"], False, 60, True),
        ("git rev-parse --short HEAD", ["git", "rev-parse", "--short", "HEAD"], False, 60, True),
        ("git diff --name-status", ["git", "diff", "--name-status"], False, 60, False),
        ("git diff --cached --name-status", ["git", "diff", "--cached", "--name-status"], False, 60, False),
        ("git diff --stat", ["git", "diff", "--stat"], False, 60, False),
        ("git diff --cached --stat", ["git", "diff", "--cached", "--stat"], False, 60, False),
        ("git diff --check", ["git", "diff", "--check"], False, 120, True),
    ]

    for title, command, shell, timeout, fail_on_error in checks:
        code, output = run(command, repo, shell=shell, timeout=timeout)
        if fail_on_error and code != 0:
            failures += 1
        print(section(f"{title} (exit {code})", output))
        print()

    for pattern in args.rg:
        code, output = run(["rg", "-n", pattern], repo, timeout=120)
        if code not in (0, 1):
            failures += 1
        print(section(f"rg {pattern!r} (exit {code})", output))
        print()

    if not args.build_command:
        print(section("build/check commands", "未提供构建或最小验证命令"))
        print()

    for command in args.build_command:
        code, output = run(command, repo, shell=True, timeout=args.build_timeout)
        if code != 0:
            failures += 1
        print(section(f"build/check: {command} (exit {code})", output, limit=10000))
        print()

    print("## Closeout Report Template")
    print()
    print(
        "```text\n"
        "问题：\n"
        "根因：\n"
        "修改：\n"
        "影响范围：\n"
        "验证：\n"
        "风险：\n"
        "未覆盖项：\n"
        "记忆库：\n"
        "禅道解决说明：\n"
        "```"
    )
    print()
    print(f"结论：{'存在失败项或未通过检查' if failures else '基础收尾检查通过'}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
