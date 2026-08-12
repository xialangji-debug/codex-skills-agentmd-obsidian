#!/usr/bin/env python3

from __future__ import annotations

import argparse
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("fix_memory.py")
SPEC = importlib.util.spec_from_file_location("fix_memory", MODULE_PATH)
assert SPEC and SPEC.loader
fix_memory = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fix_memory)


def context(target_id: str, branch: str, verification: str, updated: str) -> dict:
    return {
        "target_id": target_id,
        "project_key": "sample-project",
        "repo_id": "a1b2c3d4e5f6",
        "branch": branch,
        "version": "1.0.0",
        "variant_id": "abcdef123456",
        "bug_ids": ["1001"],
        "implementation": "applied",
        "verification": verification,
        "zentao": "active",
        "relation": "applied",
        "commit": "abc1234",
        "evidence": "synthetic evidence",
        "symptom_fingerprint": "sample symptom",
        "updated_at": updated,
    }


class FixMemoryTests(unittest.TestCase):
    def test_round_trip_managed_state(self) -> None:
        state = fix_memory.empty_state("FP-TEST")
        state["targets"] = [context("target-a", "main", "build_passed", "2026-08-01T10:00:00+08:00")]
        text = fix_memory.note_template("Sample fix", "FP-TEST")
        result = fix_memory.finalize_note(text, state)
        loaded = fix_memory.decode_state(result)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["fix_id"], "FP-TEST")
        self.assertEqual(loaded["reference_target"], "target-a")
        self.assertNotIn("C:\\Users", result)

    def test_stronger_reference_beats_newer_weak_target(self) -> None:
        state = fix_memory.empty_state("FP-TEST")
        state["targets"] = [
            context("target-old", "release", "device_verified", "2026-08-01T10:00:00+08:00"),
            context("target-new", "next", "build_passed", "2026-08-03T10:00:00+08:00"),
        ]
        fix_memory.choose_reference(state)
        self.assertEqual(state["reference_target"], "target-old")

    def test_reactivation_falls_back_to_next_reference(self) -> None:
        state = fix_memory.empty_state("FP-TEST")
        failed = context("target-new", "next", "qa_verified", "2026-08-03T10:00:00+08:00")
        fallback = context("target-old", "release", "device_verified", "2026-08-01T10:00:00+08:00")
        state["targets"] = [failed, fallback]
        fix_memory.choose_reference(state)
        self.assertEqual(state["reference_target"], "target-new")
        fix_memory.apply_event_to_target(
            failed,
            {"event": "reactivated_same", "observed_at": "2026-08-04T10:00:00+08:00", "evidence": "reopened"},
        )
        fix_memory.choose_reference(state)
        self.assertEqual(state["reference_target"], "target-old")
        self.assertEqual(state["last_reference_target"], "target-new")

    def test_apply_events_requires_exact_target_and_bug(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            note = root / "sample.md"
            state = fix_memory.empty_state("FP-TEST")
            state["targets"] = [context("target-a", "main", "build_passed", "2026-08-01T10:00:00+08:00")]
            note.write_text(fix_memory.finalize_note(fix_memory.note_template("Sample", "FP-TEST"), state), encoding="utf-8")
            events = root / "events.json"
            events.write_text(
                json.dumps(
                    {
                        "events": [
                            {"event": "zentao_closed", "target_id": "target-wrong", "bug_id": "1001"},
                            {"event": "zentao_closed", "target_id": "target-a", "bug_id": "1001"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            args = argparse.Namespace(root=str(root), events=events, write=True)
            fix_memory.command_apply_events(args)
            loaded = fix_memory.decode_state(note.read_text(encoding="utf-8"))
            self.assertEqual(loaded["targets"][0]["verification"], "qa_verified")
            self.assertEqual(loaded["targets"][0]["zentao"], "closed")

    def test_variant_reactivation_does_not_mutate_target(self) -> None:
        target = context("target-a", "main", "qa_verified", "2026-08-01T10:00:00+08:00")
        changed = fix_memory.apply_event_to_target(target, {"event": "reactivated_variant"})
        self.assertFalse(changed)
        self.assertEqual(target["verification"], "qa_verified")

    def test_knowledge_sections_are_filled_without_touching_other_sections(self) -> None:
        text = fix_memory.note_template("Sample", "FP-TEST")
        args = argparse.Namespace(
            keyword=["refresh"],
            scope=["sample firmware"],
            symptoms="screen does not refresh",
            root_cause="missing state notification",
            key_file=["ui/sample.c:refresh_view"],
            fix="emit the existing notification after state changes",
            verification_method="target build and device regression",
            caution=["do not affect the simulator variant"],
        )
        result = fix_memory.update_knowledge_sections(text, args)
        self.assertIn("- missing state notification", result)
        self.assertIn("- ui/sample.c:refresh_view", result)
        self.assertIn("## 注意事项", result)

    def test_fix_notes_excludes_directory_index(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "index.md").write_text("# Index\n", encoding="utf-8")
            note = root / "sample.md"
            note.write_text("# Sample\n", encoding="utf-8")
            self.assertEqual(fix_memory.fix_notes(root), [note])


if __name__ == "__main__":
    unittest.main()
