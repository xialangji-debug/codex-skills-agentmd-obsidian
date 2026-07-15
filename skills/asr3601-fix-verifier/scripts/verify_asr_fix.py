#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


def run(command: list[str] | str, cwd: Path, shell: bool = False, timeout: int = 120) -> tuple[int, str]:
    try:
        result = subprocess.run(
            command,
            cwd=str(cwd),
            shell=shell,
            text=True,
            encoding="utf-8",
            errors="replace",
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


def variant_check(repo: Path) -> tuple[int, str]:
    path = repo / ".codex-project" / "variant.md"
    if not path.exists():
        return 2, "未找到 .codex-project/variant.md；先运行 asr3601-project-onboard 生成变体指纹。"
    text = path.read_text(encoding="utf-8", errors="replace")

    def field(name: str) -> str:
        match = re.search(rf"^- `?{re.escape(name)}`?：`([^`]*)`", text, re.M)
        return match.group(1).strip() if match else ""

    current_branch = run(["git", "branch", "--show-current"], repo, timeout=60)[1].strip()
    current_commit = run(["git", "rev-parse", "--short", "HEAD"], repo, timeout=60)[1].strip()
    stored_branch, stored_commit = field("branch"), field("commit")
    issues = []
    if not stored_branch or not stored_commit:
        issues.append("指纹缺少 branch/commit")
    if stored_branch and stored_branch != current_branch:
        issues.append(f"branch 已过期：fingerprint={stored_branch}, current={current_branch}")
    if stored_commit and stored_commit != current_commit:
        issues.append(f"commit 已过期：fingerprint={stored_commit}, current={current_commit}")
    summary = [f"path={path}", f"branch={stored_branch or '缺失'}", f"commit={stored_commit or '缺失'}"]
    for name in ("yl_device_ver", "CHIP_ID", "TARGET_OS", "PS_MODE", "协议", "客户/产品变体", "构建命令", "禅道项目", "映射状态"):
        summary.append(f"{name}={field(name) or '缺失'}")
    if issues:
        summary.append("stale=" + "; ".join(issues))
        return 1, "\n".join(summary)
    summary.append("stale=no")
    return 0, "\n".join(summary)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run non-destructive ASR3601 firmware fix verification checks.")
    parser.add_argument("--repo", default=".", help="Repository path. Default: current directory.")
    parser.add_argument("--rg", action="append", default=[], help="Pattern to search with rg. Can be repeated.")
    parser.add_argument("--build-command", action="append", default=[], help="Optional build command. Can be repeated.")
    parser.add_argument("--build-timeout", type=int, default=900, help="Timeout per build command in seconds.")
    parser.add_argument("--skip-i18n-preflight", action="store_true", help="Skip automatic LVGL i18n/long-text scan.")
    parser.add_argument("--i18n-path", action="append", default=[], help="Extra UI/language file or directory for i18n preflight.")
    parser.add_argument("--i18n-language", default="vi", help="Target locale for i18n preflight. Default: vi.")
    parser.add_argument("--i18n-resolution", default="240x240", help="Target display resolution for the preflight report.")
    parser.add_argument("--i18n-strict", action="store_true", help="Treat high-severity i18n findings as verification failures.")
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

    variant_code, variant_output = variant_check(repo)
    if variant_code == 1:
        failures += 1
    print(section(f"variant fingerprint (status {variant_code})", variant_output, limit=6000))
    print()

    if not args.skip_i18n_preflight:
        script = Path(__file__).with_name("lvgl_i18n_preflight.py")
        command = [
            sys.executable,
            "-X",
            "utf8",
            str(script),
            "--repo",
            str(repo),
            "--language",
            args.i18n_language,
            "--resolution",
            args.i18n_resolution,
        ]
        for value in args.i18n_path:
            command.extend(["--path", value])
        if args.i18n_strict:
            command.append("--strict")
        code, output = run(command, repo, timeout=180)
        if code != 0:
            failures += 1
        print(section(f"LVGL i18n / long-text preflight (exit {code})", output, limit=12000))
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
