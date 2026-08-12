#!/usr/bin/env python3
"""Fail closed when reusable Codex files contain local or private data."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, replace
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit


SKIP_PARTS = {".git", "__pycache__", "node_modules"}
BINARY_SUFFIXES = {
    ".7z", ".bin", ".bmp", ".dll", ".exe", ".gif", ".ico", ".jpg", ".jpeg",
    ".mdb", ".mp3", ".mp4", ".pdf", ".png", ".pyc", ".so", ".webp", ".zip",
}
FORBIDDEN_FILE_SUFFIXES = {
    ".7z", ".axf", ".bin", ".hex", ".icl", ".ild", ".log", ".mdb", ".mp4", ".zip",
}
FORBIDDEN_FILE_NAMES = {
    ".env", "credentials.json", "id_dsa", "id_ed25519", "id_rsa", "secrets.json",
}
FORBIDDEN_PATH_PARTS = {"DebugConfig", "Listings", "Objects"}
SAFE_URL_HOSTS = {
    "127.0.0.1", "aka.ms", "apache.org", "arm.com", "arxiv.org", "example.com",
    "example.invalid", "github.com", "gnu.org", "keil.com", "localhost",
    "learn.chatgpt.com", "learn.microsoft.com", "microsoft.com", "npmjs.com",
    "obsidian.md", "openai.com", "opensource.org", "pypi.org",
    "raw.githubusercontent.com", "registry.npmjs.org", "registry.npmmirror.com",
    "smithery.ai", "docs.astral.sh", "voidtools.com", "w3.org", "zentao.example",
}


@dataclass(frozen=True)
class Finding:
    rule: str
    path: Path
    line: int
    revision: str = "worktree"


@dataclass(frozen=True)
class ScanTarget:
    path: Path
    data: bytes | None
    revision: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--denylist", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--staged", action="store_true")
    mode.add_argument("--history", action="store_true")
    return parser.parse_args()


def run_git(root: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, check=True
    )
    return result.stdout


def decode_path(value: bytes) -> str:
    return value.decode("utf-8", errors="surrogateescape")


def worktree_targets(root: Path) -> list[ScanTarget]:
    output = run_git(root, "ls-files", "--cached", "--others", "--exclude-standard", "-z")
    targets: list[ScanTarget] = []
    for item in output.split(b"\0"):
        if not item:
            continue
        relative = Path(decode_path(item))
        absolute = root / relative
        targets.append(
            ScanTarget(relative, absolute.read_bytes() if absolute.is_file() else None, "worktree")
        )
    return targets


def staged_targets(root: Path) -> list[ScanTarget]:
    output = run_git(root, "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z")
    targets: list[ScanTarget] = []
    for item in output.split(b"\0"):
        if not item:
            continue
        relative_text = decode_path(item)
        data = run_git(root, "show", f":{relative_text}")
        targets.append(ScanTarget(Path(relative_text), data, "index"))
    return targets


def history_targets(root: Path) -> list[ScanTarget]:
    commits = [line for line in run_git(root, "rev-list", "--all").splitlines() if line]
    seen: set[tuple[str, str]] = set()
    targets: list[ScanTarget] = []
    for commit_bytes in commits:
        commit = commit_bytes.decode("ascii")
        tree = run_git(root, "ls-tree", "-r", "-z", "--full-tree", commit)
        for record in tree.split(b"\0"):
            if not record:
                continue
            metadata, raw_path = record.split(b"\t", 1)
            _mode, object_type, object_id = metadata.split(b" ", 2)
            if object_type != b"blob":
                continue
            relative_text = decode_path(raw_path)
            key = (object_id.decode("ascii"), relative_text)
            if key in seen:
                continue
            seen.add(key)
            data = run_git(root, "cat-file", "blob", key[0])
            targets.append(ScanTarget(Path(relative_text), data, commit[:12]))
    return targets


def targets_for_mode(root: Path, staged: bool, history: bool) -> list[ScanTarget]:
    if staged:
        return staged_targets(root)
    if history:
        return history_targets(root)
    return worktree_targets(root)


def decode_text(path: Path, data: bytes | None) -> str | None:
    if data is None or path.suffix.lower() in BINARY_SUFFIXES:
        return None
    if any(part in SKIP_PARTS for part in path.parts) or b"\0" in data:
        return None
    return data.decode("utf-8", errors="replace")


def read_text(path: Path) -> str | None:
    if not path.is_file():
        return None
    return decode_text(path, path.read_bytes())


def default_denylist(root: Path) -> Path | None:
    local = root / ".privacy-denylist.local.txt"
    if local.exists():
        return local
    private = Path.home() / ".codex" / "secrets" / "repo-privacy" / "denylist.txt"
    return private if private.exists() else None


def load_denylist(path: Path | None) -> list[tuple[str, str]]:
    if path is None or not path.exists():
        return []
    entries: list[tuple[str, str]] = []
    for index, raw in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "\t" in line:
            label, value = line.split("\t", 1)
        else:
            label, value = f"private-term-{index}", line
        value = value.strip()
        if value:
            entries.append((label.strip() or f"private-term-{index}", value.casefold()))
    return entries


def path_findings(path: Path) -> list[Finding]:
    normalized = PurePosixPath(path.as_posix())
    name = normalized.name
    suffix = normalized.suffix.lower()
    findings: list[Finding] = []
    if suffix in FORBIDDEN_FILE_SUFFIXES:
        findings.append(Finding("forbidden-artifact-file", path, 1))
    if name.casefold() in {item.casefold() for item in FORBIDDEN_FILE_NAMES}:
        findings.append(Finding("credential-file-name", path, 1))
    if any(part in FORBIDDEN_PATH_PARTS for part in normalized.parts):
        findings.append(Finding("generated-build-directory", path, 1))
    if ".uvguix." in name.casefold() or suffix in {".key", ".pem", ".pfx", ".p12"}:
        findings.append(Finding("private-or-user-configuration-file", path, 1))
    return findings


def url_findings(text: str, path: Path) -> list[Finding]:
    findings: list[Finding] = []
    for match in re.finditer(r"https?://[^\s<>'\"`)]+", text, flags=re.IGNORECASE):
        parsed = urlsplit(match.group(0).rstrip(".,;"))
        host = (parsed.hostname or "").lower()
        try:
            port = parsed.port
        except ValueError:
            if "{" in match.group(0) or "<" in match.group(0):
                continue
            findings.append(Finding("malformed-url-port", path, text.count("\n", 0, match.start()) + 1))
            continue
        if parsed.username or parsed.password:
            rule = "url-embedded-credentials"
        elif port and host not in {"127.0.0.1", "localhost"}:
            rule = "external-service-url-with-port"
        elif host and host not in SAFE_URL_HOSTS and not any(
            host.endswith("." + safe) for safe in SAFE_URL_HOSTS
        ):
            rule = "unapproved-url-host"
        else:
            continue
        findings.append(Finding(rule, path, text.count("\n", 0, match.start()) + 1))
    return findings


def scan_file(path: Path, text: str, denylist: list[tuple[str, str]]) -> list[Finding]:
    findings: list[Finding] = []
    rules = {
        "literal-windows-user-path": re.compile(r"(?i)\b[A-Z]:[\\/]Users[\\/][^\\/\s`'\"<>]+"),
        "file-uri-user-path": re.compile(r"(?i)file:/+(?:[A-Z]:/)?Users/[^/\s`'\"<>]+"),
        "ssh-remote": re.compile(r"(?i)\bssh://[^\s`'\"<>]+"),
        "private-ip-address": re.compile(
            r"(?<![\d.])(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})(?![\d.])"
        ),
        "credential-assignment": re.compile(
            r"(?i)\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|password|passwd|secret)\b\s*[:=]\s*['\"][^<${][^'\"]{7,}['\"]"
        ),
    }
    for rule, pattern in rules.items():
        for match in pattern.finditer(text):
            findings.append(Finding(rule, path, text.count("\n", 0, match.start()) + 1))

    findings.extend(url_findings(text, path))

    folded = text.casefold()
    for label, value in denylist:
        start = 0
        while True:
            index = folded.find(value, start)
            if index < 0:
                break
            findings.append(Finding(f"denylist:{label}", path, text.count("\n", 0, index) + 1))
            start = index + len(value)

    if path.name == "project-map.md" and "synthetic" not in folded:
        findings.append(Finding("bundled-project-map-is-not-synthetic", path, 1))
    return findings


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    denylist_path = args.denylist.resolve() if args.denylist else default_denylist(root)
    denylist = load_denylist(denylist_path)
    findings: list[Finding] = []
    try:
        targets = targets_for_mode(root, args.staged, args.history)
    except subprocess.CalledProcessError as error:
        print(f"privacy_scan: ERROR (git command failed with exit code {error.returncode})")
        return 2

    for target in targets:
        findings.extend(replace(item, revision=target.revision) for item in path_findings(target.path))
        text = decode_text(target.path, target.data)
        if text is not None:
            findings.extend(
                replace(item, revision=target.revision)
                for item in scan_file(target.path, text, denylist)
            )

    unique = sorted(
        set(findings), key=lambda item: (item.revision, str(item.path), item.line, item.rule)
    )
    if unique:
        print(f"privacy_scan: FAIL ({len(unique)} finding(s))")
        for finding in unique:
            location = f"{finding.path.as_posix()}:{finding.line}"
            print(f"- {finding.rule}: {location} [{finding.revision}]")
        return 1

    mode = "history" if args.history else "staged" if args.staged else "worktree"
    source = str(denylist_path) if denylist_path else "none"
    print(
        f"privacy_scan: PASS (mode: {mode}, targets: {len(targets)}, "
        f"private denylist: {source})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
