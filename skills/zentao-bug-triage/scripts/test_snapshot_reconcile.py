#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("zentao_snapshot_reconcile.py")
SPEC = importlib.util.spec_from_file_location("zentao_snapshot_reconcile", MODULE_PATH)
assert SPEC and SPEC.loader
reconcile_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reconcile_module)


def bug(bug_id: str, status: str, activations: int = 0, actual: str = "same symptom") -> dict:
    return {
        "id": bug_id,
        "title": "Synthetic screen refresh issue",
        "status": status,
        "activationCount": activations,
        "actual": actual,
        "expected": "screen refreshes",
        "lastActivation": {"note": actual} if activations else None,
    }


def payload(repo: Path, bugs: list[dict]) -> dict:
    return {
        "context": {
            "repo": str(repo),
            "branch": "sample-main",
            "deviceVer": "SAMPLE_1.0",
            "productName": "Sample Product",
        },
        "projectResolution": {"productName": "Sample Product"},
        "args": {"ids": [], "bugStatus": "active"},
        "bugs": bugs,
    }


class SnapshotReconcileTests(unittest.TestCase):
    def write_snapshot(self, root: Path, name: str, data: dict) -> Path:
        directory = root / name
        directory.mkdir(parents=True)
        path = directory / "bugs.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        (directory / "chat-summary.md").write_text("# Summary\n", encoding="utf-8")
        return path

    def test_first_fetch_creates_baseline_without_events(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo = root / "repo"
            repo.mkdir()
            snapshot = self.write_snapshot(root, "first", payload(repo, [bug("1001", "active")]))
            state_root = root / "state"
            result = reconcile_module.reconcile(snapshot, state_root=state_root, write_memory=False)
            self.assertTrue(result["baseline"])
            self.assertEqual(result["events"], [])

    def test_missing_active_bug_is_planned_for_detail_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo = root / "repo"
            repo.mkdir()
            state_root = root / "state"
            first = self.write_snapshot(root, "first", payload(repo, [bug("1001", "active")]))
            reconcile_module.reconcile(first, state_root=state_root, write_memory=False)
            second = self.write_snapshot(root, "second", payload(repo, []))
            plan = reconcile_module.prepare_refresh(second, state_root)
            self.assertEqual(plan["refresh_ids"], ["1001"])

    def test_resolved_and_closed_transitions(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo = root / "repo"
            repo.mkdir()
            state_root = root / "state"
            first = self.write_snapshot(root, "first", payload(repo, [bug("1001", "active")]))
            reconcile_module.reconcile(first, state_root=state_root, write_memory=False)
            second = self.write_snapshot(root, "second", payload(repo, []))
            refresh_resolved = self.write_snapshot(root, "refresh-resolved", payload(repo, [bug("1001", "已解决")]))
            result = reconcile_module.reconcile(second, [refresh_resolved], state_root, write_memory=False)
            self.assertEqual(result["events"][0]["event"], "zentao_resolved")
            third = self.write_snapshot(root, "third", payload(repo, []))
            refresh_closed = self.write_snapshot(root, "refresh-closed", payload(repo, [bug("1001", "已关闭")]))
            result = reconcile_module.reconcile(third, [refresh_closed], state_root, write_memory=False)
            self.assertEqual(result["events"][0]["event"], "zentao_closed")

    def test_reactivation_distinguishes_same_and_variant_symptoms(self) -> None:
        previous = reconcile_module.compact_bug(bug("1001", "resolved", 0, "same symptom"))
        self.assertEqual(reconcile_module.transition(previous, bug("1001", "active", 1, "same symptom")), "reactivated_same")
        self.assertEqual(
            reconcile_module.transition(previous, {
                **bug("1001", "active", 1, "different protocol failure"),
                "title": "Completely different network issue",
            }),
            "reactivated_variant",
        )

    def test_report_uses_combined_bug_id_and_title(self) -> None:
        report = reconcile_module.render_report(
            [{
                "event": "zentao_resolved",
                "bug_id": "1001",
                "title": "Synthetic screen refresh issue",
                "previous_status": "active",
                "current_status": "resolved",
            }],
            baseline=False,
            refresh_ids=[],
        )
        self.assertIn("| Bug（ID + 标题） |", report)
        self.assertIn("| 1001 Synthetic screen refresh issue |", report)
        self.assertNotIn("| 1001 |", report)

    def test_bug_display_label_has_explicit_missing_title(self) -> None:
        self.assertEqual(reconcile_module.bug_display_label("#1002", ""), "1002 标题未获取")

    def test_exact_context_separates_branches(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo = root / "repo"
            repo.mkdir()
            one = payload(repo, [])
            two = payload(repo, [])
            two["context"]["branch"] = "sample-release"
            self.assertNotEqual(
                reconcile_module.context_from_payload(one)["target_id"],
                reconcile_module.context_from_payload(two)["target_id"],
            )


if __name__ == "__main__":
    unittest.main()
