#!/usr/bin/env python3
"""Run deterministic, offline checks for the public repository."""

from __future__ import annotations

import os
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECK_ENV = os.environ.copy()

PYTHON_TESTS = [
    "scripts/test_privacy_scan.py",
    "scripts/test_sync_public_snapshot.py",
    "skills/asr3601-cross-branch-porting/scripts/test_ordered_cherry_pick.py",
    "skills/asr3601-lvgl-firmware-triage/scripts/test_closeout_verification.py",
    "skills/obsidian-fix-pattern-memory/scripts/test_validation_debt_report.py",
    "skills/asr3601-project-onboard/scripts/test_project_onboard.py",
    "skills/asr3601-project-onboard/scripts/test_identity_contract.py",
    "skills/catstudio-log-extractor/scripts/test_bug_evidence_presets.py",
    "skills/asr360x-bug-delivery-orchestrator/scripts/test_delivery_state.py",
    "skills/obsidian-fix-pattern-memory/scripts/test_fix_memory.py",
    "skills/obsidian-fix-pattern-memory/scripts/test_memory_trust.py",
    "skills/skill-usage-tracker/scripts/test_incremental_scan.py",
    "skills/skill-usage-tracker/scripts/test_registry_audit.py",
    "runtime/test_asr3602_build_profile.py",
    "skills/zentao-bug-triage/scripts/test_snapshot_reconcile.py",
    "skills/zentao-bug-triage/scripts/test_zentao_bug_fast_fetch.py",
]

NODE_TESTS = [
    "skills/zentao-bug-resolver/scripts/zentao_bug_resolver.test.js",
    "skills/zentao-bug-triage/scripts/test_bug_labels.js",
    "skills/zentao-bug-triage/scripts/test_memory_linkage.js",
    "skills/zentao-bug-triage/scripts/test_project_matching.js",
]

POWERSHELL_TESTS = [
    "skills/asr3602-local-build-flash/scripts/test_embedded_target_preflight.ps1",
]
WINDOWS_TESTS = [
    "skills/asr3602-local-build-flash/scripts/test_local_build_flash.ps1",
    "runtime/test_asr360x_build_runtime.ps1",
]


def run(label: str, command: list[str], env: dict[str, str] | None = None) -> None:
    print(f"\n== {label} ==")
    result = subprocess.run(command, cwd=ROOT, env=env or CHECK_ENV)
    if result.returncode != 0:
        raise SystemExit(f"{label} failed with exit code {result.returncode}")


def require(command: str) -> str:
    resolved = shutil.which(command)
    if not resolved:
        raise SystemExit(f"required command is unavailable: {command}")
    return resolved


def install_smoke_test(temp_root: Path) -> None:
    codex_home = temp_root / ".codex"
    vault = temp_root / "vault"
    if os.name == "nt":
        shell = shutil.which("pwsh") or require("powershell")
        run(
            "Windows installer smoke test",
            [
                shell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(ROOT / "scripts" / "install.ps1"),
                "-CodexHome",
                str(codex_home),
                "-VaultPath",
                str(vault),
                "-SkipMcp",
                "-SkipObsidianInstall",
            ],
        )
    else:
        bash = require("bash")
        env = CHECK_ENV.copy()
        env.update(
            {
                "CODEX_HOME": str(codex_home),
                "OBSIDIAN_VAULT": str(vault),
                "INSTALL_MCP": "0",
            }
        )
        run("Unix installer smoke test", [bash, str(ROOT / "scripts" / "install.sh")], env)

    expected = [
        codex_home / "AGENTS.md",
        codex_home / "skills-index" / "index.md",
        codex_home / "scripts" / "asr3602_build_profile.py",
        codex_home / "scripts" / "asr360x_build_runtime.ps1",
        vault / "Codex" / "AGENTS.md",
    ]
    manifest = json.loads((ROOT / "public-sync-manifest.json").read_text(encoding="utf-8"))
    expected.extend(codex_home / "skills" / name / "SKILL.md" for name in manifest["skills"])
    missing = [str(path) for path in expected if not path.exists()]
    if missing:
        raise SystemExit("installer smoke test missing: " + ", ".join(missing))
    installed = {path.parent.name for path in (codex_home / "skills").glob("*/SKILL.md")}
    if installed != set(manifest["skills"]):
        raise SystemExit("installed Skills differ from the public manifest")
    (codex_home / "skills.disabled").mkdir()
    (codex_home / "plugins" / "cache").mkdir(parents=True)
    run(
        "installed Skill routing",
        [
            sys.executable, "-X", "utf8",
            str(ROOT / "skills/skill-usage-tracker/scripts/registry_audit.py"),
            "--active-root", str(codex_home / "skills"),
            "--disabled-root", str(codex_home / "skills.disabled"),
            "--index", str(codex_home / "skills-index/index.md"),
            "--plugin-cache", str(codex_home / "plugins/cache"),
            "--strict",
        ],
    )


def run_checks() -> int:
    run(
        "privacy scan",
        [sys.executable, "-X", "utf8", str(ROOT / "scripts" / "privacy_scan.py"), "--root", str(ROOT)],
    )

    for relative in PYTHON_TESTS:
        run(relative, [sys.executable, "-X", "utf8", str(ROOT / relative)])

    node = require("node")
    for relative in NODE_TESTS:
        run(relative, [node, str(ROOT / relative)])

    powershell = shutil.which("pwsh")
    if powershell:
        for relative in POWERSHELL_TESTS + (WINDOWS_TESTS if os.name == "nt" else []):
            run(
                relative,
                [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / relative)],
            )
    elif os.name == "nt":
        raise SystemExit("required command is unavailable: pwsh")
    else:
        print("\nPowerShell tests skipped: pwsh is unavailable on this runner")

    print("\npublic repository checks: PASS")
    return 0


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="codex-public-checks-") as temporary:
        root = Path(temporary).resolve()
        scratch = root / "tmp"
        scratch.mkdir()
        CHECK_ENV.update({"HOME": str(root), "USERPROFILE": str(root), "CODEX_HOME": str(root / ".codex")})
        CHECK_ENV.update({"TMP": str(scratch), "TEMP": str(scratch), "TMPDIR": str(scratch)})
        install_smoke_test(root)
        return run_checks()


if __name__ == "__main__":
    sys.exit(main())
