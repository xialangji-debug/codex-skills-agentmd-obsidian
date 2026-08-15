#!/usr/bin/env python3
"""Build, scan, compare, and optionally apply the public Codex snapshot."""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath

import privacy_scan


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "public-sync-manifest.json"
SKILL_NAME = re.compile(r"^[a-z0-9][a-z0-9-]*$")
GITHUB_REPOSITORY = re.compile(
    r"https:" + r"//github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?"
)
SKILLS_START = "<!-- BEGIN PUBLIC SKILLS -->"
SKILLS_END = "<!-- END PUBLIC SKILLS -->"
MCP_START = "<!-- BEGIN PUBLIC MCP -->"
MCP_END = "<!-- END PUBLIC MCP -->"


class SyncError(RuntimeError):
    """A fail-closed public sync error."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--codex-home", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--denylist", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--check", action="store_true")
    return parser.parse_args()


def normalized_relative(value: str, label: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise SyncError(f"{label} must be a non-empty relative path")
    posix = PurePosixPath(value)
    if (
        posix.is_absolute()
        or ".." in posix.parts
        or posix == PurePosixPath(".")
        or "\\" in value
        or any(":" in part or part == ".git" for part in posix.parts)
    ):
        raise SyncError(f"{label} must stay inside its configured root")
    return Path(*posix.parts)


def load_manifest(path: Path) -> dict[str, object]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SyncError(f"cannot read manifest: {error}") from error
    if not isinstance(manifest, dict) or manifest.get("version") != 1:
        raise SyncError("manifest version must be 1")
    allowed = {
        "version",
        "repository",
        "global_files",
        "skills",
        "mcp_packages",
        "exclude_globs",
    }
    unknown = sorted(set(manifest) - allowed)
    if unknown:
        raise SyncError("unknown manifest keys: " + ", ".join(unknown))
    for key in ("global_files", "skills", "mcp_packages", "exclude_globs"):
        if not isinstance(manifest.get(key), list):
            raise SyncError(f"manifest field must be a list: {key}")
    repository = manifest.get("repository")
    if not isinstance(repository, str) or not GITHUB_REPOSITORY.fullmatch(repository):
        raise SyncError("manifest repository must be an HTTPS GitHub repository URL")
    return manifest


def is_excluded(relative: Path, patterns: list[str]) -> bool:
    value = relative.as_posix()
    return any(
        fnmatch.fnmatchcase(value, pattern)
        or fnmatch.fnmatchcase(relative.name, pattern)
        or any(fnmatch.fnmatchcase(part, pattern.rstrip("/**")) for part in relative.parts)
        for pattern in patterns
    )


def copy_candidate_file(source: Path, destination: Path) -> None:
    if source.is_symlink():
        raise SyncError(f"symbolic links are not allowed: {source}")
    if not source.is_file():
        raise SyncError(f"required public source is missing: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(source.read_bytes())


def copy_candidate_tree(
    source: Path,
    destination: Path,
    patterns: list[str],
) -> None:
    if source.is_symlink() or not source.is_dir():
        raise SyncError(f"required public source directory is missing: {source}")
    copied = 0
    for current, directories, files in os.walk(source, followlinks=False):
        current_path = Path(current)
        relative_root = current_path.relative_to(source)
        for directory in list(directories):
            child = current_path / directory
            relative = relative_root / directory
            if child.is_symlink():
                raise SyncError(f"symbolic links are not allowed: {child}")
            if is_excluded(relative, patterns):
                directories.remove(directory)
        for filename in sorted(files):
            child = current_path / filename
            relative = relative_root / filename
            if is_excluded(relative, patterns):
                continue
            copy_candidate_file(child, destination / relative)
            copied += 1
    if copied == 0:
        raise SyncError(f"public source directory is empty after exclusions: {source}")


def replace_marked_block(text: str, start: str, end: str, body: str) -> str:
    if text.count(start) != 1 or text.count(end) != 1:
        raise SyncError(f"README must contain exactly one marker pair: {start} / {end}")
    before, remainder = text.split(start, 1)
    _old, after = remainder.split(end, 1)
    return f"{before}{start}\n{body}\n{end}{after}"


def generated_inventory(items: list[str]) -> str:
    return ", ".join(f"`{item}`" for item in items) + "。"


def add_expected(
    expected: dict[Path, bytes],
    relative: Path,
    data: bytes,
) -> None:
    if relative in expected:
        raise SyncError(f"manifest destination is duplicated: {relative.as_posix()}")
    expected[relative] = data


def build_candidate(
    repo_root: Path,
    codex_home: Path,
    manifest: dict[str, object],
    candidate_root: Path,
) -> tuple[dict[Path, bytes], list[Path], set[Path]]:
    patterns = [str(value) for value in manifest["exclude_globs"]]
    managed_roots: list[Path] = []
    managed_files: set[Path] = set()

    for index, entry in enumerate(manifest["global_files"]):
        if not isinstance(entry, dict):
            raise SyncError(f"global_files[{index}] must be an object")
        source = normalized_relative(entry.get("source", ""), f"global_files[{index}].source")
        destination = normalized_relative(
            entry.get("destination", ""), f"global_files[{index}].destination"
        )
        copy_candidate_file(codex_home / source, candidate_root / destination)
        managed_files.add(destination)

    skills: list[str] = []
    for index, value in enumerate(manifest["skills"]):
        if not isinstance(value, str) or not SKILL_NAME.fullmatch(value):
            raise SyncError(f"skills[{index}] has an invalid public skill name")
        if value.startswith(".") or value in skills:
            raise SyncError(f"skills[{index}] is duplicated or private")
        skills.append(value)
        destination = Path("skills") / value
        copy_candidate_tree(
            codex_home / "skills" / value,
            candidate_root / destination,
            patterns,
        )
        managed_roots.append(destination)
    if skills != sorted(skills):
        raise SyncError("public skills must be sorted")

    mcp_names: list[str] = []
    for index, entry in enumerate(manifest["mcp_packages"]):
        if not isinstance(entry, dict):
            raise SyncError(f"mcp_packages[{index}] must be an object")
        name = entry.get("name")
        if not isinstance(name, str) or not SKILL_NAME.fullmatch(name) or name in mcp_names:
            raise SyncError(f"mcp_packages[{index}].name is invalid or duplicated")
        mcp_names.append(name)
        source_root = normalized_relative(
            entry.get("source", ""), f"mcp_packages[{index}].source"
        )
        destination_root = normalized_relative(
            entry.get("destination", ""), f"mcp_packages[{index}].destination"
        )
        files = entry.get("files")
        if not isinstance(files, list) or not files:
            raise SyncError(f"mcp_packages[{index}].files must be a non-empty list")
        for file_index, value in enumerate(files):
            relative = normalized_relative(
                value, f"mcp_packages[{index}].files[{file_index}]"
            )
            destination = destination_root / relative
            copy_candidate_file(
                codex_home / source_root / relative,
                candidate_root / destination,
            )
            managed_files.add(destination)
    if mcp_names != sorted(mcp_names):
        raise SyncError("public MCP packages must be sorted")

    readme_path = repo_root / "README.md"
    if not readme_path.is_file():
        raise SyncError("README.md is missing")
    readme = readme_path.read_text(encoding="utf-8")
    readme = replace_marked_block(
        readme,
        SKILLS_START,
        SKILLS_END,
        generated_inventory(skills),
    )
    readme = replace_marked_block(
        readme,
        MCP_START,
        MCP_END,
        generated_inventory(mcp_names),
    )
    (candidate_root / "README.md").write_text(readme, encoding="utf-8", newline="\n")
    managed_files.add(Path("README.md"))

    expected: dict[Path, bytes] = {}
    for path in sorted(candidate_root.rglob("*")):
        if path.is_symlink():
            raise SyncError(f"symbolic links are not allowed: {path}")
        if path.is_file():
            add_expected(expected, path.relative_to(candidate_root), path.read_bytes())
    return expected, managed_roots, managed_files


def scan_candidate(
    expected: dict[Path, bytes],
    denylist_path: Path,
) -> None:
    denylist = privacy_scan.load_denylist(denylist_path)
    findings: list[privacy_scan.Finding] = []
    for path, data in expected.items():
        findings.extend(privacy_scan.path_findings(path))
        text = privacy_scan.decode_text(path, data)
        if text is not None:
            findings.extend(privacy_scan.scan_file(path, text, denylist))
    unique = sorted(set(findings), key=lambda item: (str(item.path), item.line, item.rule))
    if unique:
        print(f"sync_public_snapshot: BLOCKED ({len(unique)} privacy finding(s))")
        for finding in unique:
            print(f"- {finding.rule}: {finding.path.as_posix()}:{finding.line}")
        raise SyncError("candidate tree did not pass privacy checks")


def managed_current_files(
    repo_root: Path,
    managed_roots: list[Path],
    managed_files: set[Path],
    patterns: list[str],
) -> set[Path]:
    current = {path for path in managed_files if (repo_root / path).is_file()}
    for relative_root in managed_roots:
        root = repo_root / relative_root
        if root.is_symlink():
            raise SyncError(f"managed destination cannot be a symbolic link: {relative_root}")
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_symlink():
                raise SyncError(f"managed destination contains a symbolic link: {path}")
            relative_to_root = path.relative_to(root)
            if path.is_file() and not is_excluded(relative_to_root, patterns):
                current.add(path.relative_to(repo_root))
    return current


def comparison_bytes(data: bytes) -> bytes:
    if b"\0" in data:
        return data
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return data
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def changes_for(
    repo_root: Path,
    expected: dict[Path, bytes],
    managed_roots: list[Path],
    managed_files: set[Path],
    patterns: list[str],
) -> list[tuple[str, Path]]:
    current = managed_current_files(repo_root, managed_roots, managed_files, patterns)
    changes: list[tuple[str, Path]] = []
    for path in sorted(set(expected) | current):
        destination = repo_root / path
        if path not in expected:
            changes.append(("D", path))
        elif path not in current:
            changes.append(("A", path))
        elif comparison_bytes(destination.read_bytes()) != comparison_bytes(expected[path]):
            changes.append(("M", path))
    return changes


def require_clean_repo(repo_root: Path) -> None:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "status", "--porcelain", "--untracked-files=all"],
        capture_output=True,
        check=True,
    )
    if result.stdout:
        raise SyncError("--apply requires a clean Git worktree")


def canonical_remote(value: str) -> str:
    return re.sub(r"\.git$", "", value.strip().rstrip("/"), flags=re.IGNORECASE).casefold()


def require_expected_origin(repo_root: Path, expected: str) -> None:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "remote", "get-url", "origin"],
        capture_output=True,
        check=True,
        text=True,
    )
    if canonical_remote(result.stdout) != canonical_remote(expected):
        raise SyncError("origin does not match the public repository in the manifest")


def apply_changes(
    repo_root: Path,
    expected: dict[Path, bytes],
    changes: list[tuple[str, Path]],
    managed_roots: list[Path],
) -> None:
    snapshots: dict[Path, bytes | None] = {}
    for _status, relative in changes:
        destination = repo_root / relative
        snapshots[relative] = destination.read_bytes() if destination.is_file() else None
    try:
        for status, relative in changes:
            destination = repo_root / relative
            if status == "D":
                destination.unlink()
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_name(destination.name + ".public-sync.tmp")
            temporary.write_bytes(expected[relative])
            os.replace(temporary, destination)
        for relative_root in managed_roots:
            root = repo_root / relative_root
            if root.exists():
                for path in sorted(root.rglob("*"), reverse=True):
                    if path.is_dir() and not any(path.iterdir()):
                        path.rmdir()
    except Exception:
        for relative, data in snapshots.items():
            destination = repo_root / relative
            if data is None:
                if destination.is_file():
                    destination.unlink()
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(data)
        raise


def resolve_codex_home(value: Path | None) -> Path:
    if value is not None:
        return value.expanduser().resolve()
    configured = os.environ.get("CODEX_HOME")
    return Path(configured).expanduser().resolve() if configured else Path.home() / ".codex"


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.expanduser().resolve()
    codex_home = resolve_codex_home(args.codex_home)
    manifest_path = (args.manifest or repo_root / DEFAULT_MANIFEST.name).expanduser().resolve()
    denylist_path = (
        args.denylist.expanduser().resolve()
        if args.denylist
        else privacy_scan.default_denylist(repo_root)
    )
    if denylist_path is None or not denylist_path.is_file():
        print("sync_public_snapshot: ERROR (private denylist is required)")
        return 2
    try:
        if args.apply:
            require_clean_repo(repo_root)
        manifest = load_manifest(manifest_path)
        require_expected_origin(repo_root, str(manifest["repository"]))
        patterns = [str(value) for value in manifest["exclude_globs"]]
        with tempfile.TemporaryDirectory(prefix="codex-public-sync-") as temp:
            expected, managed_roots, managed_files = build_candidate(
                repo_root,
                codex_home,
                manifest,
                Path(temp),
            )
            scan_candidate(expected, denylist_path)
            changes = changes_for(
                repo_root,
                expected,
                managed_roots,
                managed_files,
                patterns,
            )
            if args.check:
                if changes:
                    print(f"sync_public_snapshot: OUT OF DATE ({len(changes)} change(s))")
                    for status, path in changes:
                        print(f"- {status} {path.as_posix()}")
                    return 1
                print("sync_public_snapshot: PASS (public snapshot is current)")
                return 0
            if args.apply:
                apply_changes(repo_root, expected, changes, managed_roots)
                print(f"sync_public_snapshot: APPLIED ({len(changes)} change(s))")
            else:
                print(f"sync_public_snapshot: DRY RUN ({len(changes)} change(s))")
            for status, path in changes:
                print(f"- {status} {path.as_posix()}")
            return 0
    except (OSError, subprocess.CalledProcessError, SyncError) as error:
        print(f"sync_public_snapshot: ERROR ({error})")
        return 2


if __name__ == "__main__":
    sys.exit(main())
