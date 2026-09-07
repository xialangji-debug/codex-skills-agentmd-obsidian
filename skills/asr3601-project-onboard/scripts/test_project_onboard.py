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
    yl_dir = repo / "gui" / "lv_watch" / "lv_apps" / "yl"
    yl_dir.mkdir(parents=True)
    (yl_dir / "yl.h").write_text(
        '#define yl_device_name "SAMPLE"\n#define yl_device_ver "SAMPLE_3602_TEST"\n#define yl_hw_ver "SAMPLE_3602"\n',
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "base"], check=True)
    write = run_script(repo, "--write")
    assert write.returncode == 0, write.stderr or write.stdout
    local_file = repo / ".codex-project" / "local.md"
    local_content = "# Project-owned local context\n\nDO-NOT-OVERWRITE\n"
    local_file.write_text(local_content, encoding="utf-8")
    force = run_script(repo, "--write", "--force")
    assert force.returncode == 0, force.stderr or force.stdout
    assert local_file.read_text(encoding="utf-8") == local_content
    assert "local.md" not in force.stdout.split("written=", 1)[-1].splitlines()[0]
    for name in ["variant.md", "device.md", "memory.md"]:
        assert (repo / ".codex-project" / name).exists()
    agents = (repo / "AGENTS.md").read_text(encoding="utf-8")
    index = (repo / ".codex-project" / "index.md").read_text(encoding="utf-8")
    zentao = (repo / ".codex-project" / "zentao.md").read_text(encoding="utf-8")
    assert ".codex-project/local.md" in agents
    assert ".codex-project/local.md" in index
    assert ".codex\\skills\\zentao-bug-triage" in zentao
    variant = (repo / ".codex-project" / "variant.md").read_text(encoding="utf-8")
    assert "branch：`main`" in variant
    assert "yl_device_ver`：`SAMPLE_3602_TEST`" in variant
    assert "构建命令：`make craneg_modem_watch" in variant
    assert "project_id：`" in variant
    stable_files = [
        repo / "AGENTS.md",
        repo / ".codex-project" / "index.md",
        *[
            repo / ".codex-project" / name
            for name in ["zentao.md", "build.md", "protocol.md", "device.md", "memory.md"]
        ],
    ]
    forbidden_values = ["SAMPLE_3602_TEST", "branch：`main`", "make craneg_modem_watch", "project_id：`"]
    for path in stable_files:
        text = path.read_text(encoding="utf-8")
        for value in forbidden_values:
            assert value not in text, f"{path.name} duplicated dynamic value: {value}"
    check = run_script(repo, "--check")
    assert check.returncode == 0, check.stderr or check.stdout
    snapshot_line = next(line for line in check.stdout.splitlines() if line.startswith("snapshot_id="))
    snapshot_id = snapshot_line.split("=", 1)[1]
    assert len(snapshot_id) == 16
    repeated_check = run_script(repo, "--check")
    assert f"snapshot_id={snapshot_id}" in repeated_check.stdout
    yl_file = yl_dir / "yl.h"
    original_yl = yl_file.read_text(encoding="utf-8")
    yl_file.write_text(original_yl + "// dirty\n", encoding="utf-8")
    dirty = run_script(repo, "--check")
    assert dirty.returncode == 2
    assert "variant content differs" in dirty.stdout and "status=stale" in dirty.stdout
    assert "snapshot_id=" not in dirty.stdout
    yl_file.write_text(original_yl, encoding="utf-8")
    clean_again = run_script(repo, "--check")
    assert clean_again.returncode == 0, clean_again.stderr or clean_again.stdout
    (repo / "tracked.txt").write_text("next\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "tracked.txt"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "next"], check=True)
    stale = run_script(repo, "--check")
    assert stale.returncode == 2
    assert "commit:" in stale.stdout and "status=stale" in stale.stdout
    refresh = run_script(repo, "--write")
    assert refresh.returncode == 0, refresh.stderr or refresh.stdout
    refreshed_check = run_script(repo, "--check")
    assert refreshed_check.returncode == 0, refreshed_check.stderr or refreshed_check.stdout
    refreshed_snapshot = next(
        line.split("=", 1)[1]
        for line in refreshed_check.stdout.splitlines()
        if line.startswith("snapshot_id=")
    )
    assert refreshed_snapshot != snapshot_id

with tempfile.TemporaryDirectory(prefix="project-onboard-variant-") as temp:
    repo = Path(temp) / "example_variant"
    yl_dir = repo / "gui" / "lv_watch" / "lv_apps" / "yl"
    yl_dir.mkdir(parents=True)
    (yl_dir / "yl.h").write_text(
        '#define yl_device_name "SAMPLE"\n#define yl_device_ver "SAMPLE_LZ_3602_TEST"\n#define yl_hw_ver "SAMPLE_LZ_3602"\n',
        encoding="utf-8",
    )
    branch = "sample_lz_3602_20260101"
    subprocess.run(["git", "init", "-q", "-b", branch, str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "base"], check=True)
    write = run_script(repo, "--write")
    assert write.returncode == 0, write.stderr or write.stdout
    variant_path = repo / ".codex-project" / "variant.md"
    first = variant_path.read_text(encoding="utf-8")
    assert "TARGET_OS：`ALIOS`" in first
    subprocess.run(["git", "-C", str(repo), "branch", "-m", "sample_lz_3602_20260102"], check=True)
    refresh = run_script(repo, "--write")
    assert refresh.returncode == 0, refresh.stderr or refresh.stdout
    second = variant_path.read_text(encoding="utf-8")
    assert "branch：`sample_lz_3602_20260102`" in second
    assert ".codex-project/variant.md" in refresh.stdout.split("written=", 1)[-1]

with tempfile.TemporaryDirectory(prefix="project-onboard-app-") as temp:
    repo = Path(temp) / "example_app_firmware"
    yl_dir = repo / "gui" / "lv_watch" / "lv_apps" / "yl"
    yl_dir.mkdir(parents=True)
    (yl_dir / "yl.h").write_text(
        '#define yl_device_name "LT52"\n'
        '#define yl_device_ver "LT52_YD_ASR3602_TW18_APP_TEST"\n'
        '#define yl_hw_ver "LT52_YouDao"\n',
        encoding="utf-8",
    )
    branch = "TW18_LT52_3602_有道APP定制腕表20260813"
    subprocess.run(["git", "init", "-q", "-b", branch, str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "base"], check=True)
    write = run_script(repo, "--write")
    assert write.returncode == 0, write.stderr or write.stdout
    variant = (repo / ".codex-project" / "variant.md").read_text(encoding="utf-8")
    assert "协议：`LT52 APP协议`" in variant
    assert "协议优先级：`APP协议 > 平台协议 > 公共固件逻辑`" in variant

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
