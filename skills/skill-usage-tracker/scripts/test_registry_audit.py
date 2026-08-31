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

print("registry audit tests passed")
