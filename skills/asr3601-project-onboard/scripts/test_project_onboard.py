#!/usr/bin/env python3
"""Offline smoke test for project onboarding and stale checks."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).with_name("project_onboard.py")
SCRIPT_ENV = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}


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
    assert "不创建也不覆盖" in index
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
    yl_file = yl_dir / "yl.h"
    original_yl = yl_file.read_text(encoding="utf-8")
    yl_file.write_text(original_yl + "// dirty\n", encoding="utf-8")
    dirty = run_script(repo, "--check")
    assert dirty.returncode == 2
    assert "variant content differs" in dirty.stdout and "status=stale" in dirty.stdout
    yl_file.write_text(original_yl, encoding="utf-8")
    clean_again = run_script(repo, "--check")
    assert clean_again.returncode == 0, clean_again.stderr or clean_again.stdout
    (repo / "tracked.txt").write_text("next\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "tracked.txt"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "next"], check=True)
    stale = run_script(repo, "--check")
    assert stale.returncode == 2
    assert "commit:" in stale.stdout and "status=stale" in stale.stdout

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
    assert "3602 默认构建命令" in first
    subprocess.run(["git", "-C", str(repo), "branch", "-m", "sample_lz_3602_20260102"], check=True)
    refresh = run_script(repo, "--write")
    assert refresh.returncode == 0, refresh.stderr or refresh.stdout
    second = variant_path.read_text(encoding="utf-8")
    assert "branch：`sample_lz_3602_20260102`" in second
    assert ".codex-project/variant.md" in refresh.stdout.split("written=", 1)[-1]

print("project onboard tests passed")
