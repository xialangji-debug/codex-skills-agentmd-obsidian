#!/usr/bin/env python3
"""Generate local Codex project context for ASR3601/ASR3602 firmware repos."""

from __future__ import annotations

import argparse
import json
import sys
import hashlib
import re
import subprocess
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path



SKILLS_ROOT = Path.home() / ".codex" / "skills"
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
    import yaml

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


def match_mapping(info: RepoInfo, project_map: Path | None = None) -> Mapping:
    matches: list[Mapping] = []
    candidates: list[Mapping] = []
    tokens_text = " ".join([info.name, info.branch, info.yl_device_name, info.yl_device_ver, info.yl_hw_ver])
    for branches, yl_versions, local_tokens, mapping in parse_project_map(project_map or PROJECT_MAP):
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
        branch=(lambda value: "detached" if value == "干净" else value)(run_git(repo, "branch", "--show-current")),
        commit=run_git(repo, "rev-parse", "--short", "HEAD"),
        dirty=run_git(repo, "status", "--short"),
        yl_device_name=yl["yl_device_name"],
        yl_device_ver=yl["yl_device_ver"],
        yl_hw_ver=yl["yl_hw_ver"],
    )


def context_from_info(info: RepoInfo, mapping: Mapping | None = None) -> dict:
    mapping = mapping or match_mapping(info)
    names = list(dict.fromkeys(mapping.zentao_names))
    products = list(dict.fromkeys(mapping.product_names))
    project_name = names[0] if len(names) == 1 else "未确认"
    product_name = products[0] if len(products) == 1 else (project_name if not products else "未确认")
    verified = mapping.verified.lower()
    legacy = verified in {"true", "yes", "confirmed"} or bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", verified))
    confirmed = bool(mapping.project_id and (mapping.status == "confirmed" or (not mapping.status and legacy)) and len(names) == 1 and len(products) <= 1 and product_name != "未确认")
    repo_id = repository_id(info)
    variant_id = identity_hash(product_name, 12) if product_name not in {"", "未确认"} else ""
    target_source = "|".join(" ".join(value.split()) for value in [repo_id, info.branch, info.yl_device_ver, variant_id])
    return {
        "repo": str(info.root), "repo_id": repo_id, "branch": info.branch,
        "commit": info.commit, "dirty": info.dirty,
        "yl_device_name": info.yl_device_name, "yl_device_ver": info.yl_device_ver,
        "yl_hw_ver": info.yl_hw_ver, "variant_id": variant_id,
        "target_id": hashlib.sha256(target_source.encode("utf-8")).hexdigest()[:16],
        "mapping_status": "confirmed" if confirmed else "needs-confirmation",
        "project_name": project_name, "product_name": product_name,
        "project_id": mapping.project_id, "product_id": mapping.product_id,
        "mapping_source": PROJECT_MAP_SOURCE, "mapping_note": mapping.note,
    }


def read_context(repo: Path, project_map: Path | None = None) -> dict:
    info = gather(repo)
    if info.commit == "不可用":
        raise ValueError(f"Cannot read Git identity: {repo}")
    return context_from_info(info, match_mapping(info, project_map))


def main() -> int:
    parser = argparse.ArgumentParser(description="Read live ASR identity without generated Markdown dependencies")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--project-map", type=Path)
    args = parser.parse_args()
    try:
        result = read_context(Path(args.repo), args.project_map)
    except (ValueError, OSError) as exc:
        print(json.dumps({"status": "unavailable", "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
