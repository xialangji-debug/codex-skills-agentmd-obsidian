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
    def write_registry(self, root: Path) -> Path:
        registry = root / "active-projects.json"
        registry.write_text(
            json.dumps(
                {
                    "projects": [
                        {
                            "project_key": "esp32_c5",
                            "family": "esp32",
                            "path": str(root / "esp32"),
                            "enabled": True,
                        },
                        {
                            "project_key": "watch",
                            "family": "asr360x",
                            "path": str(root / "watch"),
                            "enabled": True,
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )
        return registry

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

    def test_literal_paths_survive_new_and_updated_sections(self) -> None:
        text = fix_memory.note_template("Sample", "FP-TEST")
        values = [r"C:\BuildRoots\example\固件\ui.c", r"pattern \1 \g<1> \n \t"]
        for heading in ["关键文件和函数", "Extra evidence"]:
            with self.subTest(heading=heading):
                result = fix_memory.set_section(text, heading, values)
                updated = fix_memory.set_section(result, heading, values)
                self.assertEqual(result, updated)
                for value in values:
                    self.assertIn("- " + value + "\n", updated)
                self.assertEqual(fix_memory.frontmatter_value(updated, "fix_id"), "FP-TEST")

    def test_repeated_caution_arguments_preserve_literal_text(self) -> None:
        values = [r"C:\BuildRoots\example\固件\ui.c", r"Literal \1 and \g<1>"]
        args = fix_memory.build_parser().parse_args([
            "upsert", "--caution", values[0], "--caution", values[1],
        ])
        result = fix_memory.update_knowledge_sections(fix_memory.note_template("Sample", "FP-TEST"), args)
        for value in values:
            self.assertIn("- " + value + "\n", result)
        self.assertNotIn("- ['", result)

    def test_omitted_caution_preserves_existing_section(self) -> None:
        note = fix_memory.set_section(
            fix_memory.note_template("Sample", "FP-TEST"), "注意事项", ["Keep existing caution"],
        )
        args = fix_memory.build_parser().parse_args(["upsert"])
        self.assertEqual(fix_memory.update_knowledge_sections(note, args), note)

    def test_literal_frontmatter_and_target_state_round_trip(self) -> None:
        text = fix_memory.note_template("Sample", "FP-TEST")
        value = r"C:\BuildRoots\example\1"
        text = fix_memory.set_frontmatter(text, "source", value)
        text = fix_memory.set_frontmatter(text, "source", value)
        self.assertEqual(fix_memory.frontmatter_value(text, "source"), value)
        state = fix_memory.empty_state("FP-TEST")
        target = context("target-a", r"branch\1", "static_checked", "2026-09-07T10:00:00+08:00")
        target["evidence"] = r"C:\BuildRoots\example\report.md"
        state["targets"] = [target]
        text = fix_memory.replace_state_block(text, state)
        text = fix_memory.replace_state_block(text, state)
        self.assertEqual(fix_memory.decode_state(text)["targets"][0], target)
        self.assertIn(r"branch\1", text)

    def test_domain_template_and_frontmatter_round_trip(self) -> None:
        esp = fix_memory.note_template("ESP32 fix", "FP-ESP", "esp32")
        neutral = fix_memory.note_template("Tool fix", "FP-TOOL", "none")
        self.assertEqual(fix_memory.frontmatter_domains(esp), ["esp32"])
        self.assertEqual(fix_memory.frontmatter_domains(neutral), [])
        changed = fix_memory.set_frontmatter_domains(esp, "asr")
        self.assertEqual(fix_memory.frontmatter_domains(changed), ["asr"])

    def test_infer_domain_from_project_key_or_repo(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            registry = self.write_registry(root)
            domain, _ = fix_memory.infer_domain(str(root / "unknown"), "esp32_c5", registry)
            self.assertEqual(domain, "esp32")
            domain, _ = fix_memory.infer_domain(str(root / "watch"), "", registry)
            self.assertEqual(domain, "asr")

    def test_new_note_requires_explicit_or_inferred_domain(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            registry = self.write_registry(root)
            args = argparse.Namespace(
                root=str(root),
                note="",
                title="Unknown fix",
                slug="unknown-fix",
                repo=str(root / "unknown"),
                project_key="unknown",
                repo_id="",
                branch="main",
                version="1",
                variant="",
                variant_id="",
                bug=[],
                commit="",
                evidence="",
                symptom_fingerprint="",
                implementation="applied",
                verification="static_checked",
                zentao="unknown",
                relation="applied",
                domain="",
                active_projects=str(registry),
                write=False,
                keyword=[],
                scope=[],
                symptoms="symptom",
                root_cause="cause",
                key_file=[],
                fix="fix",
                verification_method="test",
                caution=[],
            )
            with self.assertRaises(SystemExit):
                fix_memory.command_upsert(args)

    def test_maintenance_without_private_project_registry(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            registry = root / "absent-projects.json"
            note = root / "sample.md"
            state = fix_memory.empty_state("FP-TEST")
            state["targets"] = [context("target-a", "main", "static_checked", "2026-09-07T10:00:00+08:00")]
            original = fix_memory.finalize_note(fix_memory.note_template("Sample", "FP-TEST", "none"), state)
            note.write_text(original, encoding="utf-8")
            args = argparse.Namespace(root=str(root), active_projects=str(registry), only_domain="all", write=False)
            self.assertEqual(0, fix_memory.command_validate(args))
            self.assertEqual(0, fix_memory.command_audit_domains(args))
            self.assertEqual(("", ""), fix_memory.infer_domain(str(root), "sample-project", registry))
            self.assertEqual(original, note.read_text(encoding="utf-8"))

    def test_validation_rejects_malformed_project_registry(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            registry = root / "active-projects.json"
            registry.write_text("{invalid", encoding="utf-8")
            (root / "sample.md").write_text(fix_memory.note_template("Sample", "FP-TEST", "none"), encoding="utf-8")
            args = argparse.Namespace(root=str(root), active_projects=str(registry))
            with self.assertRaises(json.JSONDecodeError):
                fix_memory.command_validate(args)

    def test_domain_audit_writes_only_selected_high_confidence_domain(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            registry = self.write_registry(root)
            esp_note = root / "esp32-c5-cache-fix.md"
            neutral_note = root / "powershell-helper.md"
            esp_note.write_text(
                fix_memory.note_template("ESP32-C5 cache fix", "FP-ESP", "asr"),
                encoding="utf-8",
            )
            neutral_note.write_text(
                fix_memory.note_template("PowerShell helper", "FP-PS", "asr"),
                encoding="utf-8",
            )
            args = argparse.Namespace(
                root=str(root), active_projects=str(registry), only_domain="esp32", write=True
            )
            fix_memory.command_audit_domains(args)
            self.assertEqual(fix_memory.frontmatter_domains(esp_note.read_text(encoding="utf-8")), ["esp32"])
            self.assertEqual(fix_memory.frontmatter_domains(neutral_note.read_text(encoding="utf-8")), ["asr"])


if __name__ == "__main__":
    unittest.main()
