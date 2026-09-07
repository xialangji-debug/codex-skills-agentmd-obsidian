#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import zentao_bug_fast_fetch as fast_fetch


LIVE = {
    "repo": "C:/repo",
    "repoName": "repo",
    "branch": "main",
    "commit": "abc1234",
    "deviceVer": "DEVICE_1",
}


class SnapshotCommandTests(unittest.TestCase):
    @mock.patch.object(fast_fetch.shutil, "which", return_value="node")
    def test_default_is_list_only(self, _which: mock.Mock) -> None:
        command = fast_fetch.snapshot_command(Path("C:/repo"), LIVE, "active", 80, 4)
        self.assertIn("--detail-limit", command)
        self.assertIn("--no-download-attachments", command)
        self.assertIn("--no-work-md", command)
        self.assertIn("--no-memory-link", command)
        self.assertNotIn("--download-attachments", command)

    @mock.patch.object(fast_fetch.shutil, "which", return_value="node")
    def test_deep_all_downloads_attachments(self, _which: mock.Mock) -> None:
        command = fast_fetch.snapshot_command(
            Path("C:/repo"), LIVE, "active", 80, 4, deep_all=True
        )
        self.assertIn("--download-attachments", command)
        self.assertNotIn("--detail-limit", command)

    @mock.patch.object(fast_fetch.shutil, "which", return_value="node")
    def test_selected_ids_are_deep_fetched(self, _which: mock.Mock) -> None:
        command = fast_fetch.snapshot_command(
            Path("C:/repo"), LIVE, "active", 80, 4, bug_ids="4045"
        )
        self.assertEqual(command[command.index("--ids") + 1], "4045")
        self.assertIn("--download-attachments", command)


class SnapshotValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name) / "repo"
        self.repo.mkdir()
        self.snapshot = Path(self.temp.name) / "bugs.json"
        payload = {
            "context": {
                **LIVE,
                "repo": str(self.repo),
                "productName": "C10",
            },
            "projectResolution": {"mode": "project", "productName": "C10"},
            "bugs": [
                {
                    "id": "4045",
                    "status": "active",
                    "detailFetched": False,
                    "attachmentLinks": [{"href": "a.zip", "text": "a.zip"}],
                }
            ],
        }
        self.snapshot.write_text(json.dumps(payload), encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    @mock.patch.object(fast_fetch, "live_context")
    def test_list_snapshot_does_not_require_details(self, live_context: mock.Mock) -> None:
        live_context.return_value = {**LIVE, "repo": str(self.repo)}
        _, errors, missing, _ = fast_fetch.validate_snapshot(
            self.snapshot, self.repo, "active", require_details=False
        )
        self.assertEqual(errors, [])
        self.assertEqual(missing, {})

    @mock.patch.object(fast_fetch, "live_context")
    def test_deep_snapshot_requires_details(self, live_context: mock.Mock) -> None:
        live_context.return_value = {**LIVE, "repo": str(self.repo)}
        _, errors, missing, _ = fast_fetch.validate_snapshot(
            self.snapshot, self.repo, "active", require_details=True
        )
        self.assertIn("bug 4045 detail was not fetched", errors)
        self.assertIn("4045", missing)


if __name__ == "__main__":
    unittest.main()
