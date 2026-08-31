#!/usr/bin/env python3
"""Aggregate explicit validation debt from Obsidian fix-pattern notes.

The scanner is read-only by default. It treats the last explicit
"验证状态/验证结论" field in each note as authoritative, so historical
verification instructions in an already-closed note are not reopened.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
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
MANAGED_STATE_RE = re.compile(r"<!--\s*codex-fix-state-json:\s*([A-Za-z0-9_=-]+)\s*-->")


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
    domain: str = "none"
    version: str = "unknown"
    variant_id: str = ""
    target_id: str = ""
    updated_at: str = ""
    legacy: bool = False


def clean_value(value: str) -> str:
    value = value.strip().strip(chr(96)).strip()
    return re.sub(r"\s+", " ", value)


def unique(values: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))


def frontmatter_domain(text: str) -> str:
    match = re.match(r"\A---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    if not match:
        return "none"
    yaml = match.group(1)
    field = re.search(r"^domains:[ \t]*(.*?)[ \t]*$", yaml, re.M)
    if not field:
        return "none"
    inline = field.group(1).strip()
    if inline == "[]":
        return "none"
    if inline:
        values = [item.strip().strip("'\"") for item in inline.strip("[]").split(",") if item.strip()]
    else:
        tail = yaml[field.end() :]
        values = []
        for line in tail.splitlines():
            item = re.match(r"^\s+-\s*(.+?)\s*$", line)
            if item:
                values.append(item.group(1).strip().strip("'\""))
                continue
            if line.strip() and not line.startswith((" ", "\t")):
                break
    return values[0] if len(values) == 1 and values[0] in {"asr", "esp32"} else "none"


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
    domain = frontmatter_domain(text)
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
            domain=domain,
            legacy=True,
        ),
        True,
    )


def managed_state(text: str) -> dict | None:
    match = MANAGED_STATE_RE.search(text)
    if not match:
        return None
    try:
        raw = base64.urlsafe_b64decode(match.group(1).encode("ascii"))
        state = json.loads(raw.decode("utf-8"))
    except (ValueError, json.JSONDecodeError):
        return None
    return state if state.get("schema_version") == 2 else None


def managed_debts(path: Path, text: str, state: dict) -> list[Debt]:
    title = path.stem
    title_match = re.search(r"^#\s+(.+?)\s*$", text, re.M)
    if title_match:
        title = clean_value(title_match.group(1))
    debts: list[Debt] = []
    domain = frontmatter_domain(text)
    for target in state.get("targets") or []:
        relation = target.get("relation", "candidate")
        implementation = target.get("implementation", "not_applied")
        verification = target.get("verification", "unverified")
        bug_ids = target.get("bug_ids") or []
        if relation in {"candidate", "not_applicable"} or implementation in {"not_applied", "superseded"}:
            continue
        if verification == "qa_verified":
            continue
        if verification in {"device_verified", "platform_verified"} and not bug_ids:
            continue

        passed: tuple[str, ...]
        pending: tuple[str, ...]
        priority: str
        if verification == "needs_review" or implementation == "failed":
            passed = ("历史修复记录",)
            pending = ("重新激活复核",)
            priority = "P0"
            next_action = "核对同一目标的最新复现证据与代码路径，确认旧修复失败还是新变体"
        elif verification == "unverified":
            passed = ("未记录已通过门槛",)
            pending = ("静态检查与真机回归",)
            priority = "P0"
            next_action = "先完成最窄静态/构建检查，再按根因笔记执行目标真机回归"
        elif verification == "static_checked":
            passed = ("静态检查",)
            pending = ("目标构建与真机回归",)
            priority = "P1"
            next_action = "完成目标构建后执行对应版本真机回归"
        elif verification == "build_passed":
            passed = ("目标构建",)
            pending = ("真机回归",)
            priority = "P1"
            next_action = "按笔记验证方法完成目标版本真机回归并回写证据"
        else:
            passed = (("平台验证" if verification == "platform_verified" else "真机验证"),)
            pending = ("QA 关闭",)
            priority = "P1"
            next_action = "等待或核对 QA 复测结果；禅道关闭后自动升级精确目标"

        status = f"implementation={implementation}; verification={verification}; zentao={target.get('zentao', 'unknown')}"
        target_title = f"{title} [{target.get('project_key', 'unknown')} / {target.get('branch', 'unknown')}]"
        debts.append(
            Debt(
                source=path,
                title=target_title,
                project=target.get("project_key") or "未记录",
                branch=target.get("branch") or "未记录",
                commit=target.get("commit") or "未记录",
                status=status,
                passed_gates=passed,
                pending=pending,
                priority=priority,
                next_action=next_action,
                domain=domain,
                version=target.get("version") or "unknown",
                variant_id=target.get("variant_id") or "",
                target_id=target.get("target_id") or "",
                updated_at=target.get("updated_at") or "",
            )
        )
    return debts


def scan(root: Path) -> tuple[list[Debt], int, int]:
    debts: list[Debt] = []
    explicit_count = 0
    files = sorted(root.glob("*.md"), key=lambda path: path.name.lower())
    for path in files:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        state = managed_state(text)
        if state:
            explicit_count += 1
            debts.extend(managed_debts(path, text, state))
            continue
        debt, has_explicit_status = parse_note(path)
        if has_explicit_status:
            explicit_count += 1
        if debt is not None:
            debts.append(debt)
    debts.sort(key=lambda debt: (debt.priority, debt.project.lower(), debt.title.lower()))
    return debts, len(files), explicit_count


def filter_debts(
    debts: list[Debt],
    domain: str = "all",
    project: str = "",
    branch: str = "",
    priority: str = "",
    since: str = "",
) -> list[Debt]:
    project_key = project.casefold()
    branch_key = branch.casefold()
    return [
        debt
        for debt in debts
        if (domain == "all" or debt.domain == domain)
        and (not project_key or project_key in debt.project.casefold())
        and (not branch_key or branch_key in debt.branch.casefold())
        and (not priority or debt.priority == priority)
        and (not since or (bool(debt.updated_at) and debt.updated_at[:10] >= since))
    ]


def campaign_key(debt: Debt) -> str:
    if debt.legacy:
        return f"legacy|{debt.domain}|{debt.source.name}"
    return "|".join([debt.domain, debt.project, debt.branch, debt.version, debt.variant_id])


def build_campaigns(debts: list[Debt]) -> list[dict]:
    grouped: dict[str, list[Debt]] = {}
    for debt in debts:
        grouped.setdefault(campaign_key(debt), []).append(debt)
    campaigns: list[dict] = []
    for key, rows in sorted(grouped.items()):
        priorities = sorted({row.priority for row in rows})
        pending = sorted({item for row in rows for item in row.pending})
        passed = sorted({item for row in rows for item in row.passed_gates})
        statuses = " ".join(row.status for row in rows)
        hard_block = "P0" in priorities or bool(re.search(r"needs_review|unverified|failed", statuses))
        device_pending = any("真机" in item or "设备" in item for item in pending)
        if hard_block:
            state = "BLOCKED"
        elif device_pending:
            state = "DEVICE_VERIFICATION_PENDING"
        else:
            state = "READY_FOR_QA"
        campaigns.append(
            {
                "campaign_id": "VC-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:12].upper(),
                "domain": rows[0].domain,
                "project": rows[0].project,
                "branch": rows[0].branch,
                "version": rows[0].version,
                "variant_id": rows[0].variant_id or None,
                "legacy": rows[0].legacy,
                "state": state,
                "release_blocked": state in {"BLOCKED", "DEVICE_VERIFICATION_PENDING"},
                "priorities": priorities,
                "passed_gates": passed,
                "pending": pending,
                "target_ids": sorted({row.target_id for row in rows if row.target_id}),
                "required_commits": sorted({row.commit for row in rows if row.commit != "未记录"}),
                "source_notes": sorted({row.source.name for row in rows}),
                "next_actions": sorted({row.next_action for row in rows}),
            }
        )
    return campaigns


def md_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def render_report(
    debts: list[Debt],
    root: Path,
    file_count: int,
    explicit_count: int,
    filtered: bool = False,
) -> str:
    debt_note_count = len({debt.source for debt in debts})
    closed_count = max(0, explicit_count - debt_note_count)
    lines = [
        "# ASR360x 验证债务报告",
        "",
        f"- 扫描目录：{root}",
        f"- Markdown 文件：{file_count}",
        f"- 含显式验证状态：{explicit_count}",
        f"- 当前债务笔记：{debt_note_count}",
        f"- 当前债务目标行：{len(debts)}",
        f"- 已闭环笔记：{'未计算（过滤模式）' if filtered else closed_count}",
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


def render_campaign_report(campaigns: list[dict]) -> str:
    lines = [
        "# 验证债务 Campaign",
        "",
        f"- Campaign 数：{len(campaigns)}",
        f"- 发布阻断：{sum(bool(item['release_blocked']) for item in campaigns)}",
        "- 分组键：domain + project + branch + version + variant；legacy 笔记按来源隔离。",
        "",
        "| Campaign | 域 | 项目 | 分支 | 版本 | 状态 | 发布阻断 | 目标数 | 来源 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for item in campaigns:
        row = [
            item["campaign_id"],
            item["domain"],
            item["project"],
            item["branch"],
            item["version"],
            item["state"],
            "是" if item["release_blocked"] else "否",
            str(len(item["target_ids"]) or len(item["source_notes"])),
            "、".join(item["source_notes"]),
        ]
        lines.append("| " + " | ".join(md_cell(value) for value in row) + " |")
    return "\n".join(lines) + "\n"


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
        debt_id = debt.target_id or debt.source.name
        lines.extend(
            [
                f"- [ ] [{debt.priority}] {debt.title} <!-- validation-debt:{debt_id} -->",
                f"  - 项目：{debt.project}",
                f"  - 分支 / commit：{debt.branch} / {debt.commit}",
                f"  - 已过门槛：{'；'.join(debt.passed_gates)}",
                f"  - 待办：{'；'.join(debt.pending)}",
                f"  - 下一动作：{debt.next_action}",
                f"  - 来源：{debt.source.name}",
            ]
        )
    return "\n".join(lines) + "\n"


def render_open_loops_delta(debts: list[Debt], root: Path, existing_text: str) -> str:
    marker_re = re.compile(r"<!--\s*validation-debt:([^>]+?)\s*-->")
    existing_ids = {match.group(1).strip() for match in marker_re.finditer(existing_text)}
    current = {debt.target_id or debt.source.name: debt for debt in debts}
    added = sorted(set(current) - existing_ids)
    still_open = sorted(set(current) & existing_ids)
    stale = sorted(existing_ids - set(current))
    lines = [
        "# Open Loops 验证债务差异草稿",
        "",
        f"> 来源：{root}",
        "> 只对带 `validation-debt` 标识的条目做机器对账；未带标识的人工条目不判断、不修改。",
        "",
        f"- 新增：{len(added)}",
        f"- 仍开放：{len(still_open)}",
        f"- 疑似过期：{len(stale)}",
        "",
        "## 新增",
        "",
    ]
    if not added:
        lines.append("- 无")
    for debt_id in added:
        debt = current[debt_id]
        lines.append(f"- [ ] [{debt.priority}] {debt.title} <!-- validation-debt:{debt_id} -->")
        lines.append(f"  - 下一动作：{debt.next_action}")
        lines.append(f"  - 来源：{debt.source.name}")
    lines.extend(["", "## 仍开放", ""])
    lines.extend(f"- {debt_id}" for debt_id in still_open)
    if not still_open:
        lines.append("- 无")
    lines.extend(["", "## 疑似过期", ""])
    lines.extend(f"- {debt_id}" for debt_id in stale)
    if not stale:
        lines.append("- 无")
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
    parser.add_argument("--domain", choices=["all", "asr", "esp32", "none"], default="all")
    parser.add_argument("--project", default="", help="Case-insensitive project substring filter.")
    parser.add_argument("--branch", default="", help="Case-insensitive branch substring filter.")
    parser.add_argument("--priority", choices=["", "P0", "P1", "P2"], default="")
    parser.add_argument("--since", default="", help="Managed-target lower date bound in YYYY-MM-DD form.")
    parser.add_argument("--campaign", action="store_true", help="Append grouped validation Campaign output.")
    parser.add_argument("--campaign-json", help="Optional output path for machine-readable Campaign JSON.")
    parser.add_argument("--open-loops", help="Existing canonical open-loops.md to compare read-only.")
    parser.add_argument("--open-loops-delta", help="Output path for the standalone open-loops delta draft.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.fix_patterns).expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"fix-patterns directory does not exist: {root}")

    if args.since and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.since):
        raise SystemExit("--since must use YYYY-MM-DD")
    if bool(args.open_loops) != bool(args.open_loops_delta):
        raise SystemExit("--open-loops and --open-loops-delta must be provided together")

    all_debts, file_count, explicit_count = scan(root)
    debts = filter_debts(
        all_debts,
        domain=args.domain,
        project=args.project,
        branch=args.branch,
        priority=args.priority,
        since=args.since,
    )
    filtered = any([args.domain != "all", args.project, args.branch, args.priority, args.since])
    print(render_report(debts, root, file_count, explicit_count, filtered=filtered))

    campaigns = build_campaigns(debts)
    if args.campaign:
        print("\n" + render_campaign_report(campaigns))
    if args.campaign_json:
        campaign_path = Path(args.campaign_json).expanduser().resolve()
        campaign_path.parent.mkdir(parents=True, exist_ok=True)
        campaign_path.write_text(json.dumps({"campaigns": campaigns}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\nCampaign JSON written: {campaign_path}")

    if args.open_loops_draft:
        draft_path = Path(args.open_loops_draft).expanduser().resolve()
        draft_path.parent.mkdir(parents=True, exist_ok=True)
        draft_path.write_text(render_open_loops_draft(debts, root), encoding="utf-8")
        print(f"\nOpen-loops draft written: {draft_path}")
    if args.open_loops_delta:
        existing_path = Path(args.open_loops).expanduser().resolve()
        existing_text = existing_path.read_text(encoding="utf-8-sig", errors="replace")
        delta_path = Path(args.open_loops_delta).expanduser().resolve()
        delta_path.parent.mkdir(parents=True, exist_ok=True)
        delta_path.write_text(render_open_loops_delta(debts, root, existing_text), encoding="utf-8")
        print(f"\nOpen-loops delta written: {delta_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
