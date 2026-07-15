#!/usr/bin/env python3
"""Generate local Codex project context for ASR3601/ASR3602 firmware repos."""

from __future__ import annotations

import argparse
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


CODEX_HOME = Path.home() / ".codex"
PROJECT_MAP = CODEX_HOME / "skills" / "zentao-bug-triage" / "references" / "project-map.md"
PROTOCOL_ROOT = Path.home() / "Documents" / "Obsidian" / "CodexVault" / "Codex" / "references" / "asr3601-protocols"
JUNICARE_PROTOCOL_PDF = PROTOCOL_ROOT / "raw" / "20260707-junicare-app-protocol-v1.201-for-yuelan.pdf"
JUNICARE_PROTOCOL_TEXT = PROTOCOL_ROOT / "extracted" / "20260707-junicare-app-protocol-v1.201-for-yuelan.md"


@dataclass
class RepoInfo:
    root: Path
    name: str
    branch: str
    commit: str
    dirty: str
    yl_device_name: str
    yl_device_ver: str
    yl_hw_ver: str


@dataclass
class Mapping:
    zentao_names: list[str]
    project_id: str
    product_id: str
    verified: str
    note: str
    status: str


def run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        return "不可用"
    return result.stdout.strip() or "干净"


def read_yl(repo: Path) -> dict[str, str]:
    yl = repo / "gui" / "lv_watch" / "lv_apps" / "yl" / "yl.h"
    values = {"yl_device_name": "不可用", "yl_device_ver": "不可用", "yl_hw_ver": "不可用"}
    if not yl.exists():
        return values
    text = yl.read_text(encoding="utf-8", errors="replace")
    for key in values:
        m = re.search(rf"#define\s+{re.escape(key)}\s+\"([^\"]+)\"", text)
        if m:
            values[key] = m.group(1)
    return values


def clean_value(value: str) -> str:
    value = value.strip().strip("\"'")
    if value.startswith("- "):
        value = value[2:].strip()
    return value.strip().strip("\"'")


def line_indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def collect_list(block: str, key: str) -> list[str]:
    values: list[str] = []
    lines = block.splitlines()
    for i, line in enumerate(lines):
        m = re.match(rf"^(\s*){re.escape(key)}:\s*(.*)$", line)
        if not m:
            continue
        key_indent = len(m.group(1))
        inline = m.group(2).strip()
        if inline:
            return [clean_value(inline)]
        for child in lines[i + 1 :]:
            if not child.strip():
                continue
            if line_indent(child) <= key_indent:
                break
            item = re.match(r"^\s*-\s*(.+?)\s*$", child)
            if item:
                values.append(clean_value(item.group(1)))
        break
    return values


def collect_scalar(block: str, key: str) -> str:
    m = re.search(rf"^\s*{re.escape(key)}:\s*(.+?)\s*$", block, re.M)
    return clean_value(m.group(1)) if m else ""


def normalize_entry(block: str) -> str:
    lines = block.splitlines()
    if lines and lines[0].startswith("- "):
        lines[0] = lines[0][2:]
    return "\n".join(lines)


def yaml_blocks(text: str) -> list[str]:
    return re.findall(r"```yaml\s*(.*?)```", text, flags=re.S)


def split_yaml_entries(block: str) -> list[str]:
    entries: list[str] = []
    current: list[str] = []
    for line in block.splitlines():
        if re.match(r"^-\s+(branch_contains|local_tokens):", line):
            if current:
                entries.append(normalize_entry("\n".join(current)))
            current = [line]
        elif current:
            current.append(line)
    if current:
        entries.append(normalize_entry("\n".join(current)))
    return entries


