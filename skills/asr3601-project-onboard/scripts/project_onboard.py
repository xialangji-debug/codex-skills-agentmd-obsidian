#!/usr/bin/env python3
"""Generate local Codex project context for ASR3601/ASR3602 firmware repos."""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path

import yaml


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


def parse_project_map(path: Path) -> list[tuple[list[str], list[str], list[str], Mapping]]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    parsed = []

    def values(entry: dict, key: str) -> list[str]:
        value = entry.get(key)
        if value is None:
            return []
        return [str(item).strip() for item in (value if isinstance(value, list) else [value]) if item is not None and str(item).strip()]

    def scalar(entry: dict, key: str) -> str:
        value = entry.get(key)
        return str(value).strip() if value is not None else ""

    for block in re.findall(r"^[ \t]*\x60\x60\x60yaml[ \t]*\r?\n(.*?)^[ \t]*\x60\x60\x60[ \t]*$", text, flags=re.S | re.M):
        try:
            entries = yaml.safe_load(block)
        except yaml.YAMLError as exc:
            raise ValueError("Invalid YAML in project map; correct it before using project identity.") from exc
        if not isinstance(entries, list) or any(not isinstance(entry, dict) for entry in entries):
            raise ValueError("Project-map YAML must contain a list of mapping objects.")
        for entry in entries:
            names = values(entry, "zentao_names") or values(entry, "candidate")
            mapping = Mapping(
                zentao_names=names,
                product_names=values(entry, "product_names"),
                project_id=scalar(entry, "project_id"),
                product_id=scalar(entry, "product_id"),
                verified=scalar(entry, "verified"),
                note=scalar(entry, "note"),
                status=scalar(entry, "status"),
            )
            parsed.append((values(entry, "branch_contains"), values(entry, "yl_device_ver_contains"), values(entry, "local_tokens"), mapping))
    return parsed


def match_mapping(info: RepoInfo) -> Mapping:
    matches: list[Mapping] = []
    candidates: list[Mapping] = []
    tokens_text = " ".join([info.name, info.branch, info.yl_device_name, info.yl_device_ver, info.yl_hw_ver])
    for branches, yl_versions, local_tokens, mapping in parse_project_map(PROJECT_MAP):
        branch_hit = any(b and b in info.branch for b in branches)
        ver_hit = any(v and v in info.yl_device_ver for v in yl_versions)
        if branch_hit and (not yl_versions or ver_hit):
            matches.append(mapping)
        token_hit = bool(local_tokens) and all(token and token in tokens_text for token in local_tokens)
        if branch_hit or token_hit:
            candidates.append(mapping)
    if matches:
        identities = {(tuple(m.zentao_names), tuple(m.product_names), m.project_id, m.product_id, m.status, m.verified) for m in matches}
        if len(identities) == 1:
            return matches[0]
        return Mapping([], [], "", "", "", "Multiple project-map matches; confirm the exact product.", "needs-confirmation")
    if candidates:
        return replace(candidates[0], status="needs-confirmation", note="Candidate only: branch/version constraints were not fully matched.")
    return Mapping([], [], "", "", "", "No confirmed project-map match.", "unconfirmed")


def product_family(info: RepoInfo) -> str:
    text = " ".join([info.name, info.branch, info.yl_device_name, info.yl_device_ver, info.yl_hw_ver]).upper()
    device = info.yl_device_name if info.yl_device_name != "不可用" else ""
    if "C10" in text and "TW10" in text:
        return "C10/TW10"
    if device:
        return device
    return "360x"


