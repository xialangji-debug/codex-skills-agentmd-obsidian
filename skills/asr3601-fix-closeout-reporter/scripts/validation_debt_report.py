#!/usr/bin/env python3
"""Aggregate explicit validation debt from Obsidian fix-pattern notes.

The scanner is read-only by default. It treats the last explicit
"验证状态/验证结论" field in each note as authoritative, so historical
verification instructions in an already-closed note are not reopened.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path


DEFAULT_FIX_PATTERNS = (
    Path.home() / "Documents" / "Obsidian" / "CodexVault" / "Codex" / "fix-patterns"
)

STATUS_RE = re.compile(
    r"^\s*-\s*(?:验证状态|验证结论)\s*[：:]\s*(?P<value>.+?)\s*$"
)
FIELD_RES = {
    "project_path": re.compile(r"^\s*-\s*项目路径\s*[：:]\s*(?P<value>.+?)\s*$"),
    "project": re.compile(r"^\s*-\s*项目\s*[：:]\s*(?P<value>.+?)\s*$"),
    "current_branch": re.compile(r"^\s*-\s*当前分支\s*[：:]\s*(?P<value>.+?)\s*$"),
    "target_branch": re.compile(r"^\s*-\s*目标分支\s*[：:]\s*(?P<value>.+?)\s*$"),
    "commit": re.compile(
        r"^\s*-\s*(?:当前提交|当前短提交|短提交|commit)\s*[：:]\s*(?P<value>.+?)\s*$",
        re.IGNORECASE,
    ),
}


@dataclass(frozen=True)
class Debt:
    source: Path
    title: str
    project: str
    branch: str
    commit: str
    status: str
    passed_gates: tuple[str, ...]
    pending: tuple[str, ...]
    priority: str
    next_action: str


def clean_value(value: str) -> str:
    value = value.strip().strip(chr(96)).strip()
    return re.sub(r"\s+", " ", value)


def unique(values: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))


def extract_passed_gates(status: str) -> tuple[str, ...]:
    gates: list[str] = []
    if re.search(r"git\s+diff\s+--check.*通过", status, re.IGNORECASE):
        gates.append("git diff --check")
    if re.search(r"(?:对象级\s*ARMCC|ARMCC\s*对象).*编译通过", status, re.IGNORECASE):
        gates.append("ARMCC 对象编译")
    if re.search(r"改动文件已?编译通过", status):
        gates.append("改动文件编译")
    if re.search(r"(?:完整固件|全量(?:清理)?).*?(?:构建|编译).*?(?:通过|已验证)", status):
        gates.append("完整固件构建")
    if re.search(r"增量重编译通过", status):
        gates.append("增量重编译")
    if re.search(r"(?:发布已验证|已发布|发布\s*fnOS|已出版本)", status):
        gates.append("发布/出版本")
    if re.search(r"已推送\s*Git|Git\s*远端", status, re.IGNORECASE):
        gates.append("Git 远端")
    return unique(gates) or ("未记录已通过门槛",)


def extract_pending(status: str) -> tuple[str, ...]:
    pending: list[str] = []
    if re.search(r"(?:^|[；;（(，,])\s*未验证|尚未验证|验证未完成", status):
        pending.append("整体验证未完成")
    if re.search(r"(?:license|许可证|授权).*(?:缺失|不可用|阻断)", status, re.IGNORECASE):
        pending.append("授权环境构建")
    if re.search(
        r"(?:整包|完整固件|后处理).*?(?:失败|停止|阻断|未通过)",
        status,
        re.IGNORECASE,
    ):
        pending.append("完整固件/整包")

    protocol_pending = bool(
        re.search(r"(?:平台|协议).*?日志.*?待|日志待验证|待.*?(?:平台|协议).*?日志", status)
    )
    if protocol_pending:
        pending.append("真机/平台协议日志")

    device_pending = bool(
        re.search(
            r"(?:待真机|真机.*?(?:待测试|待验证|待回归)|"
            r"实机.*?(?:待测试|待验证|待回归)|设备.*?(?:待测试|待验证|待回归))",
            status,
        )
    )
    if device_pending and not protocol_pending:
        pending.append("真机回归")
    if re.search(r"待回归", status) and not device_pending:
        pending.append("回归验证")
    if not pending and re.search(r"(?:待测试|待验证|阻断|失败|停止)", status):
        pending.append("验证未完成")
    return unique(pending)


def classify_priority(status: str, passed: tuple[str, ...], pending: tuple[str, ...]) -> str:
    if not pending:
        return ""
    joined = "；".join(pending)
    if (
        "整体验证未完成" in pending
        or "授权环境构建" in pending
        or "完整固件/整包" in pending
        or ("发布/出版本" in passed and "真机回归" in pending)
    ):
        return "P0"
    if "日志" in joined or "真机" in joined or "回归" in joined:
        return "P1"
    return "P2"


def next_action_for(title: str, status: str, pending: tuple[str, ...]) -> str:
    joined = "；".join(pending)
    if re.search(r"ARM\s*Compiler\s*5.*license|license.*ARM\s*Compiler\s*5", status, re.IGNORECASE):
        return "在具备 ARM Compiler 5 license 的环境重跑目标构建，成功后执行笔记中的场景回归"
    if re.search(r"xzcat", status, re.IGNORECASE):
        return "补齐 xzcat 或等价工具后重跑整包后处理，再执行目标真机验证"
    if "完整固件/整包" in pending:
        return "修复构建环境阻断并重跑完整固件/整包验证"
    if "日志" in joined:
        return "按笔记复现目标场景，采集真机与平台协议日志并确认交互闭环"
    if "真机回归" in pending:
        if re.search(r"低电|10/5/2", title, re.IGNORECASE):
            return "真机覆盖 10%/5%/2%、跨档、断网恢复和充电重置"
        if re.search(r"日历|星期|weekday", title, re.IGNORECASE):
            return "在目标语言真机检查七列显示、月份切换并回归中英文"
        return "按笔记验证方法完成目标版本真机回归，并回写验证状态"
    if "整体验证未完成" in pending:
        return "完成最窄可用构建与目标场景验证，并回写明确验证层级"
    return "按笔记验证方法完成剩余验证并回写结果"


def parse_note(path: Path) -> tuple[Debt | None, bool]:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    lines = text.splitlines()
    status_hits: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        match = STATUS_RE.match(line)
        if match:
            status_hits.append((index, clean_value(match.group("value"))))
    if not status_hits:
        return None, False

    status_index, status = status_hits[-1]
    fields: dict[str, str] = {}
    for line in lines[: status_index + 1]:
        for key, pattern in FIELD_RES.items():
            match = pattern.match(line)
            if match:
                fields[key] = clean_value(match.group("value"))

    title = path.stem
    for line in lines:
        if line.startswith("# "):
            title = clean_value(line[2:])
            break

    project = fields.get("project_path") or fields.get("project") or "未记录"
    branch = fields.get("current_branch") or fields.get("target_branch") or "未记录"
    commit = fields.get("commit", "未记录")
    passed = extract_passed_gates(status)
    pending = extract_pending(status)
    if not pending:
        return None, True

    return (
        Debt(
            source=path,
            title=title,
            project=project,
            branch=branch,
            commit=commit,
            status=status,
            passed_gates=passed,
            pending=pending,
            priority=classify_priority(status, passed, pending),
            next_action=next_action_for(title, status, pending),
        ),
        True,
    )


def scan(root: Path) -> tuple[list[Debt], int, int]:
    debts: list[Debt] = []
    explicit_count = 0
    files = sorted(root.glob("*.md"), key=lambda path: path.name.lower())
    for path in files:
        debt, has_explicit_status = parse_note(path)
        if has_explicit_status:
            explicit_count += 1
        if debt is not None:
            debts.append(debt)
    debts.sort(key=lambda debt: (debt.priority, debt.project.lower(), debt.title.lower()))
    return debts, len(files), explicit_count


def md_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def render_report(debts: list[Debt], root: Path, file_count: int, explicit_count: int) -> str:
    closed_count = explicit_count - len(debts)
    lines = [
        "# ASR360x 验证债务报告",
        "",
        f"- 扫描目录：{root}",
        f"- Markdown 文件：{file_count}",
        f"- 含显式验证状态：{explicit_count}",
        f"- 当前验证债务：{len(debts)}",
        f"- 已闭环排除：{closed_count}",
        "- 判定规则：每篇笔记只采纳最后一个“验证状态/验证结论”字段；正文中的历史验证说明不重新开债。",
        "",
    ]
    if not debts:
        lines.extend(["## 结论", "", "未发现带显式状态的当前验证债务。", ""])
        return "\n".join(lines)

    for priority in ("P0", "P1", "P2"):
        group = [debt for debt in debts if debt.priority == priority]
        if not group:
            continue
        lines.extend(
            [
                f"## {priority} 验证债务",
                "",
                "| 项目 | 事项 | 分支 | commit | 已过门槛 | 待办 | 下一动作 | 来源 |",
                "|---|---|---|---|---|---|---|---|",
            ]
        )
        for debt in group:
            row = [
                debt.project,
                debt.title,
                debt.branch,
                debt.commit,
                "；".join(debt.passed_gates),
                "；".join(debt.pending),
                debt.next_action,
                debt.source.name,
            ]
            lines.append("| " + " | ".join(md_cell(value) for value in row) + " |")
        lines.append("")
    return "\n".join(lines)


def render_open_loops_draft(debts: list[Debt], root: Path) -> str:
    lines = [
        "# Open Loops 验证债务草案",
        "",
        f"> 来源：{root}",
        "> 这是只读扫描生成的草案；人工确认后再合入 open-loops.md。不得据此自动升级验证状态或关闭禅道。",
        "",
        "## 验证债务",
        "",
    ]
    if not debts:
        lines.append("- 暂无带显式状态的当前验证债务。")
        return "\n".join(lines) + "\n"
    for debt in debts:
        lines.extend(
            [
                f"- [ ] [{debt.priority}] {debt.title}",
                f"  - 项目：{debt.project}",
                f"  - 分支 / commit：{debt.branch} / {debt.commit}",
                f"  - 已过门槛：{'；'.join(debt.passed_gates)}",
                f"  - 待办：{'；'.join(debt.pending)}",
                f"  - 下一动作：{debt.next_action}",
                f"  - 来源：{debt.source.name}",
            ]
        )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read explicit validation states from Obsidian fix-patterns and report current debt."
    )
    parser.add_argument(
        "--fix-patterns",
        default=str(DEFAULT_FIX_PATTERNS),
        help="Path to Codex/fix-patterns. Default: user Obsidian Codex memory.",
    )
    parser.add_argument(
        "--open-loops-draft",
        help="Optional output path for a standalone open-loops Markdown draft. No file is written by default.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.fix_patterns).expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"fix-patterns directory does not exist: {root}")

    debts, file_count, explicit_count = scan(root)
    print(render_report(debts, root, file_count, explicit_count))

    if args.open_loops_draft:
        draft_path = Path(args.open_loops_draft).expanduser().resolve()
        draft_path.parent.mkdir(parents=True, exist_ok=True)
        draft_path.write_text(render_open_loops_draft(debts, root), encoding="utf-8")
        print(f"\nOpen-loops draft written: {draft_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
