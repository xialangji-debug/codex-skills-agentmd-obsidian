#!/usr/bin/env python3
"""Generate local Codex project context for ASR3601/ASR3602 firmware repos."""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


SKILLS_ROOT = Path(__file__).resolve().parents[2]
LOCAL_PROJECT_MAP = Path.home() / ".codex" / "zentao-bug-triage" / "project-map.local.md"
BUNDLED_PROJECT_MAP = SKILLS_ROOT / "zentao-bug-triage" / "references" / "project-map.md"
PROJECT_MAP = LOCAL_PROJECT_MAP if LOCAL_PROJECT_MAP.exists() else BUNDLED_PROJECT_MAP
PROJECT_MAP_SOURCE = "local private project map" if PROJECT_MAP == LOCAL_PROJECT_MAP else "bundled generic project map"
PLUGIN_ZENTAO_SCRIPT = r"$env:USERPROFILE\.codex\skills\zentao-bug-triage\scripts\zentao_bug_snapshot.js"
FAST_ZENTAO_SCRIPT = r"$env:USERPROFILE\.codex\skills\zentao-bug-triage\scripts\zentao_bug_fast_fetch.py"
PROTOCOL_ROOT = Path.home() / "Documents" / "Obsidian" / "CodexVault" / "Codex" / "references" / "asr3601-protocols"


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
    product_names: list[str]
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


def identity_hash(value: str, length: int) -> str:
    normalized = " ".join(value.split()).replace("\\", "/").lower()
    return hashlib.sha256(normalized.encode("utf-8", errors="replace")).hexdigest()[:length]


