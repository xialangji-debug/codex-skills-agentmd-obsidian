#!/usr/bin/env python3
"""Run deterministic, offline checks for the public repository."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

PYTHON_TESTS = [
    "scripts/test_privacy_scan.py",
    "skills/asr3601-cross-branch-porting/scripts/test_ordered_cherry_pick.py",
    "skills/asr3601-fix-closeout-reporter/scripts/test_closeout_verification.py",
    "skills/asr3601-fix-closeout-reporter/scripts/test_validation_debt_report.py",
    "skills/asr3601-project-onboard/scripts/test_project_onboard.py",
    "skills/asr360x-bug-delivery-orchestrator/scripts/test_delivery_state.py",
    "skills/obsidian-fix-pattern-memory/scripts/test_fix_memory.py",
    "skills/obsidian-fix-pattern-memory/scripts/test_memory_trust.py",
    "skills/skill-usage-tracker/scripts/test_incremental_scan.py",
    "skills/zentao-bug-triage/scripts/test_snapshot_reconcile.py",
]

NODE_TESTS = [
    "skills/zentao-bug-resolver/scripts/zentao_bug_resolver.test.js",
    "skills/zentao-bug-triage/scripts/test_bug_labels.js",
    "skills/zentao-bug-triage/scripts/test_memory_linkage.js",
    "skills/zentao-bug-triage/scripts/test_project_matching.js",
]

POWERSHELL_TESTS = [
    "skills/aa-skill-router/scripts/test_embedded_target_preflight.ps1",
    "skills/asr3602-local-build-flash/scripts/test_local_build_flash.ps1",
]


def run(label: str, command: list[str], env: dict[str, str] | None = None) -> None:
    print(f"\n== {label} ==")
    result = subprocess.run(command, cwd=ROOT, env=env)
    if result.returncode != 0:
        raise SystemExit(f"{label} failed with exit code {result.returncode}")


def require(command: str) -> str:
    resolved = shutil.which(command)
    if not resolved:
        raise SystemExit(f"required command is unavailable: {command}")
    return resolved


def install_smoke_test() -> None:
    with tempfile.TemporaryDirectory(prefix="codex-public-install-") as temp:
        temp_root = Path(temp)
        codex_home = temp_root / "codex-home"
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
            env = os.environ.copy()
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
            codex_home / "skills" / "aa-skill-router" / "SKILL.md",
            codex_home / "skills-index" / "index.md",
            vault / "Codex" / "AGENTS.md",
        ]
        missing = [str(path) for path in expected if not path.exists()]
        if missing:
            raise SystemExit("installer smoke test missing: " + ", ".join(missing))


def main() -> int:
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
        for relative in POWERSHELL_TESTS:
            run(
                relative,
                [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / relative)],
            )
    elif os.name == "nt":
        raise SystemExit("required command is unavailable: pwsh")
    else:
        print("\nPowerShell tests skipped: pwsh is unavailable on this runner")

    install_smoke_test()
    print("\npublic repository checks: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
