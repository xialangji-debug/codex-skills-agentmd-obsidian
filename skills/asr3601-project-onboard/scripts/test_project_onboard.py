#!/usr/bin/env python3
"""Offline smoke test for project onboarding and stale checks."""

from __future__ import annotations

import os
import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).with_name("project_onboard.py")
SCRIPT_ENV = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
SPEC = importlib.util.spec_from_file_location("project_onboard_under_test", SCRIPT)
assert SPEC and SPEC.loader
onboard = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = onboard
SPEC.loader.exec_module(onboard)


def run_script(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--repo", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=SCRIPT_ENV,
    )


with tempfile.TemporaryDirectory(prefix="project-onboard-") as temp:
    repo = Path(temp) / "example_firmware"
    yl_dir = repo / "gui/lv_watch/lv_apps/yl"
    yl_dir.mkdir(parents=True)
    header = yl_dir / "yl.h"
    header.write_text('#define yl_device_name "SAMPLE"\n#define yl_device_ver "SAMPLE_3602_TEST"\n#define yl_hw_ver "SAMPLE_3602"\n')
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    for key, value in (("user.name", "Test"), ("user.email", "test@example.invalid")):
        subprocess.run(["git", "-C", str(repo), "config", key, value], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "base"], check=True)
    result = run_script(repo, "--prepare")
    assert result.returncode == 0, result.stderr
    assert "NEEDS_CONFIGURATION" in result.stdout  # Unknown targets still support source work.
    assert sorted(p.name for p in (repo / ".codex-project").iterdir()) == ["variant.md"]
    assert (repo / "AGENTS.md").exists()
    view = repo / ".codex-project/variant.md"
    assert onboard.variant_fields(view.read_text(encoding="utf-8"))["构建命令"] == "未确认"
    first_time = view.stat().st_mtime_ns
    assert run_script(repo, "--prepare").returncode == 0
    assert view.stat().st_mtime_ns == first_time
    local = repo / ".codex-project/local.md"
    local.write_bytes(b"User-owned local instructions\r\n")
    agents = repo / "AGENTS.md"
    agents.write_bytes(b"# Custom project rules\r\nDo not overwrite\r\n")
    assert run_script(repo, "--write", "--force").returncode == 0
    assert local.read_bytes() == b"User-owned local instructions\r\n"
    assert agents.read_bytes() == b"# Custom project rules\r\nDo not overwrite\r\n"
    assert run_script(repo, "--check").returncode == 0
    header.write_text(header.read_text() + "// changed source\n")
    before = view.read_bytes()
    assert run_script(repo, "--check").returncode == 2
    assert view.read_bytes() == before
    assert run_script(repo, "--prepare").returncode == 0
    assert run_script(repo, "--check").returncode == 0
    subprocess.run(["git", "-C", str(repo), "branch", "-m", "changed-branch"], check=True)
    assert run_script(repo, "--prepare").returncode == 0
    assert onboard.variant_fields(view.read_text(encoding="utf-8"))["branch"] == "changed-branch"


def mapping_entry(*, branch="SAMPLE", version="MODEL_A", project="Project A", products=("Product A",), status="confirmed", verified="true", local_tokens=()):
    lines = ["- branch_contains:", f"    - {branch}", "  yl_device_ver_contains:", f"    - {version}", "  zentao_names:", f"    - {project}"]
    if products:
        lines.append("  product_names:")
        lines.extend(f"    - {value}" for value in products)
    if local_tokens:
        lines.append("  local_tokens:")
        lines.extend(f"    - {value}" for value in local_tokens)
    lines.extend(["  project_id: 42", "  product_id: 7"])
    if status:
        lines.append(f"  status: {status}")
    if verified:
        lines.append(f"  verified: {verified}")
    return "\n".join(lines) + "\n"


with tempfile.TemporaryDirectory(prefix="project-onboard-mapping-") as temp:
    repo = Path(temp)
    project_map = repo / "synthetic-map.md"
    cases = [
        ("full match", mapping_entry(), "SAMPLE_MAIN", "MODEL_A_V1", True),
        ("version mismatch", mapping_entry(), "SAMPLE_MAIN", "MODEL_B_V1", False),
        ("reverse short branch", mapping_entry(branch="SAMPLE_LONG"), "SAMPLE", "MODEL_A_V1", False),
        ("needs confirmation", mapping_entry(status="needs-confirmation"), "SAMPLE_MAIN", "MODEL_A_V1", False),
        ("ambiguous products", mapping_entry(products=("Product A", "Product B")), "SAMPLE_MAIN", "MODEL_A_V1", False),
        ("legacy verified", mapping_entry(status=""), "SAMPLE_MAIN", "MODEL_A_V1", True),
        ("legacy project-only name", mapping_entry(status="", products=()), "SAMPLE_MAIN", "MODEL_A_V1", True),
        ("legacy unverified", mapping_entry(status="", verified=""), "SAMPLE_MAIN", "MODEL_A_V1", False),
        ("legacy explicit false", mapping_entry(status="", verified="false"), "SAMPLE_MAIN", "MODEL_A_V1", False),
        ("token-only candidate", mapping_entry(branch="OTHER", local_tokens=("SAMPLE",)), "SAMPLE_MAIN", "MODEL_A_V1", False),
        ("overlapping products", mapping_entry() + mapping_entry(branch="SAMPLE_MAIN", products=("Product B",)), "SAMPLE_MAIN", "MODEL_A_V1", False),
        ("duplicate same identity", mapping_entry() + mapping_entry(branch="SAMPLE_MAIN"), "SAMPLE_MAIN", "MODEL_A_V1", True),
    ]
    failures = []
    for name, entries, branch, version, confirmed in cases:
        project_map.write_text("```yaml\n" + entries + "```\n", encoding="utf-8")
        info = onboard.RepoInfo(repo, "sample", branch, "abc1234", "clean", "SAMPLE", version, "ASR3602")
        with patch.object(onboard, "PROJECT_MAP", project_map):
            fields = onboard.variant_fields(onboard.render_files(info)[".codex-project/variant.md"])
        actual = fields["映射状态"] == "confirmed"
        if actual != confirmed:
            failures.append(f"{name}: expected confirmed={confirmed}, got {fields['映射状态']}")
    assert not failures, "\n".join(failures)

print("project onboard tests passed (including 12 mapping boundary cases)")