def repository_id(info: RepoInfo) -> str:
    remote = run_git(info.root, "remote", "get-url", "origin")
    source = remote if remote not in {"不可用", "干净"} else str(info.root)
    return identity_hash(source, 12)


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
        product_names = collect_list(block, "product_names")
        if not names:
            candidate = collect_scalar(block, "candidate")
            if candidate:
                names = [candidate]
        mapping = Mapping(
            zentao_names=names,
            product_names=product_names,
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
    return Mapping([], [], "", "", "", "No confirmed project-map match.", "unconfirmed")


def product_family(info: RepoInfo) -> str:
    text = " ".join([info.name, info.branch, info.yl_device_name, info.yl_device_ver, info.yl_hw_ver]).upper()
    device = info.yl_device_name if info.yl_device_name != "不可用" else ""
    if device:
        return device
    return "360x"


def protocol_profile(info: RepoInfo) -> tuple[str, str]:
    raw = " ".join([info.name, info.branch, info.yl_device_name, info.yl_device_ver, info.yl_hw_ver])
    text = raw.lower()
    family = product_family(info)

    if "3603" in text and "app" in text:
        return f"{family} APP 协议（海外版本）", "APP 协议 > 海外平台协议 > 公共固件逻辑"

    if "lz" in text or "乐智" in raw or "电信" in raw:
        return f"{family} 电信乐智协议", "电信乐智协议 > 平台协议 > 公共固件逻辑"
    if "app" in text and "xcx" not in text:
        return f"{family} APP协议", "APP协议 > 平台协议 > 公共固件逻辑"

    if "物卡" in raw or "wk" in text:
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
    if "lz" in text or "乐智" in text or "电信" in text:
        return (
            "make craneg_modem_watch TARGET_OS=ALIOS PS_MODE=LITE_LTEONLY CHIP_ID=CRANEL",
            "用户确认过的 3602 默认构建命令；如具体分支验证为 THREADX，以本项目 variant.md 更新为准。",
        )
    if "app" in text and "3602" in text:
        return (
            "make craneg_modem_watch TARGET_OS=THREADX PS_MODE=LITE_LTEONLY CHIP_ID=CRANEL",
            "通用 3602 APP 构建候选；实际参数以项目本地 build.md 为准。",
        )
    return (
        "make craneg_modem_watch TARGET_OS=ALIOS PS_MODE=LITE_LTEONLY CHIP_ID=CRANEL",
        "通用 3602 默认构建候选；产品例外只记录在项目本地 build.md。",
    )


def build_identity(command: str) -> tuple[str, str, str]:
    def value(name: str) -> str:
        match = re.search(rf"(?:^|\s){re.escape(name)}=([^\s]+)", command)
        return match.group(1) if match else "未确认"

    return value("CHIP_ID"), value("TARGET_OS"), value("PS_MODE")


def memory_aliases(info: RepoInfo) -> list[str]:
    values = [info.name, product_family(info), info.yl_device_name, info.yl_hw_ver]
    values.extend(token for token in re.split(r"[_\-/\s]+", info.branch) if len(token) >= 3)
    result: list[str] = []
    for value in values:
        if value and value != "不可用" and value not in result:
            result.append(value)
    return result[:16]


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
    zentao_product_name = mapping.product_names[0] if mapping.product_names else zentao_name
    project_id = mapping.project_id or "未确认"
    product_id = mapping.product_id or "未确认"
    verified = mapping.verified or "未确认"
    mapping_status = "confirmed" if mapping.project_id and mapping.status != "unconfirmed" else "needs-confirmation"
    aliases = "\n".join(f"- `{value}`" for value in memory_aliases(info)) or "- 未确认"
    protocol_links = ""

    agents = f"""# Codex Project Instructions

## Scope

- Repository: `{info.name}`
- Local path: `{info.root}`
- Domain: ASR360x / Crane / LVGL watch firmware.

## Context Loading

1. For list-only “抓bug / 当前bug” requests, check whether `AGENTS.md` and `.codex-project/{{index,zentao,build,protocol,variant,device,memory}}.md` exist. If they do, run the `zentao-bug-triage` fast fetch immediately and validate afterward; do not pre-refresh for commit or dirty changes. If any are missing, initialize first.
2. For other work, read `.codex-project/index.md` first.
3. If `.codex-project/local.md` exists and the task needs project-specific tools or constraints, read it next.
4. Read `.codex-project/variant.md` before bug investigation/fixing, protocol, build, flash, release, or Zentao writes.
5. If the fingerprint is stale, refresh it with `asr3601-project-onboard` before those actions.
6. Read only the task-specific context linked by the index.

## Project Guardrails

- Treat live repository evidence as authoritative; preserve unrelated dirty-worktree changes.
- Do not infer protocol, customer variant, build parameters, Zentao mapping, or device identity from the folder name alone.
- Do not select a flash target by COM number alone; confirm chip, artifact, USB identity, and probe result.
- Keep reusable procedures in global Skills and current checkout facts in `.codex-project/`.
- Store cross-project reusable fixes in the Obsidian `fix-patterns/` memory only after verification.
"""

    index = f"""# {info.name} Codex Project Index

Current branch, commit, dirty state, product identity, protocol, build parameters, and Zentao IDs live only in `variant.md`.

## 默认路由

| 请求 | 使用 |
|---|---|
| 抓 bug / 当前 bug / 禅道 | `zentao-bug-triage` + `.codex-project/zentao.md` |
| 修 bug / 是否存在 / 当前分支实现 | `asr3601-lvgl-firmware-triage` |
| 查协议 / 是否符合协议 | `asr3601-protocol-branch-matrix` + `.codex-project/protocol.md` |
| CATStudio / 日志 | `catstudio-log-extractor` |
| 验证 / 收工 / 解决说明 / 验证债务 | `asr3601-fix-closeout-reporter` |
| 编译 / 刷机 | `asr3602-local-build-flash` + `.codex-project/build.md` + `.codex-project/device.md` |
| 正式发布 / 上传 | `.codex-project/local.md` 指定的私有发布流程 |
| 变体确认 / 客户能力边界 | `.codex-project/variant.md` |
| 类似问题/修复记忆 | `.codex-project/memory.md` |

## 项目专属扩展

如果 `.codex-project/local.md` 存在，按需读取其中的项目专属工具、命令或约束。该文件由项目自行维护，project-onboard 不创建也不覆盖。

## 注意

项目上下文文件是本机 Codex 辅助文件，不参与固件提交。不要在本文件复制 `variant.md` 的动态字段。
"""

    zentao = f"""# Zentao Context

当前映射状态、项目名、产品名、候选名称、project_id、product_id 和核验信息只记录在 `variant.md`。

## 映射来源

- 来源：`{PROJECT_MAP_SOURCE}`

## 抓取规则

- 用户说“抓 bug / 当前 bug / 去禅道抓 bug”时，直接运行快速入口；它先按文件存在性判断是否初始化，抓取完成后再校验实时仓库、版本、项目和附件。
- 已初始化时不因 commit 或 dirty 变化在抓取前刷新；未初始化时才先运行 project-onboard。抓取快照不一致时刷新并重抓一次。
- 不优先使用浏览器、Chrome 或 Computer Use；只有脚本失败、登录失效、页面结构变化或用户明确要求看网页时才兜底。
- 如果 `variant.md` 的映射状态是 `needs-confirmation`，抓项目专属 bug 前先让用户确认禅道项目名和项目 ID。

## 常用命令

```powershell
python -X utf8 \"{FAST_ZENTAO_SCRIPT}\" --repo .
$env:NODE_PATH=\"$env:USERPROFILE\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\node\\node_modules;$env:USERPROFILE\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\node\\node_modules\\.pnpm\\node_modules\"
node \"{PLUGIN_ZENTAO_SCRIPT}\" --repo . --bug-status unresolved --detail-limit 0 --no-download-attachments
```
"""

    build_md = """# Build Context

当前构建命令、构建来源、目标、CHIP_ID、TARGET_OS 和 PS_MODE 只记录在 `variant.md`。

## 使用规则

- 修复后优先跑最小验证；涉及共用逻辑、协议、UI 状态机或出版本前，再跑全量构建。
- 全量构建前先执行 `git status --short`，不要忽略未跟踪源码文件。
- 构建前重新核对 `variant.md` 与当前仓库；指纹过期时先刷新项目上下文。
- 如果已记录命令在本项目失败，修正证据来源并重新生成 `variant.md`，不要把当前分支参数写回本文件或全局 Skill。
"""

    protocol_md = f"""# Protocol Context

当前产品族、客户/产品变体、协议、协议优先级和 `yl_*` 版本只记录在 `variant.md`。

## 协议资料入口

- [协议资料索引]({(PROTOCOL_ROOT / 'index.md').as_posix()})
- [协议与分支矩阵]({(PROTOCOL_ROOT / 'matrix.md').as_posix()})

## 使用规则

- 判断“是否符合协议”时，先走 `asr3601-protocol-branch-matrix`。
- 只读相关协议文件，不默认读取整个协议库。
- 结论要区分：固件未发送、固件字段不一致、平台未识别、当前分支不支持、产品/客户/平台变体差异。
- `variant.md` 记录的当前项目协议优先级高于全局泛化判断。
"""

    repo_id = repository_id(info)
    variant_id = identity_hash(zentao_product_name, 12) if zentao_product_name not in {"", "未确认"} else ""
    target_id = identity_hash("|".join([repo_id, info.branch, info.yl_device_ver, variant_id]), 16)

    variant_md = f"""# ASR Variant Fingerprint

- verified_at：`{verified_at}`
- repo：`{info.root}`
- repo_id：`{repo_id}`
- variant_id：`{variant_id or "未确认"}`
- target_id：`{target_id}`
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
- 构建目标：`craneg_modem_watch`
- 构建命令：`{build}`
- 构建来源：{build_source}
- 禅道项目：`{zentao_name}`
- 禅道产品：`{zentao_product_name}`
- 禅道候选项目：{", ".join(f"`{n}`" for n in mapping.zentao_names) if mapping.zentao_names else "未确认"}
- project_id：`{project_id}`
- product_id：`{product_id}`
- 映射 verified：`{verified}`
- 映射状态：`{mapping_status}`
- 映射备注：{mapping.note or "无"}
- 映射来源：`{PROJECT_MAP_SOURCE}`
{protocol_links}

## 记忆搜索别名

{aliases}

## 使用规则

- 每次修复、移植、验证、构建、发布或禅道操作前重新核对 branch、commit、dirty 和 `yl_device_ver`。
- 客户/产品变体不等于协议；协议只按 APP、小程序、乐智及明确的平台路径判断。
- 指纹与当前仓库不一致时，先重新运行 project-onboard，不沿用旧构建或禅道映射。
"""

    device_md = """# Device Target Context

当前项目、分支、预期芯片参数和构建目标只记录在 `variant.md`。

## 稳定识别规则

- 预期下载设备族：`ASR Modem / ASR Serial Download / ASR DIAG`
- 常见 USB 标识：`VID_2ECC`（只作候选，必须以实时枚举和芯片探测为准）
- 固定 COM：`不记录`

## 刷机门槛

- 刷机前同时核对项目指纹、固件产物、CHIP_ID、USB VID/PID/设备名称和探测结果。
- COM 号不是设备身份，不能因为上次使用过同一 COM 就直接刷写。
- 检测到 ESP32、蓝牙串口、未知 USB 串口或芯片不一致时立即停止。
- 多台嵌入式设备同时连接时，先输出候选设备表，再选择唯一匹配目标。
"""

    memory_md = f"""# Project Memory Context

- 记忆根目录：`{(Path.home() / 'Documents' / 'Obsidian' / 'CodexVault' / 'Codex' / 'fix-patterns')}`

当前项目、分支、产品族、协议和搜索别名只记录在 `variant.md`。

## 使用规则

- 仅在类似问题、回归、跨分支、明确日志关键词或用户要求读取记忆时，使用 `variant.md` 的搜索别名。
- 默认只读最相关的 1-3 条 `fix-patterns`，不扫描整个 vault。
- 已验证修复可提升记忆可信度；Bug 复测激活时必须把旧记忆标记为待复核。
"""

    return {
        "AGENTS.md": agents,
        ".codex-project/index.md": index,
        ".codex-project/zentao.md": zentao,
        ".codex-project/build.md": build_md,
        ".codex-project/protocol.md": protocol_md,
        ".codex-project/variant.md": variant_md,
        ".codex-project/device.md": device_md,
        ".codex-project/memory.md": memory_md,
    }


def variant_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"^-\s+([^：]+)：`([^`]*)`\s*$", line.strip())
        if match:
            fields[match.group(1).strip()] = match.group(2).strip()
    return fields


