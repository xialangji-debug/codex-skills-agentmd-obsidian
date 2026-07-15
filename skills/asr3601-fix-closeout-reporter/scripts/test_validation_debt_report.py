#!/usr/bin/env python3
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import validation_debt_report as report


def write_note(root: Path, name: str, body: str) -> None:
    (root / name).write_text(body.strip() + "\n", encoding="utf-8")


class ValidationDebtReportTests(unittest.TestCase):
    def test_scan_uses_only_last_explicit_status_and_excludes_closed_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_note(
                root,
                "closed.md",
                """
# 已闭环事项

## 元信息
- 项目路径：D:/XM/closed
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
- 项目路径：D:/XM/watch
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
- 项目路径：D:/XM/watch
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
- 项目路径：D:/XM/jc2
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
- 项目路径：D:/XM/released
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


if __name__ == "__main__":
    unittest.main()
