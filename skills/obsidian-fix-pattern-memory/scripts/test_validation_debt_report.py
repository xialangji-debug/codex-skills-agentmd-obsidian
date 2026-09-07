#!/usr/bin/env python3
from __future__ import annotations

import tempfile
import unittest
import base64
import json
from pathlib import Path

import validation_debt_report as report


def write_note(root: Path, name: str, body: str) -> None:
    (root / name).write_text(body.strip() + "\n", encoding="utf-8")


class ValidationDebtReportTests(unittest.TestCase):
    def test_managed_targets_report_per_target_debt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state = {
                "schema_version": 2,
                "fix_id": "FP-TEST",
                "reference_target": "target-device",
                "last_reference_target": None,
                "targets": [
                    {
                        "target_id": "target-build", "project_key": "sample-a", "branch": "main",
                        "commit": "abc1234", "implementation": "applied", "verification": "build_passed",
                        "zentao": "active", "relation": "applied", "bug_ids": ["1001"],
                    },
                    {
                        "target_id": "target-device", "project_key": "sample-b", "branch": "release",
                        "commit": "def5678", "implementation": "committed", "verification": "device_verified",
                        "zentao": "resolved", "relation": "reference", "bug_ids": ["1001"],
                    },
                    {
                        "target_id": "target-qa", "project_key": "sample-c", "branch": "qa",
                        "commit": "9999999", "implementation": "committed", "verification": "qa_verified",
                        "zentao": "closed", "relation": "applied", "bug_ids": ["1001"],
                    },
                ],
            }
            encoded = base64.urlsafe_b64encode(json.dumps(state).encode("utf-8")).decode("ascii")
            write_note(root, "managed.md", f"""
---
domains:
  - asr
---
# Managed fix
<!-- codex-fix-state-json: {encoded} -->
""")
            debts, file_count, explicit_count = report.scan(root)
            self.assertEqual(file_count, 1)
            self.assertEqual(explicit_count, 1)
            self.assertEqual(len(debts), 2)
            by_project = {debt.project: debt for debt in debts}
            self.assertIn("真机回归", by_project["sample-a"].pending)
            self.assertIn("QA 关闭", by_project["sample-b"].pending)
            self.assertEqual({debt.domain for debt in debts}, {"asr"})
            rendered = report.render_report(debts, root, file_count, explicit_count)
            self.assertIn("当前债务笔记：1", rendered)
            self.assertIn("当前债务目标行：2", rendered)
            self.assertIn("已闭环笔记：0", rendered)
            self.assertNotIn("已闭环笔记：-", rendered)

    def test_scan_uses_only_last_explicit_status_and_excludes_closed_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_note(
                root,
                "closed.md",
                """
# 已闭环事项

## 元信息
- 项目路径：/workspace/closed
- 当前分支：main
- 当前提交：abc1234
- 验证状态：未验证，待真机验证
- 验证状态：已验证

## 历史验证方法
- 旧记录曾写待真机验证。
""",
            )

            debts, file_count, explicit_count = report.scan(root)

            self.assertEqual(file_count, 1)
            self.assertEqual(explicit_count, 1)
            self.assertEqual(debts, [])

    def test_scan_classifies_device_protocol_and_build_blockers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_note(
                root,
                "device.md",
                """
# 低电量 10/5/2
- 项目路径：/workspace/watch
- 当前分支：feature
- 当前提交：abc1234
- 验证状态：对象级 ARMCC 编译通过，待真机验证
""",
            )
            write_note(
                root,
                "protocol.md",
                """
# DELIMG 应答
- 项目路径：/workspace/watch
- 当前分支：feature
- 当前提交：def5678
- 验证状态：ARMCC 对象编译通过，真机协议日志待验证
""",
            )
            write_note(
                root,
                "package.md",
                """
# 整包后处理
- 项目路径：/workspace/example-device
- 当前分支：jc2
- 当前提交：9999999
- 验证状态：未验证（改动文件已编译通过；整包后处理因本机缺少 xzcat 停止）
""",
            )

            debts, _, explicit_count = report.scan(root)

            self.assertEqual(explicit_count, 3)
            self.assertEqual(len(debts), 3)
            by_source = {debt.source.name: debt for debt in debts}
            self.assertEqual(by_source["device.md"].priority, "P1")
            self.assertIn("真机回归", by_source["device.md"].pending)
            self.assertIn("真机/平台协议日志", by_source["protocol.md"].pending)
            self.assertEqual(by_source["package.md"].priority, "P0")
            self.assertIn("完整固件/整包", by_source["package.md"].pending)
            self.assertIn("xzcat", by_source["package.md"].next_action)

    def test_published_without_device_regression_is_p0(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_note(
                root,
                "released.md",
                """
# 已发布但待真机
- 项目路径：/workspace/released
- 当前分支：release
- 当前提交：fedcba9
- 验证状态：完整固件构建与发布已验证，真机回归待测试
""",
            )

            debts, file_count, explicit_count = report.scan(root)
            rendered = report.render_report(debts, root, file_count, explicit_count)

            self.assertEqual(debts[0].priority, "P0")
            self.assertIn("完整固件构建", debts[0].passed_gates)
            self.assertIn("发布/出版本", debts[0].passed_gates)
            for column in ("项目", "分支", "commit", "已过门槛", "待办", "下一动作"):
                self.assertIn(column, rendered)

    def test_open_loops_draft_is_opt_in_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_note(
                root,
                "pending.md",
                """
# 待回归事项
- 项目：watch
- 当前分支：main
- 当前提交：1234567
- 验证状态：对象级 ARMCC 编译通过，待真机验证
""",
            )
            debts, _, _ = report.scan(root)
            draft = report.render_open_loops_draft(debts, root)

            self.assertIn("不得据此自动升级验证状态或关闭禅道", draft)
            self.assertIn("[P1] 待回归事项", draft)

    def test_campaign_groups_managed_targets_and_keeps_legacy_separate(self) -> None:
        source = Path("managed.md")
        common = dict(
            source=source,
            title="fix",
            project="watch",
            branch="main",
            commit="abc1234",
            status="verification=build_passed",
            passed_gates=("目标构建",),
            pending=("真机回归",),
            priority="P1",
            next_action="device test",
            domain="asr",
            version="V1",
            variant_id="TW10",
        )
        debts = [
            report.Debt(**common, target_id="target-a"),
            report.Debt(**{**common, "source": Path("second.md")}, target_id="target-b"),
            report.Debt(**{**common, "source": Path("legacy.md")}, target_id="", legacy=True),
        ]
        campaigns = report.build_campaigns(debts)
        self.assertEqual(len(campaigns), 2)
        managed = next(item for item in campaigns if not item["legacy"])
        self.assertEqual(managed["state"], "DEVICE_VERIFICATION_PENDING")
        self.assertTrue(managed["release_blocked"])
        self.assertEqual(managed["target_ids"], ["target-a", "target-b"])
        self.assertEqual(
            report.build_campaigns(debts)[0]["campaign_id"],
            campaigns[0]["campaign_id"],
        )

    def test_filters_domain_project_branch_priority_and_since(self) -> None:
        debt = report.Debt(
            source=Path("esp.md"),
            title="ESP fix",
            project="esp32_c5",
            branch="main",
            commit="abc",
            status="verification=build_passed",
            passed_gates=("目标构建",),
            pending=("真机回归",),
            priority="P1",
            next_action="test",
            domain="esp32",
            updated_at="2026-08-18T10:00:00+08:00",
        )
        self.assertEqual(
            report.filter_debts([debt], "esp32", "ESP32", "MAIN", "P1", "2026-08-18"),
            [debt],
        )
        self.assertEqual(report.filter_debts([debt], domain="asr"), [])
        self.assertEqual(report.filter_debts([debt], since="2026-08-19"), [])

    def test_open_loops_delta_only_reconciles_machine_markers(self) -> None:
        debt = report.Debt(
            source=Path("new.md"),
            title="New debt",
            project="watch",
            branch="main",
            commit="abc",
            status="verification=build_passed",
            passed_gates=("目标构建",),
            pending=("真机回归",),
            priority="P1",
            next_action="test",
            target_id="target-new",
        )
        existing = "- [ ] Human item\n- [ ] Old <!-- validation-debt:target-old -->\n"
        delta = report.render_open_loops_delta([debt], Path("fix-patterns"), existing)
        self.assertIn("新增：1", delta)
        self.assertIn("疑似过期：1", delta)
        self.assertIn("target-new", delta)
        self.assertIn("target-old", delta)
        self.assertNotIn("Human item", delta)


if __name__ == "__main__":
    unittest.main()
