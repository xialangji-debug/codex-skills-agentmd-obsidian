#!/usr/bin/env python3
"""Validate project-local ASR360x build profiles before any build mutation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from typing import Any


SCHEMA_VERSION = 1
PROFILES = ("release", "normal-test", "dump-test")
SUPPORT_LEVELS = ("CANDIDATE", "ASR3602_BUILD_VERIFIED", "ASR360X_BUILD_VERIFIED")
QUALIFIED_SUPPORT_LEVELS = ("ASR3602_BUILD_VERIFIED", "ASR360X_BUILD_VERIFIED")
SUPPORTED_BUILD_IDENTITIES = {
    ("THREADX", "LTEGSM", "CRANEG"),
    ("ALIOS", "LITE_LTEONLY", "CRANEL"),
    ("THREADX", "LITE_LTEONLY", "CRANEL"),
}


class ProfileError(RuntimeError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProfileError(f"cannot read adapter JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ProfileError("adapter root must be a JSON object")
    return value


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _required(mapping: dict[str, Any], key: str, expected_type: type | tuple[type, ...]) -> Any:
    value = mapping.get(key)
    if not isinstance(value, expected_type) or isinstance(value, bool) and expected_type is int:
        raise ProfileError(f"adapter field {key!r} has the wrong type")
    if isinstance(value, str) and not value.strip():
        raise ProfileError(f"adapter field {key!r} must not be empty")
    return value


def _relative_path(value: str, field: str) -> str:
    normalized = value.replace("\\", "/")
    pure = PurePosixPath(normalized)
    if pure.is_absolute() or ".." in pure.parts or not pure.parts:
        raise ProfileError(f"adapter field {field!r} must be a safe repository-relative path")
    return normalized


def resolve_repo(repo: str | os.PathLike[str], adapter_path: Path) -> Path:
    if repo:
        root = Path(repo).resolve()
    elif adapter_path.parent.name.lower() == ".codex-project":
        root = adapter_path.parent.parent.resolve()
    else:
        raise ProfileError("--repo is required when the adapter is outside <repo>/.codex-project")
    if not (root / ".git").exists():
        raise ProfileError(f"repository .git file or directory not found: {root}")
    return root


def repo_path(repo: Path, value: str, field: str) -> Path:
    relative = _relative_path(value, field)
    candidate = (repo / Path(relative)).resolve()
    try:
        candidate.relative_to(repo)
    except ValueError as exc:
        raise ProfileError(f"adapter field {field!r} resolves outside repository") from exc
    return candidate


def _run_git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    if proc.returncode != 0:
        raise ProfileError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.replace("\r\n", "\n").rstrip("\n")


def _run_git_bytes(repo: Path, *args: str) -> bytes:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )
    if proc.returncode != 0:
        error = proc.stderr.decode("utf-8", errors="replace").strip()
        raise ProfileError(f"git {' '.join(args)} failed: {error}")
    return proc.stdout


def git_identity(repo: Path) -> dict[str, Any]:
    dirty = _run_git(repo, "status", "--porcelain=v1", "--untracked-files=all")
    return {
        "branch": _run_git(repo, "branch", "--show-current"),
        "head": _run_git(repo, "rev-parse", "HEAD"),
        "dirty": dirty.splitlines(),
        "dirtySummarySha256": sha256_bytes(dirty.encode("utf-8")),
    }


_RELEASE_VERSION_PATH = "gui/lv_watch/lv_apps/yl/yl.h"
_DEVICE_VERSION_DEFINE = re.compile(
    rb'(?m)^(?P<prefix>[ \t]*#define[ \t]+yl_device_ver[ \t]+")(?P<value>[^"\r\n]+)(?P<suffix>"[^\r\n]*\r?)$'
)
_VERSION_TIME = re.compile(rb"_\d{8}_\d{4}_")


def _validate_release_version_resume(repo: Path, identity: dict[str, Any], expected_release_time: str) -> dict[str, Any]:
    if not re.fullmatch(r"\d{8}_\d{4}", expected_release_time or ""):
        raise ProfileError("--expected-release-time must be YYYYMMDD_HHMM")
    dirty = identity["dirty"]
    if len(dirty) != 1:
        raise ProfileError("release resume requires exactly one dirty path")
    status = dirty[0]
    if len(status) < 4 or status[:2] != " M" or status[3:].replace("\\", "/") != _RELEASE_VERSION_PATH:
        raise ProfileError(
            f"release resume permits only an unstaged modification of {_RELEASE_VERSION_PATH}; got: {status}"
        )

    worktree_path = repo / Path(_RELEASE_VERSION_PATH)
    head_bytes = _run_git_bytes(
        repo,
        "cat-file",
        "--filters",
        f"--path={_RELEASE_VERSION_PATH}",
        f"HEAD:{_RELEASE_VERSION_PATH}",
    )
    worktree_bytes = worktree_path.read_bytes()
    head_matches = list(_DEVICE_VERSION_DEFINE.finditer(head_bytes))
    worktree_matches = list(_DEVICE_VERSION_DEFINE.finditer(worktree_bytes))
    if len(head_matches) != 1 or len(worktree_matches) != 1:
        raise ProfileError("release resume requires exactly one yl_device_ver definition in HEAD and worktree")

    head_version = head_matches[0].group("value")
    worktree_version = worktree_matches[0].group("value")
    expected_token = f"_{expected_release_time}_".encode("ascii")
    if expected_token not in worktree_version:
        raise ProfileError("worktree yl_device_ver does not contain the expected release time")
    if len(_VERSION_TIME.findall(head_version)) != 1 or len(_VERSION_TIME.findall(worktree_version)) != 1:
        raise ProfileError("yl_device_ver must contain exactly one YYYYMMDD_HHMM time token")
    if _VERSION_TIME.sub(b"_<RELEASE_TIME>_", head_version) != _VERSION_TIME.sub(
        b"_<RELEASE_TIME>_", worktree_version
    ):
        raise ProfileError("release resume only permits changing the yl_device_ver time token")

    match = head_matches[0]
    reconstructed = head_bytes[: match.start("value")] + worktree_version + head_bytes[match.end("value") :]
    if reconstructed != worktree_bytes:
        raise ProfileError("yl.h contains changes outside the yl_device_ver value")
    return {
        "allowed": True,
        "path": _RELEASE_VERSION_PATH,
        "expectedReleaseTime": expected_release_time,
        "headVersion": head_version.decode("utf-8", errors="replace"),
        "worktreeVersion": worktree_version.decode("utf-8", errors="replace"),
    }


def validate_adapter(adapter: dict[str, Any], repo: Path) -> dict[str, Any]:
    if adapter.get("schemaVersion") != SCHEMA_VERSION:
        raise ProfileError(f"adapter schemaVersion must be {SCHEMA_VERSION}")
    for key in ("adapterId", "product", "supportLevel", "chipId", "targetOs", "psMode", "buildTarget"):
        _required(adapter, key, str)
    if adapter["supportLevel"] not in SUPPORT_LEVELS:
        raise ProfileError(f"unsupported adapter supportLevel: {adapter['supportLevel']}")
    build_identity = (adapter["targetOs"], adapter["psMode"], adapter["chipId"])
    if build_identity not in SUPPORTED_BUILD_IDENTITIES:
        supported = ", ".join("/".join(identity) for identity in sorted(SUPPORTED_BUILD_IDENTITIES))
        raise ProfileError(
            "unsupported ASR360x TARGET_OS/PS_MODE/CHIP_ID combination: "
            f"{'/'.join(build_identity)}; supported: {supported}"
        )

    build = _required(adapter, "build", dict)
    _required(build, "command", str)
    prebuild = _required(build, "preBuild", dict)
    _required(prebuild, "command", str)
    _required(build, "commandArgs", list)
    _required(prebuild, "commandArgs", list)
    expected_command = "make {target} TARGET_OS={os} PS_MODE={ps} CHIP_ID={chip}".format(
        target=adapter["buildTarget"], os=adapter["targetOs"], ps=adapter["psMode"], chip=adapter["chipId"]
    )
    if " ".join(build["command"].split()) != expected_command:
        raise ProfileError(f"build.command must be exactly: {expected_command}")

    watchdog = _required(adapter, "watchdogConfig", dict)
    for key in ("path", "entryId", "entryImage"):
        _required(watchdog, key, str)
    charging = _required(adapter, "chargingAnimation", dict)
    for key in ("path", "defineName", "stubStrategy"):
        _required(charging, key, str)
    for key in ("releaseValue", "dumpTestValue"):
        if charging.get(key) not in (0, 1):
            raise ProfileError(f"chargingAnimation.{key} must be 0 or 1")
    if charging["stubStrategy"] not in ("none", "inject-watch-charging-api-stubs"):
        raise ProfileError(f"unsupported charging stub strategy: {charging['stubStrategy']}")
    if charging["stubStrategy"] != "none":
        _required(charging, "stubSourcePath", str)

    artifacts = _required(adapter, "artifacts", dict)
    for key in ("outputDir", "zipName", "mdbName"):
        _required(artifacts, key, str)
    temporary = _required(adapter, "allowedTemporaryFiles", list)
    for index, value in enumerate(temporary):
        if not isinstance(value, str):
            raise ProfileError(f"allowedTemporaryFiles[{index}] must be a string")
        _relative_path(value, f"allowedTemporaryFiles[{index}]")

    expected_temporary = {watchdog["path"].replace("\\", "/")}
    if charging["releaseValue"] != charging["dumpTestValue"]:
        expected_temporary.add(charging["path"].replace("\\", "/"))
    if charging["stubStrategy"] != "none":
        expected_temporary.add(charging["stubSourcePath"].replace("\\", "/"))
    if not expected_temporary.issubset({item.replace("\\", "/") for item in temporary}):
        missing = sorted(expected_temporary - {item.replace("\\", "/") for item in temporary})
        raise ProfileError(f"allowedTemporaryFiles is missing required paths: {', '.join(missing)}")

    for field, relative in (
        ("watchdogConfig.path", watchdog["path"]),
        ("chargingAnimation.path", charging["path"]),
    ):
        path = repo_path(repo, relative, field)
        if not path.is_file():
            raise ProfileError(f"required adapter file does not exist: {path}")
    if charging["stubStrategy"] != "none":
        stub_path = repo_path(repo, charging["stubSourcePath"], "chargingAnimation.stubSourcePath")
        if not stub_path.is_file():
            raise ProfileError(f"charging stub source does not exist: {stub_path}")

    acceptance = adapter.get("dumpAcceptance")
    if acceptance is not None:
        if not isinstance(acceptance, dict):
            raise ProfileError("dumpAcceptance must be an object")
        for key in ("sourcePath", "marker"):
            _required(acceptance, key, str)
        source = repo_path(repo, acceptance["sourcePath"], "dumpAcceptance.sourcePath")
        if not source.is_file():
            raise ProfileError(f"Dump acceptance source does not exist: {source}")

    return {
        "schemaVersion": SCHEMA_VERSION,
        "adapterId": adapter["adapterId"],
        "product": adapter["product"],
        "supportLevel": adapter["supportLevel"],
        "chipId": adapter["chipId"],
        "targetOs": adapter["targetOs"],
        "psMode": adapter["psMode"],
        "buildTarget": adapter["buildTarget"],
        "buildCommand": build["command"],
        "preBuildCommand": prebuild["command"],
    }


def _load_watchdog(repo: Path, rule: dict[str, Any]) -> tuple[Path, list[dict[str, Any]]]:
    path = repo_path(repo, rule["path"], "watchdogConfig.path")
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProfileError(f"invalid watchdog config: {path}: {exc}") from exc
    if not isinstance(value, list):
        raise ProfileError("watchdog config root must be an array")
    matches = [
        item for item in value
        if isinstance(item, dict) and item.get("id") == rule["entryId"] and item.get("image") == rule["entryImage"]
    ]
    return path, matches


def _read_define(repo: Path, charging: dict[str, Any]) -> tuple[Path, int]:
    path = repo_path(repo, charging["path"], "chargingAnimation.path")
    data = path.read_bytes()
    pattern = re.compile(
        rb"(?m)^\s*#define\s+" + re.escape(charging["defineName"].encode("ascii")) + rb"\s+([01])\s*$"
    )
    matches = pattern.findall(data)
    if len(matches) != 1:
        raise ProfileError(f"expected exactly one {charging['defineName']} definition, found {len(matches)}")
    return path, int(matches[0])


def _variant_checks(repo: Path, adapter: dict[str, Any]) -> list[str]:
    variant_path = repo / ".codex-project" / "variant.md"
    if not variant_path.is_file():
        raise ProfileError(f"project variant fingerprint is missing: {variant_path}")
    variant = variant_path.read_text(encoding="utf-8-sig", errors="replace")
    required = [
        f"CHIP_ID：`{adapter['chipId']}`",
        f"TARGET_OS：`{adapter['targetOs']}`",
        f"PS_MODE：`{adapter['psMode']}`",
        f"构建目标：`{adapter['buildTarget']}`",
        f"构建命令：`{adapter['build']['command']}`",
    ]
    missing = [item for item in required if item not in variant]
    if missing:
        raise ProfileError("adapter does not match .codex-project/variant.md: " + "; ".join(missing))
    return required


def _forbidden_markers(repo: Path, adapter: dict[str, Any]) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    for index, rule in enumerate(adapter.get("forbiddenSourceMarkers") or []):
        if not isinstance(rule, dict):
            raise ProfileError(f"forbiddenSourceMarkers[{index}] must be an object")
        path = repo_path(repo, _required(rule, "path", str), f"forbiddenSourceMarkers[{index}].path")
        marker = _required(rule, "marker", str)
        if not path.is_file():
            raise ProfileError(f"forbidden marker source does not exist: {path}")
        if marker.encode("utf-8") in path.read_bytes():
            found.append({"path": str(path), "marker": marker})
    return found


def preflight(
    profile: str,
    adapter_path: Path,
    repo: Path,
    *,
    allow_candidate: bool = False,
    allow_release_version_resume: bool = False,
    expected_release_time: str = "",
) -> dict[str, Any]:
    if profile not in PROFILES:
        raise ProfileError(f"unsupported build profile: {profile}")
    adapter = read_json(adapter_path)
    summary = validate_adapter(adapter, repo)
    if adapter["supportLevel"] not in QUALIFIED_SUPPORT_LEVELS and not allow_candidate:
        raise ProfileError(
            f"adapter {adapter['adapterId']} is {adapter['supportLevel']}; qualification requires an explicit allow-candidate run"
        )
    variant_checks = _variant_checks(repo, adapter)
    identity = git_identity(repo)
    release_resume = {"allowed": False}
    if profile == "release" and identity["dirty"]:
        if not allow_release_version_resume:
            raise ProfileError("release profile requires a clean worktree before Git sync or version mutation")
        release_resume = _validate_release_version_resume(repo, identity, expected_release_time)

    watchdog_path, watchdog_matches = _load_watchdog(repo, adapter["watchdogConfig"])
    if len(watchdog_matches) != 1:
        raise ProfileError(f"expected exactly one EEHandlerConfig.nvm watchdog entry, found {len(watchdog_matches)}")
    charging_path, charging_value = _read_define(repo, adapter["chargingAnimation"])
    expected_charge = adapter["chargingAnimation"]["releaseValue"]
    if profile != "release" and charging_value != expected_charge:
        raise ProfileError(
            f"release charging configuration mismatch: expected {expected_charge}, got {charging_value} in {charging_path}"
        )
    forbidden = _forbidden_markers(repo, adapter)
    if forbidden:
        details = ", ".join(f"{item['path']}:{item['marker']}" for item in forbidden)
        raise ProfileError(f"temporary DumpTest source marker remains in worktree: {details}")

    if profile == "dump-test":
        temporary = {
            "watchdogEntry": {
                "path": str(watchdog_path),
                "entryId": adapter["watchdogConfig"]["entryId"],
                "entryImage": adapter["watchdogConfig"]["entryImage"],
                "action": "remove-exactly-one",
            },
            "chargingAnimation": {
                "path": str(charging_path),
                "from": expected_charge,
                "to": adapter["chargingAnimation"]["dumpTestValue"],
                "stubStrategy": adapter["chargingAnimation"]["stubStrategy"],
            },
            "allowedFiles": adapter["allowedTemporaryFiles"],
        }
    else:
        temporary = {"allowed": False, "files": []}

    return {
        "status": "PASSED",
        "buildProfile": profile,
        "repo": str(repo),
        "adapterPath": str(adapter_path),
        "adapterSha256": sha256_file(adapter_path),
        "adapter": summary,
        "source": identity,
        "variantChecks": variant_checks,
        "preconditions": {
            "watchdogEntryCount": len(watchdog_matches),
            "chargingAnimationValue": charging_value,
            "forbiddenMarkersFound": forbidden,
            "releaseVersionResume": release_resume,
        },
        "temporaryChanges": temporary,
    }


def describe(profile: str, adapter_path: Path, repo: Path) -> dict[str, Any]:
    adapter = read_json(adapter_path)
    summary = validate_adapter(adapter, repo)
    return {
        "status": "DESCRIBED",
        "buildProfile": profile,
        "repo": str(repo),
        "adapterPath": str(adapter_path),
        "adapterSha256": sha256_file(adapter_path),
        "adapter": summary,
        "policy": {
            "temporaryChangesAllowed": profile == "dump-test",
            "uploadAllowed": profile == "release",
            "desktopSuccessOnly": profile == "dump-test",
        },
    }


def _write_result(result: dict[str, Any], output: str | None) -> None:
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if output:
        path = Path(output).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        partial = path.with_name(path.name + f".partial-{os.getpid()}")
        partial.write_text(rendered, encoding="utf-8", newline="\n")
        os.replace(partial, path)
    print(rendered, end="")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("validate-adapter", "describe", "preflight"):
        child = subparsers.add_parser(name)
        child.add_argument("--repo", required=True)
        child.add_argument("--adapter", required=True)
        child.add_argument("--json-out")
        if name != "validate-adapter":
            child.add_argument("--profile", choices=PROFILES, required=True)
        if name == "preflight":
            child.add_argument("--allow-candidate", action="store_true", help=argparse.SUPPRESS)
            child.add_argument("--allow-release-version-resume", action="store_true", help=argparse.SUPPRESS)
            child.add_argument("--expected-release-time", default="", help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    adapter_path = Path(args.adapter).resolve()
    repo = resolve_repo(args.repo, adapter_path)
    try:
        if args.command == "validate-adapter":
            adapter = read_json(adapter_path)
            result = {
                "status": "VALID",
                "repo": str(repo),
                "adapterPath": str(adapter_path),
                "adapterSha256": sha256_file(adapter_path),
                "adapter": validate_adapter(adapter, repo),
            }
        elif args.command == "describe":
            result = describe(args.profile, adapter_path, repo)
        else:
            result = preflight(
                args.profile,
                adapter_path,
                repo,
                allow_candidate=args.allow_candidate,
                allow_release_version_resume=args.allow_release_version_resume,
                expected_release_time=args.expected_release_time,
            )
    except ProfileError as exc:
        result = {
            "status": "BLOCKED",
            "command": args.command,
            "buildProfile": getattr(args, "profile", None),
            "repo": str(repo),
            "adapterPath": str(adapter_path),
            "error": str(exc),
        }
        _write_result(result, args.json_out)
        return 2
    _write_result(result, args.json_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
