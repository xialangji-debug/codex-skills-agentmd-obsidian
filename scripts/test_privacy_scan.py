#!/usr/bin/env python3
"""Unit tests for privacy_scan without invoking Git."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import privacy_scan


class PrivacyScanTests(unittest.TestCase):
    def test_literal_user_path_is_blocked(self) -> None:
        value = "C:" + r"\Users\actual-user\project"
        findings = privacy_scan.scan_file(Path("sample.md"), value, [])
        self.assertIn("literal-windows-user-path", {item.rule for item in findings})

    def test_userprofile_path_is_allowed(self) -> None:
        findings = privacy_scan.scan_file(Path("sample.md"), r"%USERPROFILE%\.codex\skills", [])
        self.assertEqual(findings, [])

    def test_private_service_port_is_blocked(self) -> None:
        value = "https://" + "private.example.invalid:9443/path"
        findings = privacy_scan.scan_file(Path("sample.md"), value, [])
        self.assertIn("external-service-url-with-port", {item.rule for item in findings})

    def test_private_ip_is_blocked(self) -> None:
        value = "service at " + "192." + "168.12.34"
        findings = privacy_scan.scan_file(Path("sample.md"), value, [])
        self.assertIn("private-ip-address", {item.rule for item in findings})

    def test_localhost_is_allowed(self) -> None:
        findings = privacy_scan.scan_file(Path("sample.md"), "http://127.0.0.1:7897", [])
        self.assertEqual(findings, [])

    def test_official_vendor_url_is_allowed(self) -> None:
        findings = privacy_scan.scan_file(
            Path("Project.uvprojx"), "https://www.keil.com/pack/", []
        )
        self.assertEqual(findings, [])

    def test_unknown_external_url_is_blocked(self) -> None:
        findings = privacy_scan.scan_file(
            Path("sample.md"), "https://" + "service.unknown.invalid/path", []
        )
        self.assertIn("unapproved-url-host", {item.rule for item in findings})

    def test_denylist_does_not_echo_value(self) -> None:
        private_value = "confidential-customer-token"
        findings = privacy_scan.scan_file(
            Path("sample.md"), f"value={private_value}", [("customer-a", private_value)]
        )
        self.assertEqual(findings[0].rule, "denylist:customer-a")
        self.assertNotIn(private_value, findings[0].rule)

    def test_project_map_requires_synthetic_marker(self) -> None:
        findings = privacy_scan.scan_file(Path("project-map.md"), "# Real map", [])
        self.assertIn("bundled-project-map-is-not-synthetic", {item.rule for item in findings})

    def test_binary_reader_skips_nul(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "data.txt"
            path.write_bytes(b"a\0b")
            self.assertIsNone(privacy_scan.read_text(path))

    def test_firmware_artifact_name_is_blocked(self) -> None:
        findings = privacy_scan.path_findings(Path("release/demo.hex"))
        self.assertIn("forbidden-artifact-file", {item.rule for item in findings})

    def test_keil_user_config_is_blocked(self) -> None:
        findings = privacy_scan.path_findings(Path("Project.uvguix.sample-user"))
        self.assertIn(
            "private-or-user-configuration-file", {item.rule for item in findings}
        )

    def test_generated_directory_is_blocked(self) -> None:
        findings = privacy_scan.path_findings(Path("MDK-ARM/Objects/demo.o"))
        self.assertIn("generated-build-directory", {item.rule for item in findings})

    def test_staged_scan_reads_index_not_worktree(self) -> None:
        import subprocess

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True)
            sample = root / "sample.md"
            sample.write_text("safe", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "sample.md"], check=True)
            sample.write_text("C:" + r"\Users\worktree-only\project", encoding="utf-8")
            targets = privacy_scan.staged_targets(root)
            self.assertEqual(targets[0].data, b"safe")

    def test_history_scan_reads_reachable_blob(self) -> None:
        import subprocess

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True)
            subprocess.run(["git", "-C", str(root), "config", "user.name", "Test"], check=True)
            subprocess.run(
                ["git", "-C", str(root), "config", "user.email", "test@example.invalid"],
                check=True,
            )
            (root / "sample.md").write_text("history", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "sample.md"], check=True)
            subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", "base"], check=True)
            targets = privacy_scan.history_targets(root)
            self.assertEqual(targets[0].path, Path("sample.md"))
            self.assertEqual(targets[0].data, b"history")
            self.assertEqual(len(targets[0].revision), 12)


if __name__ == "__main__":
    unittest.main()