def protocol_profile(info: RepoInfo) -> tuple[str, str]:
    raw = " ".join([info.name, info.branch, info.yl_device_name, info.yl_device_ver, info.yl_hw_ver])
    text = raw.lower()
    identity_text = " ".join(
        [info.branch, info.yl_device_name, info.yl_device_ver, info.yl_hw_ver]
    ).lower()
    family = product_family(info)

    if "3603" in text and "app" in text:
        return f"{family} APP 协议（海外版本）", "APP 协议 > 海外平台协议 > 公共固件逻辑"

    if "lz" in text or "乐智" in raw or "电信" in raw:
        return f"{family} 电信乐智协议", "电信乐智协议 > 平台协议 > 公共固件逻辑"
    if "app" in identity_text:
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
            "Built-in 3603 candidate; verify against the project-confirmed build profile before execution.",
        )
    if "lz" in text or "乐智" in text or "电信" in text:
        return (
            "make craneg_modem_watch TARGET_OS=ALIOS PS_MODE=LITE_LTEONLY CHIP_ID=CRANEL",
            "Built-in 3602 candidate; a project-confirmed THREADX profile takes precedence.",
        )
    if "app" in text and "lt52" in text:
        return (
            "make craneg_modem_watch TARGET_OS=THREADX PS_MODE=LITE_LTEONLY CHIP_ID=CRANEL",
            "Built-in LT52 APP candidate; verify against the project-confirmed build profile before execution.",
        )
    return (
        "make craneg_modem_watch TARGET_OS=ALIOS PS_MODE=LITE_LTEONLY CHIP_ID=CRANEL",
        "Built-in 3602 candidate; LT52 APP defaults to THREADX. Use the project-confirmed build profile.",
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
    names = list(dict.fromkeys(mapping.zentao_names))
    products = list(dict.fromkeys(mapping.product_names))
    zentao_name = names[0] if len(names) == 1 else "未确认"
    zentao_product_name = products[0] if len(products) == 1 else (zentao_name if not products else "未确认")
    project_id = mapping.project_id or "未确认"
    product_id = mapping.product_id or "未确认"
    verified = mapping.verified or "未确认"
    verified_value = mapping.verified.lower()
    legacy_verified = verified_value in {"true", "yes", "confirmed"} or bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", verified_value))
    explicitly_confirmed = mapping.status == "confirmed" or (not mapping.status and legacy_verified)
    mapping_status = "confirmed" if (mapping.project_id and explicitly_confirmed and len(names) == 1 and len(products) <= 1 and zentao_product_name != "未确认") else "needs-confirmation"
    aliases = "\n".join(f"- `{value}`" for value in memory_aliases(info)) or "- 未确认"
    protocol_links = ""

    agents = f"""# Codex Project Instructions

## Scope

- Repository: `{info.name}`
- Local path: `{info.root}`
- Domain: ASR360x / Crane / LVGL watch firmware.

## Context Loading

1. Use `.codex-project/index.md` and only the context required by its matching route. Reuse the route already established for the task. Read `.codex-project/local.md` only for relevant project-specific tools or constraints.
2. For ordinary read-only source questions, go to live source. Load variant fields only when the answer depends on them; do not run a full context refresh.
3. For an authorized source edit, capture branch, HEAD, and dirty state once, or reuse that current task snapshot. Refresh identity only when the operation needs missing or stale facts.
4. For “抓bug / 当前bug”, use the `zentao-bug-triage` launcher directly. It owns missing-context initialization and fetch validation.
5. For build, flash, release, and Zentao operations, use the owning controller and its required current identity. Do not duplicate checks that controller already performs. Formal release, including `快速出版本`, uses the direct owner-controller path without external preflight or post-success checks.
6. Keep `.codex-project/variant.md` as the persistent identity source. Reuse a task snapshot across stages; refresh after an unexpected checkout/identity change when the next operation needs it. A controller's own authorized commit can update expected HEAD without full onboarding.

## Project Guardrails

- Treat live repository evidence as authoritative; preserve unrelated dirty-worktree changes.
- Do not infer protocol, customer variant, build parameters, Zentao mapping, or device identity from the folder name alone.
- Do not select a flash target by COM number alone; confirm chip, artifact, USB identity, and probe result.
- Keep reusable procedures in global Skills and current checkout facts in `.codex-project/`.
- Record completed behavior fixes through `obsidian-fix-pattern-memory` once; static/build evidence is not device, platform, or QA verification.
"""

    index = f"""# {info.name} Codex Project Index

Current branch, commit, dirty state, product identity, protocol, build parameters, and Zentao IDs live only in `variant.md`.

## Task Routes

| Request | Owner/context |
|---|---|
| 抓 bug / 当前 bug / 禅道 | `zentao-bug-triage` + `.codex-project/zentao.md` |
| 修 bug / 是否存在 / 当前分支实现 / screenshots or repro evidence | `asr3601-lvgl-firmware-triage` |
| 移植 / source-target adaptation / ordered integration | `asr3601-cross-branch-porting` |
| Explicit multi-stage or ordered multi-Bug delivery | `asr360x-bug-delivery-orchestrator` |
| 查协议 / 是否符合协议 | `asr3601-protocol-branch-matrix` + `.codex-project/protocol.md` |
| CATStudio / 日志 | `catstudio-log-extractor` |
| Explicit closeout / re-verification | `asr3601-lvgl-firmware-triage` closeout mode; reuse the existing result |
| Validation debt / pending device checks / Campaign | `obsidian-fix-pattern-memory` reporting mode |
| 编译 / build only | `asr3602-local-build-flash` + `.codex-project/build.md` |
| 刷机 / build and flash | `asr3602-local-build-flash`; load `.codex-project/device.md` for physical-device work |
| 出 FOTA / 重新出 FOTA / FOTA 测试双包 | `asr3602-fota-pair-release` directly; its two builds supply build evidence |
| 正式发布 / 上传 / 快速出版本 | `akq-firmware-release`; one direct controller call |
| 变体确认 / 客户能力边界 | `.codex-project/variant.md` |
| 类似问题/修复记忆 | `.codex-project/memory.md` |

## Project-Owned Context

Read `.codex-project/local.md` only when relevant. The project owns it; onboarding never creates or overwrites it.

## Scope

These local context files are excluded from firmware commits. Keep dynamic fields in `variant.md`, and specialist procedures in their Skills.
"""

    zentao = f"""# Zentao Context

Current mapping status, project/product names, candidates, IDs, and evidence live only in `variant.md`.

## Mapping Source

- Source: `{PROJECT_MAP_SOURCE}`

## Operations

- Use `zentao-bug-triage` for read-only list/detail/reconciliation requests. Its launcher owns initialization and snapshot validation; do not repeat those steps outside it.
- Use `zentao-bug-resolver` for authorized resolution. It must read the confirmed product from `variant.md` and match the detail-page product exactly before writing.
- Missing or ambiguous mapping requires the missing project/product facts; do not guess from a similar name. Preserve an already supplied exact authorization.
- Use browser fallback only when the script fails or the user requests the page.

## List Entry

```powershell
python -X utf8 \"{FAST_ZENTAO_SCRIPT}\" --repo .
```
"""

    build_md = """# Build Context

Current build command, source, target, CHIP_ID, TARGET_OS, and PS_MODE live in `variant.md` and the existing project build profile.

## Validation And Controllers

- For a source fix, run the narrowest useful documented validation. Expand for shared behavior or unresolved evidence, not merely to repeat a passed check.
- When formal/FOTA delivery immediately follows, let its controller provide full build evidence. FOTA pairs build test then formal; do not add a third standalone build.
- The selected controller owns profile, Git/dirty, freshness, package, and device checks. Supply the confirmed command and consume its result; do not repeat those checks outside it.
- Preserve required untracked source/resources and unrelated changes. Resolve a command/profile mismatch from current project evidence; keep dynamic parameters out of this file and global Skills.
"""

    protocol_md = f"""# Protocol Context

Current product, variant, protocol classification, and `yl_*` identity live in `variant.md`.

## Protocol Sources

- [协议资料索引]({(PROTOCOL_ROOT / 'index.md').as_posix()})
- [协议与分支矩阵]({(PROTOCOL_ROOT / 'matrix.md').as_posix()})

## Evidence

- Use `asr3601-protocol-branch-matrix` for protocol conformance or responsibility questions; read only the relevant protocol version and current source path.
- Generated protocol classification is an identity-based search hint, not proof of active protocol support. Confirm the active parser/formatter and applicable document before assigning protocol responsibility.
- Distinguish absent firmware reports, field mismatch, platform parsing, unsupported branches, product differences, and missing runtime evidence.
"""

    repo_id = repository_id(info)
    variant_id = identity_hash(zentao_product_name, 12) if zentao_product_name not in {"", "未确认"} else ""
    # Match canonical memory and snapshot reconciliation; branch/version are case-sensitive.
    target_source = "|".join(" ".join(value.split()) for value in [repo_id, info.branch, info.yl_device_ver, variant_id])
    target_id = hashlib.sha256(target_source.encode("utf-8")).hexdigest()[:16]

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

- Reuse the current task snapshot. A new identity-dependent operation must not use facts invalidated by a checkout or identity change; let its owner refresh them.
- Product names are not protocol evidence. Verify the generated classification against active code and the applicable protocol document.
- Build/release/Zentao controllers own their current-state gates. Do not repeat a full onboarding pass between unchanged stages or outside a direct release controller.
"""

    device_md = """# Device Target Context

Current project, branch, expected chip, and build target live in `variant.md`.

## Device Selection

- Expected family: `ASR Modem / ASR Serial Download / ASR DIAG`.
- `VID_2ECC` identifies a candidate only; live USB enumeration and chip probes decide the target.
- Do not persist a COM number as device identity.

## Flash Boundary

- Immediately before flashing, the controller revalidates the package, chip, physical USB identity, and probe result. A remembered port or earlier task snapshot cannot replace this check.
- Stop on an ESP32, Bluetooth/unknown serial target, or chip mismatch. With multiple devices, identify the one matching physical target before flashing.
- Build-only work does not load or probe devices.
"""

    memory_md = f"""# Project Memory Context

- Memory root: `{(Path.home() / 'Documents' / 'Obsidian' / 'CodexVault' / 'Codex' / 'fix-patterns')}`

Current project identity and search aliases live in `variant.md`.

## Lookup And Recording

- Search narrowly for similar/regression/cross-branch issues, clear error signatures, or explicit memory requests; read at most three relevant notes. Ordinary fixes do not require a prior memory lookup.
- After a behavior fix, use `obsidian-fix-pattern-memory` once and pass its exact note/target in the result. Downstream stages reuse it and record only new evidence events.
- Static/build evidence remains working evidence. A reactivated Bug updates only the matching target; it does not invalidate unrelated versions or prove a common root cause.
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


def task_snapshot_id(info: RepoInfo, files: dict[str, str]) -> str:
    """Return a compact receipt for one validated task context."""
    expected = variant_fields(files[".codex-project/variant.md"])
    dirty_id = identity_hash(info.dirty, 12)
    parts = [
        repository_id(info),
        info.branch,
        info.commit,
        dirty_id,
        info.yl_device_name,
        info.yl_device_ver,
        info.yl_hw_ver,
        expected.get("variant_id", ""),
        expected.get("target_id", ""),
    ]
    return identity_hash("|".join(parts), 16)


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
    print(f"snapshot_id={task_snapshot_id(info, files)}")
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