def parse_project_map(path: Path) -> list[tuple[list[str], list[str], list[str], Mapping]]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    entries: list[str] = []
    for block in yaml_blocks(text):
        entries.extend(split_yaml_entries(block))

    parsed = []
    for block in entries:
        branches = collect_list(block, "branch_contains")
        yl_versions = collect_list(block, "yl_device_ver_contains")
        local_tokens = collect_list(block, "local_tokens")
        names = collect_list(block, "zentao_names")
        if not names:
            candidate = collect_scalar(block, "candidate")
            if candidate:
                names = [candidate]
        mapping = Mapping(
            zentao_names=names,
            project_id=collect_scalar(block, "project_id"),
            product_id=collect_scalar(block, "product_id"),
            verified=collect_scalar(block, "verified"),
            note=collect_scalar(block, "note"),
            status=collect_scalar(block, "status"),
        )
        parsed.append((branches, yl_versions, local_tokens, mapping))
    return parsed


def match_mapping(info: RepoInfo) -> Mapping:
    best: Mapping | None = None
    tokens_text = " ".join([info.name, info.branch, info.yl_device_name, info.yl_device_ver, info.yl_hw_ver])
    for branches, yl_versions, local_tokens, mapping in parse_project_map(PROJECT_MAP):
        branch_hit = any(b and (b in info.branch or info.branch in b) for b in branches)
        ver_hit = any(v and v in info.yl_device_ver for v in yl_versions)
        if branch_hit and (not yl_versions or ver_hit):
            return mapping
        if branch_hit and best is None:
            best = mapping
        token_hit = bool(local_tokens) and all(token and token in tokens_text for token in local_tokens)
        if token_hit and best is None:
            best = mapping
    if best:
        return best
    return Mapping([], "", "", "", "No confirmed project-map match.", "unconfirmed")


def product_family(info: RepoInfo) -> str:
    text = " ".join([info.name, info.branch, info.yl_device_name, info.yl_device_ver, info.yl_hw_ver]).upper()
    device = info.yl_device_name if info.yl_device_name != "不可用" else ""
    if "C10" in text and "TW10" in text:
        return "C10/TW10"
    if device:
        return device
    for token in ["LT52", "C10", "JC8", "JC2"]:
        if token in text:
            return token
    return "360x"


def protocol_profile(info: RepoInfo) -> tuple[str, str]:
    raw = " ".join([info.name, info.branch, info.yl_device_name, info.yl_device_ver, info.yl_hw_ver])
    text = raw.lower()
    family = product_family(info)

    # Every product branch in this Crane 3603 checkout is an overseas APP variant.
    if info.name.lower() == "crane-2024.03_r4":
        return f"{family} APP 协议（海外版本）", "APP 协议 > 海外平台协议 > 公共固件逻辑"

    if "lz" in text or "乐智" in raw or "电信" in raw:
        return f"{family} 电信乐智协议", "电信乐智协议 > 平台协议 > 公共固件逻辑"
    if "app" in text and "xcx" not in text:
        return f"{family} APP协议", "APP协议 > 平台协议 > 公共固件逻辑"

    if "xd" in text or "熊顿" in raw:
        suffix = "熊顿儿童款"
    elif "物卡" in raw or "wk" in text:
        suffix = "物卡公版"
    elif "儿童" in raw:
        suffix = "儿童款"
    else:
        suffix = "公版"
    return f"{family} 小程序协议（{suffix}）", "小程序协议 > 平台协议 > 公共固件逻辑"


def build_command(info: RepoInfo) -> tuple[str, str]:
    text = " ".join([info.name, info.branch, info.yl_device_ver, info.yl_hw_ver]).lower()
    if "3603" in text or "craneg" in text:
        return (
            "make craneg_modem_watch TARGET_OS=THREADX PS_MODE=LTEGSM CHIP_ID=CRANEG",
            "用户确认过的 3603 全量构建命令。",
        )
    if "app" in text and "lt52" in text:
        return (
            "make craneg_modem_watch TARGET_OS=THREADX PS_MODE=LITE_LTEONLY CHIP_ID=CRANEL",
            "用户确认过的 LT52 APP 公版编译命令。",
        )
    if "lz" in text or "乐智" in text or "电信" in text:
        return (
            "make craneg_modem_watch TARGET_OS=ALIOS PS_MODE=LITE_LTEONLY CHIP_ID=CRANEL",
            "用户确认过的 3602 默认构建命令；如具体分支验证为 THREADX，以本项目 build.md 更新为准。",
        )
    return (
        "make craneg_modem_watch TARGET_OS=ALIOS PS_MODE=LITE_LTEONLY CHIP_ID=CRANEL",
        "用户确认过的 3602 默认构建命令；LT52 APP 公版单独使用 THREADX。",
    )