def comparable_variant(text: str) -> str:
    """Ignore only generation time; every other variant fact is freshness-significant."""
    return re.sub(r"^- verified_at：`[^`]*`\s*\n", "", text, count=1, flags=re.M).strip()


def check_context(info: RepoInfo, files: dict[str, str]) -> int:
    missing = [rel for rel in files if not (info.root / rel).exists()]
    live_variant = info.root / ".codex-project" / "variant.md"
    mismatches: list[str] = []
    if live_variant.exists():
        current = variant_fields(live_variant.read_text(encoding="utf-8", errors="replace"))
        expected = variant_fields(files[".codex-project/variant.md"])
        keys = [
            "repo", "repo_id", "variant_id", "target_id", "branch", "commit", "yl_device_name", "yl_device_ver", "yl_hw_ver",
            "CHIP_ID", "TARGET_OS", "PS_MODE", "协议", "禅道项目", "project_id", "product_id", "映射状态",
        ]
        for key in keys:
            if current.get(key) != expected.get(key):
                mismatches.append(f"{key}: recorded={current.get(key, '缺失')} live={expected.get(key, '缺失')}")
        recorded_text = live_variant.read_text(encoding="utf-8", errors="replace")
        expected_text = files[".codex-project/variant.md"]
        if comparable_variant(recorded_text) != comparable_variant(expected_text):
            mismatches.append("variant content differs from the current checkout or context schema")
    print(f"repo={info.root}")
    print(f"branch={info.branch}")
    print(f"commit={info.commit}")
    if missing:
        print("missing=" + ", ".join(missing))
    if mismatches:
        print("stale:")
        for item in mismatches:
            print(f"- {item}")
    if missing or mismatches:
        print("status=stale")
        return 2
    print("status=current")
    return 0


def write_files(info: RepoInfo, files: dict[str, str], force: bool) -> list[str]:
    written = []
    for rel, content in files.items():
        path = info.root / rel
        if path.exists() and not force and rel != ".codex-project/variant.md":
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
    parser.add_argument("--check", action="store_true", help="Read-only check for missing or stale project context")
    parser.add_argument("--force", action="store_true", help="Overwrite existing context files")
    parser.add_argument("--no-exclude", action="store_true", help="Do not update .git/info/exclude")
    args = parser.parse_args()

    info = gather(Path(args.repo))
    files = render_files(info)

    if args.check:
        return check_context(info, files)

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
    print("written=" + (", ".join(written) if written else "none (stable files already exist; use --force to refresh generated policy files)"))
    if not args.no_exclude:
        print("exclude=updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
