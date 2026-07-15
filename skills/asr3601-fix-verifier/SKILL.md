---
name: asr3601-fix-verifier
description: Verify ASR3601/Crane SDK LVGL children-watch firmware fixes before final reporting. Use after modifying ASR3601, Crane SDK, LVGL v7, watch firmware, CATStudio-driven fixes, alarms, power/SIM/UI/protocol code, multi-language or long-text UI, or cross-branch ports, especially when Codex should run git status, canonical variant-fingerprint checks, git diff --check, targeted rg checks, LVGL i18n preflight, target ninja/make builds, variant boundaries, and decide whether to write an Obsidian fix-pattern.
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
yl_device_ver：
芯片 / OS / PS_MODE：
协议 / 客户产品变体：
构建命令 / 禅道映射：
修改文件：
目标变体：标准版 / 运动版 / phone / simulator / 未指定
验证状态：
```

Read `.codex-project/variant.md` first when present. Refresh it through `asr3601-project-onboard` when repo, branch, commit, dirty state, or `yl_device_ver` is stale.

Never revert unrelated local changes. If the worktree was dirty before the fix, distinguish user changes from the current fix when possible.

## Verification Order

1. `git status --short`
2. `git branch --show-current`
3. `git rev-parse --short HEAD`
4. Targeted `rg` checks for the changed symbol, UI text, protocol field, resource name, or guard condition.
5. `git diff --check`
6. Run the bundled LVGL i18n/long-text preflight for UI, language, date/time, calendar, dialog, or label changes. It checks width-before-long-mode ordering, small formatting buffers, unsafe `sprintf`, hard-coded Chinese in third-party-language paths, and long weekday resources. Treat it as a static warning layer, not a substitute for real-device localization review.
7. The narrowest relevant build, for example:
   - `ninja -C out/product/craneg_modem_watch lv_watch`
   - project `make` target from `AGENTS.md`
   - object-level build when a full build is too expensive
8. Variant boundary check when relevant: standard watch, sport watch, phone, simulator, language/resource pack.
9. Decide whether the fix has reusable value and should be recorded through `obsidian-fix-pattern-memory`.

## Helper Script

For a quick verification snapshot:

```powershell
python C:\Users\84365\.codex\skills\asr3601-fix-verifier\scripts\verify_asr_fix.py `
  --repo D:\XM\360x_202403r1 `
  --rg "get_now_timer" `
  --i18n-language vi `
  --i18n-path gui/lv_watch/framework/language/lang_vi.c `
  --build-command "ninja -C out/product/craneg_modem_watch lv_watch"
```

The script runs non-destructive Git checks, optional `rg` searches, automatic changed-file LVGL i18n/long-text preflight, optional build commands, and prints a Markdown report. Use `--i18n-strict` only when high-severity static findings should fail the verification gate; use `--skip-i18n-preflight` for non-UI work.

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
