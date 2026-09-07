#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("asr3602_build_profile.py")
SPEC = importlib.util.spec_from_file_location("asr3602_build_profile_under_test", SCRIPT)
PROFILE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROFILE)


class BuildProfileTests(unittest.TestCase):
    def run_git(self, root: Path, *args: str) -> None:
        subprocess.run(["git", "-C", str(root), *args], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def make_repo(
        self,
        root: Path,
        *,
        support: str = "ASR3602_BUILD_VERIFIED",
        release_charge: int = 0,
        target_os: str = "ALIOS",
        ps_mode: str = "LITE_LTEONLY",
        chip_id: str = "CRANEL",
    ) -> Path:
        (root / ".codex-project").mkdir()
        (root / "config").mkdir()
        (root / "src").mkdir()
        (root / "out").mkdir()
        command = f"make craneg_modem_watch TARGET_OS={target_os} PS_MODE={ps_mode} CHIP_ID={chip_id}"
        (root / ".codex-project" / "variant.md").write_text(
            "\n".join([
                f"- CHIP_ID：`{chip_id}`",
                f"- TARGET_OS：`{target_os}`",
                f"- PS_MODE：`{ps_mode}`",
                "- 构建目标：`craneg_modem_watch`",
                f"- 构建命令：`{command}`",
            ]) + "\n",
            encoding="utf-8",
        )
        (root / "config" / "watchdog.json").write_text(
            json.dumps([{"id": "CDF", "image": "EEHandlerConfig.nvm"}]), encoding="utf-8"
        )
        (root / "config" / "charge.h").write_bytes(
            f"#define USE_LV_CHARGING_BATTERY {release_charge}\r\n".encode("ascii")
        )
        (root / "src" / "at.c").write_text("int at_command;\n", encoding="ascii")
        yl_dir = root / "gui" / "lv_watch" / "lv_apps" / "yl"
        yl_dir.mkdir(parents=True)
        (yl_dir / "yl.h").write_bytes(
            b'#define yl_device_ver "LT52_TEST_20260818_1200_V1.0.0_Release"\r\n#define KEEP_VALUE 1\r\n'
        )
        adapter = {
            "schemaVersion": 1,
            "adapterId": "fixture-asr3602",
            "product": "FIXTURE",
            "supportLevel": support,
            "chipId": chip_id,
            "targetOs": target_os,
            "psMode": ps_mode,
            "buildTarget": "craneg_modem_watch",
            "build": {
                "command": command,
                "commandArgs": command.split(),
                "preBuild": {"command": "ninja -C out -t clean", "commandArgs": ["ninja", "-C", "out", "-t", "clean"]},
            },
            "watchdogConfig": {"path": "config/watchdog.json", "entryId": "CDF", "entryImage": "EEHandlerConfig.nvm"},
            "chargingAnimation": {
                "path": "config/charge.h",
                "defineName": "USE_LV_CHARGING_BATTERY",
                "releaseValue": release_charge,
                "dumpTestValue": 0,
                "stubStrategy": "none",
            },
            "artifacts": {"outputDir": "out", "zipName": "firmware.zip", "mdbName": "firmware.mdb.txt"},
            "allowedTemporaryFiles": ["config/watchdog.json"] + (["config/charge.h"] if release_charge else []),
            "forbiddenSourceMarkers": [{"path": "src/at.c", "marker": "ASR360X_DUMP_ACCEPTANCE_TEST"}],
            "dumpAcceptance": {"sourcePath": "src/at.c", "marker": "ASR360X_DUMP_ACCEPTANCE_TEST"},
        }
        adapter_path = root / ".codex-project" / "asr3602-build-profile.json"
        adapter_path.write_text(json.dumps(adapter, indent=2) + "\n", encoding="utf-8")
        self.run_git(root, "init", "-q")
        self.run_git(root, "config", "user.name", "Test")
        self.run_git(root, "config", "user.email", "test@example.invalid")
        self.run_git(root, "add", ".")
        self.run_git(root, "commit", "-q", "-m", "fixture")
        return adapter_path

    def test_release_requires_clean_verified_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            adapter = self.make_repo(root)
            result = PROFILE.preflight("release", adapter, root)
            self.assertEqual("PASSED", result["status"])
            self.assertEqual("release", result["buildProfile"])
            (root / "dirty.txt").write_text("dirty", encoding="ascii")
            with self.assertRaisesRegex(PROFILE.ProfileError, "clean worktree"):
                PROFILE.preflight("release", adapter, root)

    def test_all_confirmed_build_identities_are_accepted(self) -> None:
        identities = (
            ("THREADX", "LTEGSM", "CRANEG"),
            ("ALIOS", "LITE_LTEONLY", "CRANEL"),
            ("THREADX", "LITE_LTEONLY", "CRANEL"),
        )
        for target_os, ps_mode, chip_id in identities:
            with self.subTest(identity=(target_os, ps_mode, chip_id)), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                adapter = self.make_repo(
                    root,
                    support="ASR360X_BUILD_VERIFIED",
                    target_os=target_os,
                    ps_mode=ps_mode,
                    chip_id=chip_id,
                )
                result = PROFILE.preflight("release", adapter, root)
                self.assertEqual("PASSED", result["status"])

    def test_release_resume_allows_only_expected_version_time_change(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            adapter = self.make_repo(root)
            yl_h = root / "gui" / "lv_watch" / "lv_apps" / "yl" / "yl.h"
            yl_h.write_bytes(
                b'#define yl_device_ver "LT52_TEST_20260818_1305_V1.0.0_Release"\r\n#define KEEP_VALUE 1\r\n'
            )
            result = PROFILE.preflight(
                "release",
                adapter,
                root,
                allow_release_version_resume=True,
                expected_release_time="20260818_1305",
            )
            resume = result["preconditions"]["releaseVersionResume"]
            self.assertTrue(resume["allowed"])
            self.assertEqual("20260818_1305", resume["expectedReleaseTime"])

    def test_release_resume_rejects_other_file_or_other_yl_change(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            adapter = self.make_repo(root)
            yl_h = root / "gui" / "lv_watch" / "lv_apps" / "yl" / "yl.h"
            yl_h.write_bytes(
                b'#define yl_device_ver "LT52_TEST_20260818_1305_V1.0.0_Release"\r\n#define KEEP_VALUE 2\r\n'
            )
            with self.assertRaisesRegex(PROFILE.ProfileError, "outside"):
                PROFILE.preflight(
                    "release",
                    adapter,
                    root,
                    allow_release_version_resume=True,
                    expected_release_time="20260818_1305",
                )

            self.run_git(root, "checkout", "--", "gui/lv_watch/lv_apps/yl/yl.h")
            (root / "other.txt").write_text("dirty", encoding="ascii")
            with self.assertRaisesRegex(PROFILE.ProfileError, "only an unstaged modification"):
                PROFILE.preflight(
                    "release",
                    adapter,
                    root,
                    allow_release_version_resume=True,
                    expected_release_time="20260818_1305",
                )

    def test_release_allows_charging_value_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            adapter = self.make_repo(root, release_charge=1)
            data = json.loads(adapter.read_text(encoding="utf-8"))
            data["chargingAnimation"]["releaseValue"] = 0
            adapter.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            self.run_git(root, "add", ".")
            self.run_git(root, "commit", "-q", "-m", "adapter release policy")

            result = PROFILE.preflight("release", adapter, root)
            self.assertEqual("PASSED", result["status"])
            self.assertEqual(1, result["preconditions"]["chargingAnimationValue"])

    def test_normal_test_records_dirty_but_rejects_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            adapter = self.make_repo(root, support="CANDIDATE")
            (root / "dirty.txt").write_text("dirty", encoding="ascii")
            with self.assertRaisesRegex(PROFILE.ProfileError, "CANDIDATE"):
                PROFILE.preflight("normal-test", adapter, root)
            result = PROFILE.preflight("normal-test", adapter, root, allow_candidate=True)
            self.assertTrue(result["source"]["dirty"])

    def test_dump_profile_declares_exact_temporary_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            adapter = self.make_repo(root)
            result = PROFILE.preflight("dump-test", adapter, root)
            self.assertEqual("remove-exactly-one", result["temporaryChanges"]["watchdogEntry"]["action"])
            self.assertEqual(0, result["temporaryChanges"]["chargingAnimation"]["to"])

    def test_duplicate_watchdog_entry_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            adapter = self.make_repo(root)
            entry = {"id": "CDF", "image": "EEHandlerConfig.nvm"}
            (root / "config" / "watchdog.json").write_text(json.dumps([entry, entry]), encoding="utf-8")
            with self.assertRaisesRegex(PROFILE.ProfileError, "exactly one"):
                PROFILE.preflight("normal-test", adapter, root)

    def test_wrong_charge_value_and_dump_marker_are_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            adapter = self.make_repo(root, release_charge=1)
            (root / "config" / "charge.h").write_text("#define USE_LV_CHARGING_BATTERY 0\n", encoding="ascii")
            with self.assertRaisesRegex(PROFILE.ProfileError, "charging configuration mismatch"):
                PROFILE.preflight("normal-test", adapter, root)
            (root / "config" / "charge.h").write_text("#define USE_LV_CHARGING_BATTERY 1\n", encoding="ascii")
            (root / "src" / "at.c").write_text("ASR360X_DUMP_ACCEPTANCE_TEST\n", encoding="ascii")
            with self.assertRaisesRegex(PROFILE.ProfileError, "marker remains"):
                PROFILE.preflight("normal-test", adapter, root)

    def test_adapter_and_variant_mismatch_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            adapter = self.make_repo(root)
            data = json.loads(adapter.read_text(encoding="utf-8"))
            data["chipId"] = "CRANEG"
            adapter.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(PROFILE.ProfileError, "unsupported ASR360x"):
                PROFILE.validate_adapter(data, root)


if __name__ == "__main__":
    unittest.main()
