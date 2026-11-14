#!/usr/bin/env python3
"""Audit local Codex skill registrations and Markdown routing indexes.

The audit is read-only. It never installs, enables, disables, moves, or deletes
skills, and it never edits an index automatically.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml


HOME = Path.home()
CODEX_HOME = HOME / ".codex"
DEFAULT_ACTIVE_ROOT = CODEX_HOME / "skills"
DEFAULT_DISABLED_ROOT = CODEX_HOME / "skills.disabled"
DEFAULT_PLUGIN_CACHE = CODEX_HOME / "plugins" / "cache"
DEFAULT_INDEX = HOME / "Documents" / "Obsidian" / "CodexVault" / "Codex" / "agent" / "skills-index.md"

SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
BACKTICK_TOKEN_RE = re.compile(r"`([A-Za-z0-9][A-Za-z0-9_.:-]*)`")
AVAILABLE_NAME_RE = re.compile(r"(?<![A-Za-z0-9_-])([A-Za-z0-9][A-Za-z0-9_-]*(?::[A-Za-z0-9][A-Za-z0-9_-]*)?)")
NON_ROUTE_MARKERS = ("disabled", "不路由", "已禁用", "仅历史", "archived")
IGNORED_ROUTE_TOKENS = {
    "active",
    "disabled",
    "registry-audit",
    "skill",
    "skills",
}


@dataclass(frozen=True)
class SkillRecord:
    name: str
    location: str
    source: str
    folder_name: str
    frontmatter_issues: tuple[str, ...]


@dataclass(frozen=True)
class RouteReference:
    name: str
    line: int
    text: str


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def read_frontmatter(skill_md: Path) -> tuple[dict[str, str], list[str]]:
    issues: list[str] = []
    try:
        text = skill_md.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as exc:
        return {}, [f"cannot read SKILL.md: {exc}"]

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, ["missing opening YAML frontmatter delimiter"]

    end = next((index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"), None)
    if end is None:
        return {}, ["missing closing YAML frontmatter delimiter"]

    fields: dict[str, str] = {}
    current_key: str | None = None
    for raw_line in lines[1:end]:
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if raw_line[:1].isspace():
            if current_key:
                continuation = raw_line.strip()
                if continuation:
                    fields[current_key] = f"{fields.get(current_key, '')} {continuation}".strip()
            continue
        if ":" not in raw_line:
            issues.append(f"invalid frontmatter line: {raw_line.strip()}")
            continue
        key, value = raw_line.split(":", 1)
        current_key = key.strip()
        parsed_value = _unquote(value)
        if parsed_value in {">", ">-", "|", "|-"}:
            parsed_value = ""
        fields[current_key] = parsed_value

    if not fields.get("name"):
        issues.append("missing frontmatter name")
    if not fields.get("description"):
        issues.append("missing frontmatter description")
    return fields, issues


def validate_skill_record(skill_md: Path, source: str, *, managed_plugin: bool = False) -> SkillRecord:
    fields, issues = read_frontmatter(skill_md)
    folder_name = skill_md.parent.name
    name = fields.get("name") or folder_name

    if not managed_plugin:
        if len(name) > 64:
            issues.append("frontmatter name exceeds 64 characters")
        if not SKILL_NAME_RE.fullmatch(name):
            issues.append("frontmatter name must use lowercase letters, digits, and hyphens")
        if name != folder_name:
            issues.append(f"frontmatter name '{name}' does not match folder '{folder_name}'")

    return SkillRecord(
        name=name,
        location=str(skill_md),
        source=source,
        folder_name=folder_name,
        frontmatter_issues=tuple(issues),
    )


def discover_skill_records(root: Path, source: str) -> tuple[list[SkillRecord], list[str]]:
    if not root.exists():
        return [], [f"missing root: {root}"]
    if not root.is_dir():
        return [], [f"root is not a directory: {root}"]

    records: list[SkillRecord] = []
    for skill_md in sorted(root.rglob("SKILL.md"), key=lambda path: str(path).lower()):
        relative = skill_md.relative_to(root)
        record_source = source
        if source == "active" and relative.parts and relative.parts[0] == ".system":
            record_source = "active-system"
        records.append(validate_skill_record(skill_md, record_source))

    invalid_dirs: list[str] = []
    for child in sorted(root.iterdir(), key=lambda path: path.name.lower()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        if not (child / "SKILL.md").exists():
            invalid_dirs.append(f"directory has no root SKILL.md: {child}")
    return records, invalid_dirs


def _resolve_active_plugin_version(plugin_root: Path) -> Path | None:
    """Return the concrete version selected by a valid `latest` link."""
    latest = plugin_root / "latest"
    if not latest.exists():
        return None

    try:
        resolved_root = plugin_root.resolve(strict=True)
        resolved_version = latest.resolve(strict=True)
    except OSError:
        return None

    if not resolved_version.is_dir() or resolved_version.parent != resolved_root:
        return None
    return resolved_version


def discover_plugin_records(root: Path | None) -> tuple[list[SkillRecord], list[str]]:
    if root is None:
        return [], []
    if not root.exists():
        return [], [f"missing optional plugin cache: {root}"]

    records: list[SkillRecord] = []
    active_versions: dict[Path, Path | None] = {}
    for skill_md in sorted(root.rglob("SKILL.md"), key=lambda path: str(path).lower()):
        relative = skill_md.relative_to(root)
        parts = relative.parts
        # `latest` may be traversed on platforms that follow directory links.
        if "latest" in parts:
            continue
        try:
            skills_index = parts.index("skills")
        except ValueError:
            continue
        if skills_index < 2:
            continue
        plugin_name = parts[1]

        # Versioned caches use provider/plugin/version/skills. When `latest`
        # selects a valid sibling version, historical versions are cache only,
        # not additional registrations. Without a valid pointer, retain the
        # old scan-all behavior so an ambiguous cache remains visible.
        if skills_index >= 3:
            plugin_root = root / parts[0] / plugin_name
            if plugin_root not in active_versions:
                active_versions[plugin_root] = _resolve_active_plugin_version(plugin_root)
            active_version = active_versions[plugin_root]
            version_root = plugin_root / parts[2]
            if active_version is not None and version_root.resolve() != active_version:
                continue

        raw = validate_skill_record(skill_md, "plugin", managed_plugin=True)
        records.append(
            SkillRecord(
                name=f"{plugin_name}:{raw.name}",
                location=raw.location,
                source=raw.source,
                folder_name=raw.folder_name,
                frontmatter_issues=raw.frontmatter_issues,
            )
        )
    return records, []


def read_available_names(path: Path | None) -> tuple[set[str], list[str]]:
    if path is None:
        return set(), []
    if not path.exists():
        return set(), [f"missing optional available-names file: {path}"]
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as exc:
        return set(), [f"cannot read available-names file {path}: {exc}"]

    names: set[str] = set()
    exact_name = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*(?::[A-Za-z0-9][A-Za-z0-9_-]*)?$")
    bullet_name = re.compile(r"^\s*[-*]\s+([A-Za-z0-9][A-Za-z0-9_-]*(?::[A-Za-z0-9][A-Za-z0-9_-]*)?)")
    for line in text.splitlines():
        stripped = line.strip().strip("`")
        if exact_name.fullmatch(stripped):
            names.add(stripped)
            continue
        bullet = bullet_name.match(line)
        if bullet:
            names.add(bullet.group(1))
        names.update(match.group(1) for match in AVAILABLE_NAME_RE.finditer(line) if ":" in match.group(1))
    return names, []


def extract_route_references(index_path: Path) -> tuple[list[RouteReference], list[str]]:
    if not index_path.exists():
        return [], [f"missing index: {index_path}"]
    try:
        lines = index_path.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeError) as exc:
        return [], [f"cannot read index {index_path}: {exc}"]

    routes: list[RouteReference] = []
    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not (stripped.startswith("|") and stripped.endswith("|")):
            continue
        if re.fullmatch(r"[|:\-\s]+", stripped):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 2:
            continue
        route_cell = cells[1]
        lowered_line = line.lower()
        if any(marker in lowered_line for marker in NON_ROUTE_MARKERS):
            continue
        for token in BACKTICK_TOKEN_RE.findall(route_cell):
            if token.lower() in IGNORED_ROUTE_TOKENS or "." in token:
                continue
            routes.append(RouteReference(name=token, line=line_number, text=line.strip()))
    return routes, []


def extract_disabled_references(index_path: Path) -> tuple[list[RouteReference], list[str]]:
    if not index_path.exists():
        return [], [f"missing index: {index_path}"]
    try:
        lines = index_path.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeError) as exc:
        return [], [f"cannot read index {index_path}: {exc}"]

    references: list[RouteReference] = []
    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not (stripped.startswith("|") and stripped.endswith("|")):
            continue
        if not any(marker in line.lower() for marker in NON_ROUTE_MARKERS):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 2:
            continue
        for token in BACKTICK_TOKEN_RE.findall(cells[1]):
            if token.lower() not in IGNORED_ROUTE_TOKENS and "." not in token:
                references.append(RouteReference(name=token, line=line_number, text=line.strip()))
    return references, []


def _casefold_map(names: Iterable[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for name in names:
        result.setdefault(name.casefold(), name)
    return result


def _duplicates(records: Iterable[SkillRecord]) -> dict[str, list[str]]:
    locations: dict[str, list[str]] = {}
    display: dict[str, str] = {}
    for record in records:
        key = record.name.casefold()
        display.setdefault(key, record.name)
        locations.setdefault(key, []).append(record.location)
    return {
        display[key]: sorted(set(paths), key=str.lower)
        for key, paths in locations.items()
        if len(set(paths)) > 1
    }


def _plugin_alternatives(name: str, plugin_names: Iterable[str]) -> list[str]:
    suffix = name.casefold()
    return sorted(
        {
            candidate
            for candidate in plugin_names
            if ":" in candidate and candidate.rsplit(":", 1)[1].casefold() == suffix
        },
        key=str.lower,
    )


def audit_archive_inventory(args: argparse.Namespace, disabled_names: set[str]) -> tuple[list[str], bool]:
    manifest = getattr(args, "retired_skills", None) or args.active_root.parent / "retired-skills.yaml"
    index = getattr(args, "archive_index", None) or args.active_root.parent / "skills-index" / "archive" / "index.md"
    if not manifest.exists() and not index.exists() and not getattr(args, "retired_skills", None) and not getattr(args, "archive_index", None):
        return [], False
    issues: list[str] = []
    try:
        data = yaml.safe_load(manifest.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict) or not isinstance(data.get("skills"), list):
            raise ValueError("retirement manifest requires a skills list")
        names = []
        for entry in data["skills"]:
            if not isinstance(entry, dict) or not isinstance(entry.get("name"), str) or not SKILL_NAME_RE.fullmatch(entry["name"]):
                raise ValueError("each archived entry requires a valid skill name")
            names.append(entry["name"])
        if len(names) != len(set(names)):
            issues.append("duplicate archived names in retirement manifest")
        if set(names) != disabled_names:
            issues.append(f"retirement manifest differs from disabled folders: {sorted(set(names) ^ disabled_names)}")
        if data.get("review_after") and dt.date.fromisoformat(str(data["review_after"])) < dt.date.today():
            issues.append("retirement manifest has an expired review_after date")
    except (OSError, ValueError, yaml.YAMLError) as exc:
        issues.append(f"{manifest}: {exc}")
    try:
        lines = index.read_text(encoding="utf-8-sig").splitlines()
        listed: list[str] = []
        in_entries = False
        found_section = False
        for line in lines:
            if line.startswith("## "):
                in_entries = line.strip() == "## Archived Entries"
                found_section |= in_entries
            elif in_entries:
                match = re.match(r"^\|\s*`([a-z0-9-]+)`\s*\|", line)
                if match:
                    listed.append(match.group(1))
        if not found_section:
            issues.append("archive index requires an Archived Entries section for current recoverable folders")
        if len(listed) != len(set(listed)) or set(listed) != disabled_names:
            issues.append(f"archive index differs from disabled folders: {sorted(set(listed) ^ disabled_names)}")
    except (OSError, UnicodeError) as exc:
        issues.append(f"{index}: {exc}")
    return issues, True


def build_audit(args: argparse.Namespace) -> dict[str, Any]:
    active_records, active_invalid = discover_skill_records(args.active_root, "active")
    disabled_records, disabled_invalid = discover_skill_records(args.disabled_root, "disabled")
    plugin_records, plugin_errors = discover_plugin_records(args.plugin_cache)
    available_names, available_errors = read_available_names(args.available_names_file)
    route_refs, index_errors = extract_route_references(args.index)
    disabled_refs, disabled_index_errors = extract_disabled_references(args.index)

    active_names = {record.name for record in active_records}
    personal_names = {record.name for record in active_records if record.source == "active"}
    system_names = active_names - personal_names
    disabled_names = {record.name for record in disabled_records}
    cached_names = {record.name for record in plugin_records}
    plugin_names = cached_names | available_names
    exposure_known = args.available_names_file is not None and not available_errors
    available_keys = {name.casefold() for name in available_names}
    archive_issues, archive_checked = audit_archive_inventory(args, disabled_names)

    active_map = _casefold_map(active_names)
    disabled_map = _casefold_map(disabled_names)
    plugin_map = _casefold_map(plugin_names)

    stale_routes: list[dict[str, Any]] = []
    missing_routes: list[dict[str, Any]] = []
    valid_routes: list[dict[str, Any]] = []
    suggestions: list[str] = []
    stale_disabled_records: list[dict[str, Any]] = []

    for route in route_refs:
        key = route.name.casefold()
        route_data = asdict(route)
        alternatives = _plugin_alternatives(route.name, plugin_names)
        if key in active_map or key in plugin_map:
            route_data["resolved_as"] = active_map.get(key) or plugin_map.get(key)
            route_data["registration"] = "registered" if key in active_map else "plugin-cache" if route.name in cached_names else "session-only"
            route_data["exposure"] = ("visible" if key in available_keys else "not-exposed") if exposure_known else "unknown"
            valid_routes.append(route_data)
            continue
        if key in disabled_map:
            route_data["status"] = "disabled"
            route_data["plugin_alternatives"] = alternatives
            stale_routes.append(route_data)
            if len(alternatives) == 1:
                suggestions.append(f"L{route.line}: replace `{route.name}` with `{alternatives[0]}`")
            else:
                suggestions.append(f"L{route.line}: remove `{route.name}` from recommended routes or mark the row disabled/不路由")
            continue

        route_data["status"] = "missing"
        route_data["plugin_alternatives"] = alternatives
        missing_routes.append(route_data)
        if len(alternatives) == 1:
            suggestions.append(f"L{route.line}: replace `{route.name}` with `{alternatives[0]}`")
        else:
            suggestions.append(f"L{route.line}: confirm installation for `{route.name}` or remove it from recommended routes")

    indexed_keys = {route.name.casefold() for route in route_refs}
    unindexed_active = sorted(
        (name for name in active_names if name.casefold() not in indexed_keys),
        key=str.lower,
    )

    for route in disabled_refs:
        if route.name.casefold() in disabled_map:
            continue
        stale_disabled_records.append(asdict(route))
        suggestions.append(f"L{route.line}: remove stale disabled record `{route.name}`")

    frontmatter_issues = [
        {
            "name": record.name,
            "source": record.source,
            "location": record.location,
            "issues": list(record.frontmatter_issues),
        }
        for record in [*active_records, *disabled_records, *plugin_records]
        if record.frontmatter_issues
    ]

    duplicates = _duplicates([*active_records, *disabled_records, *plugin_records])
    invalid = [*active_invalid, *disabled_invalid, *plugin_errors, *available_errors, *index_errors, *disabled_index_errors]

    return {
        "mode": "read-only",
        "inputs": {
            "active_root": str(args.active_root),
            "disabled_root": str(args.disabled_root),
            "index": str(args.index),
            "plugin_cache": str(args.plugin_cache) if args.plugin_cache else None,
            "available_names_file": str(args.available_names_file) if args.available_names_file else None,
        },
        "summary": {
            "active": len(active_records),
            "personal": len(personal_names),
            "system": len(system_names),
            "disabled": len(disabled_records),
            "plugin_cache_candidates": len(cached_names),
            "session_visible": len(available_names) if exposure_known else None,
            "session_plugins": sum(":" in name for name in available_names) if exposure_known else None,
            "archive_checked": archive_checked,
            "archive_issues": len(archive_issues),
            "plugins_or_available": len(plugin_names),
            "valid_routes": len(valid_routes),
            "stale_routes": len(stale_routes),
            "missing_routes": len(missing_routes),
            "duplicates": len(duplicates),
            "frontmatter_issues": len(frontmatter_issues),
            "invalid": len(invalid),
            "unindexed_active": len(unindexed_active),
            "stale_disabled_records": len(stale_disabled_records),
        },
        "active": sorted(active_names, key=str.lower),
        "personal": sorted(personal_names, key=str.lower),
        "system": sorted(system_names, key=str.lower),
        "plugin_cache_candidates": sorted(cached_names, key=str.lower),
        "session_visible": sorted(available_names, key=str.lower) if exposure_known else None,
        "registered_not_exposed": sorted(name for name in active_names if name.casefold() not in available_keys) if exposure_known else None,
        "disabled_but_exposed": sorted(name for name in disabled_names if name.casefold() in available_keys) if exposure_known else None,
        "archive_issues": archive_issues,
        "disabled": sorted(disabled_names, key=str.lower),
        "plugins_or_available": sorted(plugin_names, key=str.lower),
        "valid_routes": valid_routes,
        "stale_routes": stale_routes,
        "missing_routes": missing_routes,
        "duplicates": duplicates,
        "frontmatter_issues": frontmatter_issues,
        "invalid": invalid,
        "unindexed_active": unindexed_active,
        "stale_disabled_records": stale_disabled_records,
        "patch_suggestions": sorted(set(suggestions)),
    }


def _print_items(title: str, values: Iterable[str]) -> None:
    values = list(values)
    print(f"\n{title} ({len(values)})")
    if not values:
        print("- none")
        return
    for value in values:
        print(f"- {value}")


def print_text_report(report: dict[str, Any]) -> None:
    print("Codex skill registry audit (read-only)")
    for key, value in report["inputs"].items():
        print(f"{key}: {value}")

    summary = report["summary"]
    print("\nSummary")
    for key, value in summary.items():
        print(f"- {key}: {value}")

    _print_items("Registered personal skills", report["personal"])
    _print_items("Registered system skills", report["system"])
    _print_items("Disabled skills", report["disabled"])
    _print_items("Plugin cache candidates (not proof of session exposure)", report["plugin_cache_candidates"])
    if report["session_visible"] is None:
        print("\nSession exposure: unknown; provide --available-names-file to check it.")
    else:
        _print_items("Session-visible skills", report["session_visible"])
        _print_items("Registered but not exposed", report["registered_not_exposed"])
        _print_items("Disabled but still exposed in the supplied catalog", report["disabled_but_exposed"])
    _print_items("Archive inventory issues", report["archive_issues"])

    _print_items(
        "Stale recommended routes",
        [f"L{item['line']} `{item['name']}` (disabled)" for item in report["stale_routes"]],
    )
    _print_items(
        "Missing recommended routes",
        [f"L{item['line']} `{item['name']}`" for item in report["missing_routes"]],
    )
    _print_items(
        "Duplicate registrations",
        [f"{name}: {' | '.join(paths)}" for name, paths in report["duplicates"].items()],
    )
    _print_items(
        "Invalid roots/directories",
        report["invalid"],
    )
    _print_items(
        "Frontmatter issues",
        [
            f"{item['name']} [{item['source']}]: {'; '.join(item['issues'])} ({item['location']})"
            for item in report["frontmatter_issues"]
        ],
    )
    _print_items("Unindexed active skills", report["unindexed_active"])
    _print_items(
        "Stale disabled index records",
        [f"L{item['line']} `{item['name']}`" for item in report["stale_disabled_records"]],
    )
    _print_items("Patch suggestions (review before editing)", report["patch_suggestions"])
    print("\nNo files were changed.")


def run(args: argparse.Namespace) -> int:
    report = build_audit(args)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_text_report(report)

    if args.strict:
        summary = report["summary"]
        blocking = (
            summary["stale_routes"]
            + summary["missing_routes"]
            + summary["duplicates"]
            + summary["frontmatter_issues"]
            + summary["invalid"]
            + summary["stale_disabled_records"]
            + summary["archive_issues"]
        )
        return 2 if blocking else 0
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--active-root", type=Path, default=DEFAULT_ACTIVE_ROOT)
    parser.add_argument("--disabled-root", type=Path, default=DEFAULT_DISABLED_ROOT)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--plugin-cache", type=Path, default=DEFAULT_PLUGIN_CACHE)
    parser.add_argument("--available-names-file", type=Path)
    parser.add_argument("--retired-skills", type=Path)
    parser.add_argument("--archive-index", type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    return run(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
