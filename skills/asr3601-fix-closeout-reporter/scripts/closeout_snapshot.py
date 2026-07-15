#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
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


def section(title: str, body: str, limit: int = 6000) -> str:
    body = body.strip() or "(empty)"
    if len(body) > limit:
        body = body[:limit] + "\n... (truncated)"
    return f"## {title}\n\n```text\n{body}\n```"


def clean_markdown_value(value: str) -> str:
    return value.strip().strip(chr(96)).strip()


def read_yl_device_ver(repo: Path) -> str:
    path = repo / "gui" / "lv_watch" / "lv_apps" / "yl" / "yl.h"
    if not path.exists():
        return "不可用"
    text = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"^\s*#define\s+yl_device_ver\s+\"([^\"]+)\"", text, re.MULTILINE)
    return match.group(1) if match else "不可用"


def canonical_variant_snapshot(
    repo: Path, live_branch: str, live_commit: str, live_dirty: str
) -> tuple[str, list[str]]:
    path = repo / ".codex-project" / "variant.md"
    if not path.exists():
        return (
            "状态：缺失\n"
            f"文件：{path}\n"
            "下一动作：先运行 asr3601-project-onboard 生成 canonical variant fingerprint",
            ["variant.md 缺失"],
        )

    text = path.read_text(encoding="utf-8-sig", errors="replace")
    fields: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"^\s*-\s*(.+?)\s*[：:]\s*(.*?)\s*$", line)
        if match:
            fields[clean_markdown_value(match.group(1))] = clean_markdown_value(match.group(2))

    fence = chr(96) * 3
    dirty_match = re.search(
        rf"-\s*dirty worktree\s*[：:]\s*\r?\n\s*{re.escape(fence)}text\s*\r?\n"
        rf"(.*?)\r?\n{re.escape(fence)}",
        text,
        re.DOTALL,
    )
    if dirty_match:
        fields["dirty worktree"] = dirty_match.group(1).strip() or "干净"

    required = (
        "verified_at",
        "repo",
        "branch",
        "commit",
        "dirty worktree",
        "yl_device_ver",
        "CHIP_ID",
        "TARGET_OS",
        "PS_MODE",
        "协议",
        "客户/产品变体",
        "构建命令",
        "禅道项目",
        "project_id",
        "product_id",
        "映射状态",
    )
    errors = [f"缺少字段：{key}" for key in required if key not in fields]

    variant_repo = fields.get("repo", "")
    if variant_repo:
        try:
            if str(Path(variant_repo).resolve()).casefold() != str(repo.resolve()).casefold():
                errors.append(f"repo 已过期：{variant_repo}")
        except OSError:
            errors.append(f"repo 无法解析：{variant_repo}")
    if fields.get("branch") != live_branch:
        errors.append(f"branch 已过期：{fields.get('branch', '未记录')} -> {live_branch}")
    if fields.get("commit") != live_commit:
        errors.append(f"commit 已过期：{fields.get('commit', '未记录')} -> {live_commit}")

    normalized_live_dirty = live_dirty.strip() or "干净"
    if fields.get("dirty worktree") != normalized_live_dirty:
        errors.append("dirty worktree 已变化")

    live_device_ver = read_yl_device_ver(repo)
    if fields.get("yl_device_ver") != live_device_ver:
        errors.append(
            f"yl_device_ver 已过期：{fields.get('yl_device_ver', '未记录')} -> {live_device_ver}"
        )

    display_keys = (
        "verified_at",
        "repo",
        "branch",
        "commit",
        "dirty worktree",
        "yl_device_ver",
        "CHIP_ID",
        "TARGET_OS",
        "PS_MODE",
        "协议",
        "客户/产品变体",
        "构建命令",
        "禅道项目",
        "project_id",
        "product_id",
        "映射状态",
    )
    lines = [f"状态：{'过期/不完整' if errors else '与当前 checkout 一致'}", f"文件：{path}"]
    for key in display_keys:
        value = fields.get(key, "未记录").replace("\r\n", "；").replace("\n", "；")
        lines.append(f"{key}：{value}")
    if errors:
        lines.append("需要先刷新：")
        lines.extend(f"- {error}" for error in errors)
        lines.append("- 运行 asr3601-project-onboard 后再继续收尾")
    return "\n".join(lines), errors


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

    _, live_branch = run(["git", "branch", "--show-current"], repo, timeout=60)
    _, live_commit = run(["git", "rev-parse", "--short", "HEAD"], repo, timeout=60)
    _, live_dirty = run(["git", "status", "--short"], repo, timeout=60)
    variant_body, variant_errors = canonical_variant_snapshot(
        repo, live_branch.strip(), live_commit.strip(), live_dirty
    )
    if variant_errors:
        failures += 1
    print(section("canonical .codex-project/variant.md", variant_body))
    print()

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
        "变体指纹：\n"
        "  repo：\n"
        "  branch / commit / dirty：\n"
        "  yl_device_ver：\n"
        "  CHIP_ID / TARGET_OS / PS_MODE：\n"
        "  协议 / 客户产品：\n"
        "  构建命令：\n"
        "  禅道映射：\n"
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
