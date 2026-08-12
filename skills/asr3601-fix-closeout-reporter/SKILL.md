---
name: asr3601-fix-closeout-reporter
description: Verify and close out ASR3601/ASR3602/360x/Crane SDK/LVGL children-watch firmware fixes, or aggregate explicit validation debt across Obsidian fix-pattern notes. Use for an explicit closeout, multi-step delivery review, ports, release readiness, or when the user asks “修复完了吗”, “怎么验证”, “收工更新”, “禅道标记解决”, “还有哪些没验证”, “待真机”, “验证债务”, “待回归”, or “发布前验收清单”. Do not auto-trigger after a direct Codex Fast Fix, which performs one narrow inline verification and reports without a second closeout pass.
---

# ASR3601 Fix Verification and Closeout

Use this skill for explicit closeout, ports, multi-step delivery, release readiness, or validation-debt aggregation. Do not invoke it automatically after a direct Codex Fast Fix.

## Role Boundary

- Use `zentao-bug-triage` for Zentao intake or `asr3601-lvgl-firmware-triage` when the bug has not been investigated.
- Use `asr3601-cross-branch-porting` when source-target migration remains.
- Refresh a missing or stale `.codex-project/variant.md` through `asr3601-project-onboard` before verification.
- Use `obsidian-fix-pattern-memory` as the sole writer for every completed behavior fix and its exact-target evidence.
- Use `zentao-bug-resolver` only when the user explicitly asks to submit selected bugs. Otherwise produce a preview.
- Development closeout stops at `已解决`; do not perform QA `关闭` without explicit tester authority and request.

Never revert unrelated local changes. Distinguish pre-existing user changes, the current fix, unstaged changes, and staged changes.

## Verification Workflow

1. Read `<repo>/.codex-project/variant.md` and compare repo, branch, commit, dirty state, and `yl_device_ver` with the live checkout. Do not reuse stale build/protocol/customer/Zentao assumptions.
2. Confirm bug ID/title, target product/variant, changed files, and requested verification layer.
3. Run the non-destructive baseline:
   - `git status --short`
   - `git branch --show-current`
   - `git rev-parse --short HEAD`
   - `git diff --name-status` and `git diff --cached --name-status`
   - `git diff --stat` and `git diff --cached --stat`
   - `git diff --check` and `git diff --cached --check`
4. Run targeted `rg` checks for changed symbols, UI text, protocol fields, resources, or guard conditions.
5. For UI, language, date/time, calendar, dialog, label, or long-text work, run the bundled preflight. It scans changed C/C++ files by default and can include explicit paths. Treat findings as static warnings, not device proof.
6. Run the narrowest documented build or syntax/object check.
7. Check relevant boundaries: standard/sport watch, phone/simulator, language/resource pack, and APP/mini-app/vendor/platform.
8. Separate static checks, full build/package, release, device regression, platform logs, and QA status. Never promote one layer into another.

Prefer the integrated helper:

```powershell
python "$env:USERPROFILE\.codex\skills\asr3601-fix-closeout-reporter\scripts\closeout_snapshot.py" `
  --repo D:\XM\360x_202403r1 `
  --rg "changed_symbol_or_protocol_field" `
  --build-command "ninja -C out/product/craneg_modem_watch lv_watch"
```

The helper runs LVGL preflight with locale `unspecified` by default. Pass a language only when the project evidence identifies it:

```powershell
python "$env:USERPROFILE\.codex\skills\asr3601-fix-closeout-reporter\scripts\closeout_snapshot.py" `
  --repo . --i18n-language ru --i18n-path gui/lv_watch/framework/language/lang_ru.c --i18n-strict
```

Use `--skip-i18n-preflight` for non-UI work. `--i18n-strict` fails only on high-severity static findings. Do not default a project to `vi` or any other locale.

`scripts/verify_asr_fix.py` remains as a compatibility entry point and accepts the same arguments.

## Memory Evidence Update

- A completed behavior fix should already have a canonical note and current target
  row from firmware triage or porting. Closeout upgrades only the exact target's
  evidence; it does not create a competing note format.
- Use `fix_memory.py event --event device_verified|platform_verified|build_passed`
  with reviewed evidence and `--write`.
- A build alone may produce `build_passed`; it is not device/platform verification.
- For a linked reactivated Bug, use `reactivated_same` only when repository,
  branch, version, variant, and material symptom all match. Otherwise leave the old
  target unchanged and report a variant candidate.
- Skip explanation-only work, temporary setup, reverted experiments, and changes
  the user explicitly excluded from memory.

## Validation Debt Mode

For “还有哪些没验证/待真机/验证债务/待回归/发布前验收清单”, run:

```powershell
python "$env:USERPROFILE\.codex\skills\asr3601-fix-closeout-reporter\scripts\validation_debt_report.py" `
  --fix-patterns "$env:USERPROFILE\Documents\Obsidian\CodexVault\Codex\fix-patterns"
```

- Keep the default read-only.
- Treat only the last explicit `验证状态` or `验证结论` field as authoritative.
- Exclude closed history and report project, branch, commit, passed layers, remaining work, priority, next action, and source note.
- Never upgrade trust, resolve Zentao, or infer QA completion from a build.
- `--open-loops-draft <output.md>` writes only the requested standalone draft.

## Required Report

```text
变体指纹：
  repo：
  branch / commit / dirty：
  yl_device_ver：
  CHIP_ID / TARGET_OS / PS_MODE：
  协议 / 客户产品：
  构建命令：
  禅道映射：
问题：
根因：
修改文件与行为：
影响范围：
验证命令与结果：
风险：
未覆盖项：
记忆库：
禅道解决说明：
```

State exactly why a build or device test was not run and which weaker checks passed.

## Zentao Preview

For solution wording or resolution requests, first produce:

```text
建议解决方式：已解决 / 外部原因
resolvedBuild：trunk / 具体版本 / 留空
assignTo：self
解决说明：
...
是否需要提交：等待用户确认
```

After explicit confirmation, enter `zentao-bug-resolver`. For current-branch fixes, use the current branch as `resolvedBuild`. Reactivate an accidentally closed bug before resolving it; never click `关闭` from development.

## Scripts

- `scripts/closeout_snapshot.py`: integrated variant, Git, staged/unstaged diff, targeted search, LVGL preflight, optional build, and report-template snapshot.
- `scripts/lvgl_i18n_preflight.py`: read-only LVGL v7 localization/long-text heuristic scan.
- `scripts/verify_asr_fix.py`: compatibility wrapper for the integrated snapshot.
- `scripts/validation_debt_report.py`: read-only validation-debt report unless a draft output is explicitly supplied.