def build_identity(command: str) -> tuple[str, str, str]:
    def value(name: str) -> str:
        match = re.search(rf"(?:^|\s){re.escape(name)}=([^\s]+)", command)
        return match.group(1) if match else "未确认"

    return value("CHIP_ID"), value("TARGET_OS"), value("PS_MODE")


def gather(repo: Path) -> RepoInfo:
    repo = repo.resolve()
    yl = read_yl(repo)
    return RepoInfo(
        root=repo,
        name=repo.name,
        branch=run_git(repo, "branch", "--show-current"),
        commit=run_git(repo, "rev-parse", "--short", "HEAD"),
        dirty=run_git(repo, "status", "--short"),
        yl_device_name=yl["yl_device_name"],
        yl_device_ver=yl["yl_device_ver"],
        yl_hw_ver=yl["yl_hw_ver"],
    )


def render_files(info: RepoInfo) -> dict[str, str]:
    mapping = match_mapping(info)
    product, protocol_priority = protocol_profile(info)
    build, build_source = build_command(info)
    chip_id, target_os, ps_mode = build_identity(build)
    verified_at = datetime.now().astimezone().isoformat(timespec="seconds")
    zentao_name = mapping.zentao_names[0] if mapping.zentao_names else "未确认"
    project_id = mapping.project_id or "未确认"
    product_id = mapping.product_id or "未确认"
    verified = mapping.verified or "未确认"
    mapping_status = "confirmed" if mapping.project_id and mapping.status != "unconfirmed" else "needs-confirmation"
    protocol_links = ""
    if "APP 协议（海外版本）" in product:
        protocol_links = f"""
## 协议地址

- [JuniCare APP 协议 V1.201 PDF 原件]({JUNICARE_PROTOCOL_PDF.as_posix()})
- [JuniCare APP 协议 V1.201 可搜索文本]({JUNICARE_PROTOCOL_TEXT.as_posix()})
- [协议资料索引]({(PROTOCOL_ROOT / 'index.md').as_posix()})
- [协议与分支矩阵]({(PROTOCOL_ROOT / 'matrix.md').as_posix()})
"""

    agents = f"""# Project Context

当前工程：{info.name}
项目路径：{info.root}
当前分支：{info.branch}
当前提交：{info.commit}
产品/协议：{product}
禅道映射：{zentao_name}
协议优先级：{protocol_priority}
默认抓 bug：使用 `zentao-bug-triage`，优先脚本抓取，不优先浏览器/Computer Use
默认修 bug：先判断当前分支是否存在，再修改
默认收工：使用 `asr3601-fix-closeout-reporter`
编译命令：`{build}`

更多细节按需读取：

- [项目索引]({(info.root / '.codex-project' / 'index.md').as_posix()})
- [禅道配置]({(info.root / '.codex-project' / 'zentao.md').as_posix()})
- [构建说明]({(info.root / '.codex-project' / 'build.md').as_posix()})
- [协议配置]({(info.root / '.codex-project' / 'protocol.md').as_posix()})
- [变体指纹]({(info.root / '.codex-project' / 'variant.md').as_posix()})
"""

    index = f"""# {info.name} Codex Project Index

- 项目路径：`{info.root}`
- 当前分支：`{info.branch}`
- 当前提交：`{info.commit}`
- `yl_device_name`：`{info.yl_device_name}`
- `yl_device_ver`：`{info.yl_device_ver}`
- `yl_hw_ver`：`{info.yl_hw_ver}`

## 默认路由

| 请求 | 使用 |
|---|---|
| 抓 bug / 当前 bug / 禅道 | `zentao-bug-triage` + `.codex-project/zentao.md` |
| 修 bug / 是否存在 | `asr3601-bug-intake-orchestrator` |
| 查协议 / 是否符合协议 | `asr3601-protocol-branch-matrix` + `.codex-project/protocol.md` |
| CATStudio / 日志 | `catstudio-log-extractor` |
| 收工 / 解决说明 | `asr3601-fix-closeout-reporter` |
| 编译 / 验证 | `.codex-project/build.md` |
| 变体确认 / 客户能力边界 | `.codex-project/variant.md` |

## 注意

项目上下文文件是本机 Codex 辅助文件，不参与固件提交。
"""

    zentao = f"""# Zentao Context

- 映射状态：{mapping_status}
- 禅道项目名：`{zentao_name}`
- 候选项目名：{", ".join(f"`{n}`" for n in mapping.zentao_names) if mapping.zentao_names else "未确认"}
- project_id：`{project_id}`
- product_id：`{product_id}`
- verified：`{verified}`
- 来源：`C:\\Users\\84365\\.codex\\skills\\zentao-bug-triage\\references\\project-map.md`
- 备注：{mapping.note or "无"}

## 抓取规则

- 用户说“抓 bug / 当前 bug / 去禅道抓 bug”时，先用 `zentao-bug-triage` 的脚本流程。
- 不优先使用浏览器、Chrome 或 Computer Use；只有脚本失败、登录失效、页面结构变化或用户明确要求看网页时才兜底。
- 如果映射状态是 `needs-confirmation`，抓项目专属 bug 前先让用户确认禅道项目名和项目 ID。

## 常用命令

```powershell
$env:NODE_PATH=\"$env:USERPROFILE\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\node\\node_modules;$env:USERPROFILE\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\node\\node_modules\\.pnpm\\node_modules\"
node \"$env:USERPROFILE\\.codex\\skills\\zentao-bug-triage\\scripts\\zentao_bug_snapshot.js\" --repo . --limit 80
node \"$env:USERPROFILE\\.codex\\skills\\zentao-bug-triage\\scripts\\zentao_bug_snapshot.js\" --repo . --bug-status unresolved --detail-limit 0 --no-download-attachments
```
"""

    build_md = f"""# Build Context

- 默认构建命令：

```powershell
{build}
```

- 来源：{build_source}
- 目标：`craneg_modem_watch`
- 当前分支：`{info.branch}`
- 当前提交：`{info.commit}`

## 使用规则

- 修复后优先跑最小验证；涉及共用逻辑、协议、UI 状态机或出版本前，再跑全量构建。
- 全量构建前先执行 `git status --short`，不要忽略未跟踪源码文件。
- 如果该命令在本项目失败，更新本文件，不要改全局 skill。
"""

    protocol_md = f"""# Protocol Context

- 产品/协议：{product}
- 协议优先级：{protocol_priority}
- `yl_device_ver`：`{info.yl_device_ver}`
- `yl_hw_ver`：`{info.yl_hw_ver}`
{protocol_links}

## 使用规则

- 判断“是否符合协议”时，先走 `asr3601-protocol-branch-matrix`。
- 只读相关协议文件，不默认读取整个协议库。
- 结论要区分：固件未发送、固件字段不一致、平台未识别、当前分支不支持、产品/客户/平台变体差异。
- 当前项目的协议优先级高于全局泛化判断。
"""

    variant_md = f"""# ASR Variant Fingerprint

- verified_at：`{verified_at}`
- repo：`{info.root}`
- branch：`{info.branch}`
- commit：`{info.commit}`
- dirty worktree：

```text
{info.dirty}
```

- 产品族：`{product_family(info)}`
- 客户/产品变体：`{info.branch}`
- `yl_device_name`：`{info.yl_device_name}`
- `yl_device_ver`：`{info.yl_device_ver}`
- `yl_hw_ver`：`{info.yl_hw_ver}`
- CHIP_ID：`{chip_id}`
- TARGET_OS：`{target_os}`
- PS_MODE：`{ps_mode}`
- 协议：`{product}`
- 协议优先级：`{protocol_priority}`
- 构建命令：`{build}`
- 禅道项目：`{zentao_name}`
- project_id：`{project_id}`
- product_id：`{product_id}`
- 映射状态：`{mapping_status}`

## 使用规则

- 每次修复、移植、验证、构建、发布或禅道操作前重新核对 branch、commit、dirty 和 `yl_device_ver`。
- 客户/产品变体不等于协议；协议只按 APP、小程序、乐智及明确的平台路径判断。
- 指纹与当前仓库不一致时，先重新运行 project-onboard，不沿用旧构建或禅道映射。
"""

    return {
        "AGENTS.md": agents,
        ".codex-project/index.md": index,
        ".codex-project/zentao.md": zentao,
        ".codex-project/build.md": build_md,
        ".codex-project/protocol.md": protocol_md,
        ".codex-project/variant.md": variant_md,
    }


