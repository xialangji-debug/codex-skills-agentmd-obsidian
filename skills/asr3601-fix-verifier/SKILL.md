---
name: asr3601-fix-verifier
description: Verify ASR3601/Crane SDK LVGL children-watch firmware fixes before final reporting. Use after modifying ASR3601, Crane SDK, LVGL v7, watch firmware, CATStudio-driven fixes, alarms, power/SIM/UI/protocol code, or cross-branch ports, especially when Codex should run git status, branch and short commit checks, git diff --check, targeted rg checks, target ninja/make builds, variant boundary checks, and decide whether to write an Obsidian fix-pattern.
---

# ASR3601 Fix Verifier

Use this skill after a firmware fix or port, before the final answer.

## Required Snapshot

Collect and report:

```text
项目路径：
当前分支：
当前提交：
dirty worktree：
修改文件：
目标变体：标准版 / 运动版 / phone / simulator / 未指定
验证状态：
```

Never revert unrelated local changes. If the worktree was dirty before the fix, distinguish user changes from the current fix when possible.

## Verification Order

1. `git status --short`
2. `git branch --show-current`
3. `git rev-parse --short HEAD`
4. Targeted `rg` checks for the changed symbol, UI text, protocol field, resource name, or guard condition.
5. `git diff --check`
6. The narrowest relevant build, for example:
   - `ninja -C out/product/craneg_modem_watch lv_watch`
   - project `make` target from `AGENTS.md`
   - object-level build when a full build is too expensive
7. Variant boundary check when relevant: standard watch, sport watch, phone, simulator, language/resource pack.
8. Decide whether the fix has reusable value and should be recorded through `obsidian-fix-pattern-memory`.

## Helper Script

For a quick verification snapshot:

```powershell
python C:\Users\84365\.codex\skills\asr3601-fix-verifier\scripts\verify_asr_fix.py `
  --repo D:\XM\360x_202403r1 `
  --rg "get_now_timer" `
  --build-command "ninja -C out/product/craneg_modem_watch lv_watch"
```

The script runs non-destructive Git checks, optional `rg` searches, optional build commands, and prints a Markdown report.

## Report Shape

Use concise Chinese:

```text
验证：
- 分支/提交：
- dirty worktree：
- diff check：
- 构建：
- 变体边界：
- 记忆库：
```

If a build cannot be run, say exactly why and which weaker checks passed.
