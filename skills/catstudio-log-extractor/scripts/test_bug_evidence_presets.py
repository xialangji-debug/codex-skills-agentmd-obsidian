#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

import extract_bug_evidence


class PresetTests(unittest.TestCase):
    def test_expected_presets_and_evidence_types(self) -> None:
        presets = extract_bug_evidence.load_presets()
        self.assertEqual({"3996", "4003", "4045", "4046"}, set(presets))
        self.assertEqual("video", presets["3996"]["evidence"])
        self.assertTrue(all(presets[bug_id]["keywords"] for bug_id in presets))

    def test_list_presets_without_attachments(self) -> None:
        script = Path(extract_bug_evidence.__file__)
        result = subprocess.run(
            [sys.executable, "-X", "utf8", str(script), "--list-presets"],
            capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("3996:", result.stdout)
        self.assertIn("4046:", result.stdout)

    def test_unknown_preset_fails_before_attachment_lookup(self) -> None:
        script = Path(extract_bug_evidence.__file__)
        result = subprocess.run(
            [sys.executable, "-X", "utf8", str(script), "--bugs", "9999"],
            capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(2, result.returncode)
        self.assertIn("unknown preset", result.stderr)


if __name__ == "__main__":
    unittest.main()