def write_files(info: RepoInfo, files: dict[str, str], force: bool) -> list[str]:
    written = []
    for rel, content in files.items():
        path = info.root / rel
        if path.exists() and not force:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        written.append(rel)
    return written


def resolve_git_dir(repo: Path) -> Path | None:
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--git-dir"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode == 0:
        raw = result.stdout.strip()
        if raw:
            git_dir = Path(raw)
            if not git_dir.is_absolute():
                git_dir = repo / git_dir
            return git_dir.resolve()

    dot_git = repo / ".git"
    if dot_git.is_dir():
        return dot_git
    if dot_git.is_file():
        text = dot_git.read_text(encoding="utf-8", errors="replace").strip()
        m = re.match(r"gitdir:\s*(.+)", text)
        if m:
            git_dir = Path(m.group(1).strip())
            if not git_dir.is_absolute():
                git_dir = repo / git_dir
            return git_dir.resolve()
    return None


def update_exclude(repo: Path) -> None:
    git_dir = resolve_git_dir(repo)
    if not git_dir:
        return
    exclude = git_dir / "info" / "exclude"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    current = exclude.read_text(encoding="utf-8", errors="replace") if exclude.exists() else ""
    lines = ["AGENTS.md", ".codex-project/"]
    additions = [line for line in lines if line not in current.splitlines()]
    if additions:
        with exclude.open("a", encoding="utf-8", newline="\n") as f:
            if current and not current.endswith("\n"):
                f.write("\n")
            f.write("\n# Local Codex project context\n")
            for line in additions:
                f.write(line + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".", help="Firmware repo path")
    parser.add_argument("--write", action="store_true", help="Write project context files")
    parser.add_argument("--dry-run", action="store_true", help="Print planned files without writing")
    parser.add_argument("--force", action="store_true", help="Overwrite existing context files")
    parser.add_argument("--no-exclude", action="store_true", help="Do not update .git/info/exclude")
    args = parser.parse_args()

    info = gather(Path(args.repo))
    files = render_files(info)

    print(f"repo={info.root}")
    print(f"branch={info.branch}")
    print(f"commit={info.commit}")
    print(f"yl_device_ver={info.yl_device_ver}")
    print("planned_files=" + ", ".join(files.keys()))

    if args.dry_run or not args.write:
        for rel, content in files.items():
            print(f"\n--- {rel} ---")
            print(content[:1200].rstrip())
        return 0

    written = write_files(info, files, args.force)
    if not args.no_exclude:
        update_exclude(info.root)
    print("written=" + (", ".join(written) if written else "none (already exists; use --force to overwrite)"))
    if not args.no_exclude:
        print("exclude=updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
