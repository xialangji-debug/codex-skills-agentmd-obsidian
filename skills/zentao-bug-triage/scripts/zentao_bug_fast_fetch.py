#!/usr/bin/env python3
"""Fetch current-project Zentao bugs with an existence-first init gate."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from zentao_snapshot_reconcile import prepare_refresh, reconcile


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(line_buffering=True)


REQUIRED_CONTEXT = (
    "AGENTS.md",
    ".codex-project/index.md",
    ".codex-project/zentao.md",
    ".codex-project/build.md",
    ".codex-project/protocol.md",
    ".codex-project/variant.md",
    ".codex-project/device.md",
    ".codex-project/memory.md",
)


def run_text(command: list[str], cwd: Path) -> str:
    result = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(command)}\n{detail}")
    return result.stdout.strip()


def git(repo: Path, *args: str) -> str:
    return run_text(["git", "-C", str(repo), *args], repo)


def resolve_repo(value: str) -> Path:
    candidate = Path(value).expanduser().resolve()
    root = run_text(["git", "-C", str(candidate), "rev-parse", "--show-toplevel"], candidate)
    return Path(root).resolve()


def read_device_ver(repo: Path) -> str:
    yl = repo / "gui" / "lv_watch" / "lv_apps" / "yl" / "yl.h"
    if not yl.exists():
        return ""
    text = yl.read_text(encoding="utf-8", errors="replace")
    match = re.search(r'#define\s+yl_device_ver\s+"([^"]+)"', text)
    return match.group(1) if match else ""


def live_context(repo: Path) -> dict[str, str]:
    return {
        "repo": str(repo),
        "repoName": repo.name,
        "branch": git(repo, "branch", "--show-current"),
        "commit": git(repo, "rev-parse", "--short", "HEAD"),
        "deviceVer": read_device_ver(repo),
    }


def missing_context_files(repo: Path) -> list[str]:
    return [relative for relative in REQUIRED_CONTEXT if not (repo / relative).is_file()]


def run_onboard(repo: Path) -> None:
    script = Path.home() / ".codex" / "skills" / "asr3601-project-onboard" / "scripts" / "project_onboard.py"
    if not script.is_file():
        raise RuntimeError(f"Project onboarding script not found: {script}")
    print("[fast-fetch] initialization=missing-or-stale; running project-onboard")
    result = subprocess.run(
        [sys.executable, "-X", "utf8", str(script), "--repo", str(repo), "--write"],
        cwd=repo,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Project onboarding failed with exit code {result.returncode}")
    missing = missing_context_files(repo)
    if missing:
        raise RuntimeError(f"Project onboarding did not create required context: {', '.join(missing)}")


def node_environment() -> dict[str, str]:
    env = os.environ.copy()
    runtime = Path.home() / ".cache" / "codex-runtimes" / "codex-primary-runtime" / "dependencies" / "node" / "node_modules"
    candidates = [runtime, runtime / ".pnpm" / "node_modules"]
    entries = [str(path) for path in candidates if path.is_dir()]
    existing = env.get("NODE_PATH", "")
    if existing:
        entries.append(existing)
    if entries:
        env["NODE_PATH"] = os.pathsep.join(entries)
    return env


def stream_command(command: list[str], cwd: Path, env: dict[str, str]) -> list[str]:
    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    lines: list[str] = []
    assert process.stdout is not None
    for line in process.stdout:
        print(line, end="")
        lines.append(line.rstrip("\r\n"))
    return_code = process.wait()
    if return_code != 0:
        raise RuntimeError(f"Zentao snapshot failed with exit code {return_code}")
    return lines


def snapshot_command(
    repo: Path,
    live: dict[str, str],
    bug_status: str,
    limit: int,
    detail_concurrency: int,
    bug_ids: str = "",
    status_refresh: bool = False,
) -> list[str]:
    node = shutil.which("node")
    if not node:
        raise RuntimeError("Node.js was not found on PATH")
    script = Path(__file__).with_name("zentao_bug_snapshot.js")
    command = [
        node,
        str(script),
        "--repo",
        str(repo),
        "--expect-repo-name",
        live["repoName"],
        "--expect-branch",
        live["branch"],
    ]
    if bug_ids:
        command.extend(["--ids", bug_ids])
        if status_refresh:
            command.extend(["--no-download-attachments", "--no-work-md", "--no-memory-link"])
        else:
            command.append("--download-attachments")
    else:
        command.extend(
            [
                "--bug-status",
                bug_status,
                "--limit",
                str(limit),
                "--detail-concurrency",
                str(detail_concurrency),
                "--detail-retries",
                "2",
                "--detail-timeout-ms",
                "60000",
                "--download-attachments",
            ]
        )
    return command


def fetch_snapshot(
    repo: Path,
    bug_status: str,
    limit: int,
    detail_concurrency: int,
    bug_ids: str = "",
    status_refresh: bool = False,
) -> Path:
    live = live_context(repo)
    lines = stream_command(
        snapshot_command(repo, live, bug_status, limit, detail_concurrency, bug_ids, status_refresh),
        repo,
        node_environment(),
    )
    matches = []
    for line in lines:
        match = re.match(r"^Saved:\s+(.+[\\/]bugs\.json)$", line.strip())
        if match:
            matches.append(Path(match.group(1)))
    if not matches or not matches[-1].is_file():
        raise RuntimeError("Snapshot completed but bugs.json path was not found in its output")
    return matches[-1]


def normalized_path(value: str | Path) -> str:
    return os.path.normcase(os.path.normpath(str(Path(value).resolve())))


def normalized_project(value: object) -> str:
    return "".join(str(value or "").split())


def validate_snapshot(
    snapshot_path: Path,
    repo: Path,
    bug_status: str,
    expected_product: str = "",
) -> tuple[dict, list[str], dict[str, list[str]], list[str]]:
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    context = payload.get("context") or {}
    resolution = payload.get("projectResolution") or {}
    bugs = payload.get("bugs") or []
    live = live_context(repo)
    errors: list[str] = []
    warnings: list[str] = []

    if not context.get("repo") or normalized_path(context["repo"]) != normalized_path(repo):
        errors.append(f"repo mismatch: snapshot={context.get('repo')} live={repo}")
    for key in ("repoName", "branch", "commit", "deviceVer"):
        if str(context.get(key, "")) != live[key]:
            errors.append(f"{key} mismatch: snapshot={context.get(key)} live={live[key]}")
    if context.get("expectedRepoName") and context.get("expectedRepoName") != live["repoName"]:
        errors.append("expected repo guard does not match live repo")
    if context.get("expectedBranch") and context.get("expectedBranch") != live["branch"]:
        errors.append("expected branch guard does not match live branch")

    product = expected_product or context.get("productName") or resolution.get("productName") or ""
    if resolution.get("mode") == "project" and not product:
        errors.append("project fetch has no canonical product name")
    if resolution.get("mode") != "project" and not expected_product:
        warnings.append(f"project mapping is not exact; fetch mode={context.get('fetchMode', 'unknown')}")

    missing_attachments: dict[str, list[str]] = {}
    for bug in bugs:
        bug_id = str(bug.get("id", "unknown"))
        if not bug.get("detailFetched"):
            errors.append(f"bug {bug_id} detail was not fetched")
        if bug_status == "active" and str(bug.get("status", "")).strip().lower() not in {
            "active",
            "激活",
            "激活中",
        }:
            errors.append(f"bug {bug_id} status is {bug.get('status')}, expected active")
        if product and normalized_project(bug.get("product")) != normalized_project(product):
            errors.append(f"bug {bug_id} product mismatch: {bug.get('product')} != {product}")

        downloaded = {str(item.get("url", "")): item for item in bug.get("attachments") or []}
        for link in bug.get("attachmentLinks") or []:
            url = str(link.get("href", ""))
            item = downloaded.get(url)
            local_path = Path(str(item.get("path", ""))) if item else None
            if not item or not local_path or not local_path.is_file() or local_path.stat().st_size <= 0:
                missing_attachments.setdefault(bug_id, []).append(str(link.get("text") or url))

    return payload, errors, missing_attachments, warnings


def variant_is_stale(repo: Path, payload: dict) -> bool:
    variant = repo / ".codex-project" / "variant.md"
    if not variant.is_file():
        return True
    text = variant.read_text(encoding="utf-8", errors="replace")
    context = payload.get("context") or {}
    expected_lines = [
        ("branch", "- branch：`{}`"),
        ("commit", "- commit：`{}`"),
        ("deviceVer", "- `yl_device_ver`：`{}`"),
        ("projectName", "- 禅道项目：`{}`"),
        ("productName", "- 禅道产品：`{}`"),
        ("projectId", "- project_id：`{}`"),
        ("productId", "- product_id：`{}`"),
    ]
    for key, template in expected_lines:
        value = str(context.get(key, ""))
        if value and template.format(value) not in text:
            return True
    return False


def print_validation(
    snapshot_path: Path,
    errors: list[str],
    missing: dict[str, list[str]],
    warnings: list[str],
) -> None:
    print(f"[fast-fetch] snapshot={snapshot_path}")
    for warning in warnings:
        print(f"[fast-fetch] warning={warning}")
    for error in errors:
        print(f"[fast-fetch] error={error}")
    if missing:
        print(f"[fast-fetch] missing-attachments={','.join(sorted(missing))}")
    if not errors and not missing:
        print("[fast-fetch] postcheck=ok")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Existence-first current-project Zentao fetch with post-fetch validation."
    )
    parser.add_argument("--repo", default=".")
    parser.add_argument("--bug-status", default="active", choices=("active", "all", "resolved", "closed"))
    parser.add_argument("--limit", type=int, default=80)
    parser.add_argument("--detail-concurrency", type=int, default=4)
    parser.add_argument("--dry-run", action="store_true", help="Check only whether onboarding would run.")
    parser.add_argument("--validate-only", type=Path, help="Validate an existing bugs.json without network access.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = resolve_repo(args.repo)
    missing_context = missing_context_files(repo)

    if args.dry_run:
        state = "missing" if missing_context else "ready"
        action = "initialize-then-fetch" if missing_context else "fetch-directly"
        print(f"[fast-fetch] initialization={state}")
        print(f"[fast-fetch] action={action}")
        if missing_context:
            print(f"[fast-fetch] missing={','.join(missing_context)}")
        return 0

    if args.validate_only:
        payload, errors, missing, warnings = validate_snapshot(
            args.validate_only.resolve(), repo, args.bug_status
        )
        print_validation(args.validate_only.resolve(), errors, missing, warnings)
        if variant_is_stale(repo, payload):
            print("[fast-fetch] project-context=stale; refresh would run after fetch")
        return 1 if errors else 0

    initialized_before = not missing_context
    print(f"[fast-fetch] initialization={'ready' if initialized_before else 'missing'}")
    if missing_context:
        run_onboard(repo)
    else:
        print("[fast-fetch] action=fetch-directly")

    snapshot = fetch_snapshot(repo, args.bug_status, args.limit, args.detail_concurrency)
    payload, errors, missing, warnings = validate_snapshot(snapshot, repo, args.bug_status)

    bug_error_ids: set[str] = set()
    context_errors: list[str] = []
    for error in errors:
        match = re.match(r"^bug\s+(\S+)\s+", error)
        if match:
            bug_error_ids.add(match.group(1))
        else:
            context_errors.append(error)

    if context_errors:
        print_validation(snapshot, context_errors, missing, warnings)
        print("[fast-fetch] action=refresh-context-and-refetch-once")
        run_onboard(repo)
        snapshot = fetch_snapshot(repo, args.bug_status, args.limit, args.detail_concurrency)
        payload, errors, missing, warnings = validate_snapshot(snapshot, repo, args.bug_status)
        bug_error_ids = set()
        context_errors = []
        for error in errors:
            match = re.match(r"^bug\s+(\S+)\s+", error)
            if match:
                bug_error_ids.add(match.group(1))
            else:
                context_errors.append(error)
        if context_errors:
            print_validation(snapshot, context_errors, missing, warnings)
            raise RuntimeError("Post-fetch context/product validation still failed after one refresh")

    retry_snapshots: list[Path] = []
    expected_product = str((payload.get("context") or {}).get("productName", ""))
    retry_ids = sorted(set(missing) | bug_error_ids)
    for bug_id in retry_ids:
        print(f"[fast-fetch] attachment-retry={bug_id}")
        retry = fetch_snapshot(repo, args.bug_status, 1, 1, bug_id)
        _, retry_errors, retry_missing, retry_warnings = validate_snapshot(
            retry, repo, args.bug_status, expected_product=expected_product
        )
        print_validation(retry, retry_errors, retry_missing, retry_warnings)
        if retry_errors or retry_missing:
            raise RuntimeError(f"Attachment retry failed for bug {bug_id}")
        retry_snapshots.append(retry)

    if variant_is_stale(repo, payload):
        print("[fast-fetch] project-context=stale; refreshing after successful fetch")
        run_onboard(repo)
        context_refresh = "performed-after-fetch"
    else:
        context_refresh = "skipped"

    reconcile_plan = prepare_refresh(snapshot)
    status_snapshots: list[Path] = []
    refresh_ids = reconcile_plan["refresh_ids"]
    if refresh_ids:
        print("[fast-fetch] status-refresh=" + ",".join(refresh_ids))
        status_snapshot = fetch_snapshot(
            repo,
            "all",
            max(1, len(refresh_ids)),
            min(args.detail_concurrency, max(1, len(refresh_ids))),
            ",".join(refresh_ids),
            status_refresh=True,
        )
        _, status_errors, _, status_warnings = validate_snapshot(
            status_snapshot,
            repo,
            "all",
            expected_product=expected_product,
        )
        print_validation(status_snapshot, status_errors, {}, status_warnings)
        if status_errors:
            raise RuntimeError("Status refresh failed exact-context validation")
        status_snapshots.append(status_snapshot)

    reconciliation = reconcile(snapshot, status_snapshots, write_memory=True)
    print(f"[fast-fetch] reconciliation-state={reconciliation['state_path']}")
    print(f"[fast-fetch] reconciliation-events={len(reconciliation['events'])}")
    print(reconciliation["report"], end="")

    print_validation(snapshot, context_errors, {}, warnings)
    print(f"[fast-fetch] context-refresh={context_refresh}")
    if retry_snapshots:
        print("[fast-fetch] retry-snapshots=" + ",".join(str(path) for path in retry_snapshots))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"[fast-fetch] fatal={error}", file=sys.stderr)
        raise SystemExit(1)
