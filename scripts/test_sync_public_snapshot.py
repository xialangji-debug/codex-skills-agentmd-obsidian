#!/usr/bin/env python3
"""Integration tests for the fail-closed public snapshot sync."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("sync_public_snapshot.py")


class PublicSnapshotSyncTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="public-sync-test-")
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repo"
        self.codex_home = self.root / "codex-home"
        self.denylist = self.root / "denylist.txt"
        self.repo.mkdir()
        (self.codex_home / "skills" / "public-skill").mkdir(parents=True)
        (self.codex_home / "AGENTS.md").write_text("# Public rules\n", encoding="utf-8")
        (self.codex_home / "skills" / "public-skill" / "SKILL.md").write_text(
            "# Current public skill\n", encoding="utf-8"
        )
        (self.repo / "skills" / "public-skill").mkdir(parents=True)
        (self.repo / "skills" / "public-skill" / "SKILL.md").write_text(
            "# Old public skill\n", encoding="utf-8"
        )
        (self.repo / "skills" / "public-skill" / "stale.txt").write_text(
            "stale\n", encoding="utf-8"
        )
        (self.repo / "skills" / "private-skill").mkdir(parents=True)
        (self.repo / "skills" / "private-skill" / "keep.txt").write_text(
            "keep\n", encoding="utf-8"
        )
        (self.repo / "AGENTS.md").write_text("# Old rules\n", encoding="utf-8")
        (self.repo / "README.md").write_text(
            "\n".join(
                [
                    "# Demo",
                    "<!-- BEGIN PUBLIC SKILLS -->",
                    "old",
                    "<!-- END PUBLIC SKILLS -->",
                    "<!-- BEGIN PUBLIC MCP -->",
                    "old",
                    "<!-- END PUBLIC MCP -->",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        self.manifest = self.repo / "public-sync-manifest.json"
        self.manifest.write_text(
            json.dumps(
                {
                    "version": 1,
                    "repository": "https://github.com/example/public-sync-demo.git",
                    "global_files": [
                        {"source": "AGENTS.md", "destination": "AGENTS.md"}
                    ],
                    "skills": ["public-skill"],
                    "mcp_packages": [],
                    "exclude_globs": ["__pycache__/**", "*.pyc"],
                }
            ),
            encoding="utf-8",
        )
        self.denylist.write_text("", encoding="utf-8")
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.repo)], check=True)
        subprocess.run(
            ["git", "-C", str(self.repo), "config", "user.name", "Test"], check=True
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(self.repo),
                "config",
                "user.email",
                "test@example.invalid",
            ],
            check=True,
        )
        subprocess.run(["git", "-C", str(self.repo), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(self.repo), "commit", "-q", "-m", "baseline"],
            check=True,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(self.repo),
                "remote",
                "add",
                "origin",
                "https://github.com/example/public-sync-demo.git",
            ],
            check=True,
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_sync(self, *mode: str, denylist: Path | None = None) -> subprocess.CompletedProcess[str]:
        command = [
            sys.executable,
            "-X",
            "utf8",
            str(SCRIPT),
            "--repo-root",
            str(self.repo),
            "--codex-home",
            str(self.codex_home),
            "--manifest",
            str(self.manifest),
        ]
        if denylist is not None:
            command.extend(["--denylist", str(denylist)])
        command.extend(mode)
        return subprocess.run(command, capture_output=True, text=True)

    def test_dry_run_does_not_modify_repository(self) -> None:
        result = self.run_sync(denylist=self.denylist)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("DRY RUN", result.stdout)
        self.assertEqual(
            (self.repo / "skills" / "public-skill" / "SKILL.md").read_text(
                encoding="utf-8"
            ),
            "# Old public skill\n",
        )

    def test_apply_mirrors_only_allowlisted_content(self) -> None:
        result = self.run_sync("--apply", denylist=self.denylist)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("APPLIED", result.stdout)
        self.assertFalse(self.repo.joinpath("skills/public-skill/stale.txt").exists())
        self.assertTrue(self.repo.joinpath("skills/private-skill/keep.txt").exists())
        self.assertEqual(
            self.repo.joinpath("skills/public-skill/SKILL.md").read_text(encoding="utf-8"),
            "# Current public skill\n",
        )
        check = self.run_sync("--check", denylist=self.denylist)
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)

    def test_private_candidate_is_blocked_before_apply(self) -> None:
        original = self.repo.joinpath("skills/public-skill/SKILL.md").read_bytes()
        self.codex_home.joinpath("skills/public-skill/SKILL.md").write_text(
            "C:" + r"\Users\private-user\project",
            encoding="utf-8",
        )
        result = self.run_sync("--apply", denylist=self.denylist)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("literal-windows-user-path", result.stdout)
        self.assertNotIn("private-user", result.stdout)
        self.assertEqual(
            self.repo.joinpath("skills/public-skill/SKILL.md").read_bytes(), original
        )

    def test_check_ignores_line_ending_only_difference(self) -> None:
        result = self.run_sync("--apply", denylist=self.denylist)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        skill = self.repo / "skills" / "public-skill" / "SKILL.md"
        normalized = skill.read_bytes().replace(b"\r\n", b"\n")
        skill.write_bytes(normalized)
        check = self.run_sync("--check", denylist=self.denylist)
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)

    def test_check_ignores_excluded_local_cache(self) -> None:
        result = self.run_sync("--apply", denylist=self.denylist)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        cache = self.repo / "skills" / "public-skill" / "__pycache__" / "local.pyc"
        cache.parent.mkdir()
        cache.write_bytes(b"local cache")
        check = self.run_sync("--check", denylist=self.denylist)
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)

    def test_missing_private_denylist_fails_closed(self) -> None:
        missing = self.root / "missing-denylist.txt"
        result = self.run_sync(denylist=missing)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("private denylist is required", result.stdout)

    def test_manifest_rejects_parent_path(self) -> None:
        content = json.loads(self.manifest.read_text(encoding="utf-8"))
        content["global_files"][0]["source"] = "../AGENTS.md"
        self.manifest.write_text(json.dumps(content), encoding="utf-8")
        result = self.run_sync(denylist=self.denylist)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("must stay inside", result.stdout)

    def test_manifest_rejects_windows_absolute_path(self) -> None:
        content = json.loads(self.manifest.read_text(encoding="utf-8"))
        content["global_files"][0]["source"] = "C:/private/AGENTS.md"
        self.manifest.write_text(json.dumps(content), encoding="utf-8")
        result = self.run_sync(denylist=self.denylist)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("must stay inside", result.stdout)

    def test_apply_rejects_dirty_repository(self) -> None:
        self.repo.joinpath("local-only.txt").write_text("dirty", encoding="utf-8")
        result = self.run_sync("--apply", denylist=self.denylist)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("requires a clean Git worktree", result.stdout)

    def test_wrong_origin_is_rejected(self) -> None:
        subprocess.run(
            [
                "git",
                "-C",
                str(self.repo),
                "remote",
                "set-url",
                "origin",
                "https://github.com/example/wrong-repository.git",
            ],
            check=True,
        )
        result = self.run_sync(denylist=self.denylist)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("origin does not match", result.stdout)


if __name__ == "__main__":
    unittest.main()
