#!/usr/bin/env python3
"""Offline target identity contract across onboarding, memory, and resolver."""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SKILLS = Path(__file__).resolve().parents[2]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


onboard = load("identity_onboard", Path(__file__).with_name("project_onboard.py"))
memory = load("identity_memory", SKILLS / "obsidian-fix-pattern-memory/scripts/fix_memory.py")
RESOLVER = SKILLS / "zentao-bug-resolver/scripts/zentao_bug_resolver.js"
NODE_PROBE = """
const resolver = require(process.argv[1]);
const ctx = { repo: process.argv[2], branch: process.argv[3] };
const defaults = resolver.parseArgs(['node', 'resolver']);
const product = resolver.resolveExpectedProduct(defaults, ctx);
process.stdout.write(JSON.stringify(resolver.memoryTargetContext(ctx, product)));
"""


class IdentityContractTests(unittest.TestCase):
    def target(self, root: Path, branch: str, version: str, product: str = "Product A") -> dict:
        # Match read_repo_info: Windows temporary paths can use 8.3 aliases.
        root = root.resolve()
        info = onboard.RepoInfo(root, root.name, branch, "abc1234", "clean", "SAMPLE", version, "ASR3602")
        mapping = onboard.Mapping(["Project A"], [product], "42", "7", "true", "", "confirmed")
        with patch.object(onboard, "match_mapping", return_value=mapping):
            variant = onboard.render_files(info)[".codex-project/variant.md"]
        variant_path = root / ".codex-project/variant.md"
        variant_path.parent.mkdir(exist_ok=True)
        variant_path.write_text(variant, encoding="utf-8")
        fields = onboard.variant_fields(variant)
        canonical = memory.target_context(argparse.Namespace(repo=str(root), branch=branch))
        result = subprocess.run(
            ["node", "-e", NODE_PROBE, str(RESOLVER), str(root), branch],
            capture_output=True, text=True, encoding="utf-8", check=True,
        )
        resolver = json.loads(result.stdout)
        for key in ("repo_id", "variant_id", "target_id"):
            self.assertEqual(fields[key], canonical[key], f"onboard {key}")
            self.assertEqual(resolver[key], canonical[key], f"resolver {key}")
        canonical["bug_ids"] = ["1001"]
        self.assertTrue(memory.event_target_match(canonical, {"target_id": resolver["target_id"], "bug_id": "1001"}))
        return canonical

    def test_uppercase_identity_matches_existing_canonical_memory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="identity-contract-") as temp:
            self.target(Path(temp), "TW18_LT52_APP_MAIN", "LT52_ASR3602_F001")

    def test_case_distinct_branches_and_versions_do_not_collide(self) -> None:
        with tempfile.TemporaryDirectory(prefix="identity-contract-") as temp:
            root = Path(temp)
            upper = self.target(root, "SAMPLE_MAIN", "MODEL_A_V1")
            lower_branch = self.target(root, "sample_main", "MODEL_A_V1")
            lower_version = self.target(root, "SAMPLE_MAIN", "model_a_v1")
            self.assertEqual(len({target["target_id"] for target in (upper, lower_branch, lower_version)}), 3)

    def test_canonical_whitespace_normalization_is_shared(self) -> None:
        with tempfile.TemporaryDirectory(prefix="identity-contract-") as temp:
            root = Path(temp) / "repo  with  spaces"
            root.mkdir()
            self.target(root, "SAMPLE_MAIN", "MODEL_A_V1", "Product  A")


if __name__ == "__main__":
    unittest.main(verbosity=2)
