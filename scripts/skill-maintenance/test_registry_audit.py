#!/usr/bin/env python3
"""Offline regression tests for plugin-version registry auditing."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("registry_audit.py")
SPEC = importlib.util.spec_from_file_location("registry_audit_under_test", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


def create_skill(version_root: Path) -> Path:
    skill_md = version_root / "skills" / "control-chrome" / "SKILL.md"
    skill_md.parent.mkdir(parents=True)
    skill_md.write_text(
        "---\n"
        "name: control-chrome\n"
        "description: Control Chrome.\n"
        "---\n",
        encoding="utf-8",
    )
    return skill_md


with tempfile.TemporaryDirectory(prefix="registry-audit-") as temp:
    cache_root = Path(temp) / "cache"
    plugin_root = cache_root / "openai-bundled" / "chrome"
    old_version = plugin_root / "1.0.0"
    active_version = plugin_root / "2.0.0"
    create_skill(old_version)
    active_skill = create_skill(active_version)

    with mock.patch.object(
        audit,
        "_resolve_active_plugin_version",
        return_value=active_version.resolve(),
    ):
        records, issues = audit.discover_plugin_records(cache_root)

    assert issues == []
    assert [record.name for record in records] == ["chrome:control-chrome"]
    assert records[0].location == str(active_skill)

    with mock.patch.object(audit, "_resolve_active_plugin_version", return_value=None):
        records, issues = audit.discover_plugin_records(cache_root)

    assert issues == []
    assert [record.name for record in records] == [
        "chrome:control-chrome",
        "chrome:control-chrome",
    ]

with tempfile.TemporaryDirectory(prefix="registry-inventory-") as temp:
    root = Path(temp)
    active = root / "skills"
    disabled = root / "skills.disabled"
    cache = root / "cache"
    cache.mkdir()
    for folder, name in ((active / "personal-one", "personal-one"), (active / ".system" / "system-one", "system-one"), (disabled / "old-one", "old-one")):
        folder.mkdir(parents=True)
        (folder / "SKILL.md").write_text(f"---\nname: {name}\ndescription: Fixture capability.\n---\n", encoding="utf-8")
    create_skill(cache / "vendor" / "chrome" / "1.0")
    index = root / "index.md"
    index.write_text("| Request | Skill |\n|---|---|\n| Personal | `personal-one` |\n| System | `system-one` |\n| Browser | `chrome:control-chrome` |\n", encoding="utf-8")
    manifest = root / "retired-skills.yaml"
    manifest.write_text("skills:\n  - name: old-one\n", encoding="utf-8")
    archive = root / "skills-index" / "archive" / "index.md"
    archive.parent.mkdir(parents=True)
    archive.write_text("# Archived Skills\n## Archived Entries\n| Skill | Replacement |\n|---|---|\n| `old-one` | personal-one |\n## Historical Removals\n- `gone-one` is history only.\n", encoding="utf-8")
    args = audit.build_parser().parse_args(["--active-root", str(active), "--disabled-root", str(disabled), "--plugin-cache", str(cache), "--index", str(index)])
    report = audit.build_audit(args)
    assert report["summary"]["personal"] == 1 and report["summary"]["system"] == 1
    assert report["summary"]["plugin_cache_candidates"] == 1
    assert report["session_visible"] is None and report["summary"]["session_visible"] is None
    assert report["archive_issues"] == [] and report["summary"]["archive_checked"]
    assert all(row["exposure"] == "unknown" for row in report["valid_routes"])

    available = root / "available.txt"
    available.write_text("personal-one\nchrome:control-chrome\nold-one\n", encoding="utf-8")
    args.available_names_file = available
    report = audit.build_audit(args)
    assert report["summary"]["session_visible"] == 3 and report["summary"]["session_plugins"] == 1
    assert report["registered_not_exposed"] == ["system-one"]
    assert report["disabled_but_exposed"] == ["old-one"]
    assert next(row for row in report["valid_routes"] if row["name"] == "system-one")["exposure"] == "not-exposed"

    manifest.write_text("review_after: 2000-01-01\nskills: []\n", encoding="utf-8")
    archive.write_text("# Archived Skills\nOld folders are still recoverable.\n", encoding="utf-8")
    report = audit.build_audit(args)
    assert len(report["archive_issues"]) == 4
    args.strict = True
    args.json = True
    with mock.patch("builtins.print"):
        assert audit.run(args) == 2
    manifest.write_text("skills: wrong-shape\n", encoding="utf-8")
    assert any("requires a skills list" in item for item in audit.build_audit(args)["archive_issues"])
    args.available_names_file = root / "missing.txt"
    report = audit.build_audit(args)
    assert report["session_visible"] is None and report["invalid"]

print("registry audit tests passed: cache versions, distinct counts, exposure, archive drift, and strict failure")
