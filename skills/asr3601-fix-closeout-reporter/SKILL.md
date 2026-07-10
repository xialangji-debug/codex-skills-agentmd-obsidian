---
name: asr3601-fix-closeout-reporter
description: Close out ASR3601/ASR3602/Crane SDK/LVGL children-watch firmware fixes after code changes or triage decisions are complete. Use when the user asks “修复完了吗”, “改了什么”, “怎么验证”, “收工更新”, “这个怎么写解决说明”, “禅道标记解决”, or needs a Chinese delivery report that summarizes problem, root cause, modified behavior/files, verification, risks, missing coverage, Obsidian fix-pattern need, and Zentao-ready resolution notes. Use asr3601-fix-verifier for verification checks, obsidian-fix-pattern-memory for reusable memory writes, and zentao-bug-resolver only after the user explicitly wants to mark selected Zentao bugs resolved.
---

# ASR3601 Fix Closeout Reporter

Use this skill after a fix, port, or completed triage decision. Its job is to turn code work into a deliverable result: verification evidence, Chinese closeout report, memory decision, and optional Zentao resolution wording.

## Role Boundary

- Use `asr3601-bug-intake-orchestrator` or `asr3601-lvgl-firmware-triage` when the bug has not been investigated or fixed yet.
- Use `asr3601-cross-branch-porting` when the remaining work is source-target migration.
- Use `asr3601-fix-verifier` for raw verification checks; this skill consumes those checks and writes the final report.
- Use `obsidian-fix-pattern-memory` only when the fix is reusable across branches, versions, or similar projects.
- Use `zentao-bug-resolver` only when the user explicitly asks to submit or mark selected Zentao bugs resolved. Otherwise, produce a preview/草稿 only.
- Zentao development closeout stops at resolving the bug: set the bug to `已解决` with resolution `已解决` and a Chinese note.
  Do not click `关闭` from the development side; final closure belongs to test/QA unless the user explicitly says the tester has verified and asks Codex to close it.

Never revert unrelated local changes. If the worktree is dirty, distinguish known fix files from unrelated user changes when possible.

## Closeout Workflow

1. Confirm context:
   - project path
   - bug ID/title if present
   - current branch and short commit
   - dirty worktree
   - target product/variant: standard watch, sport watch, phone, simulator, C10 乐智, C10 公版, 360x, LT52, AKQ, or unknown
   - user goal: report only, verify, memory update, Zentao resolution draft, or actual Zentao submit
2. Run non-destructive checks:
   - `git status --short`
   - `git branch --show-current`
   - `git rev-parse --short HEAD`
   - `git diff --name-status`
   - `git diff --stat`
   - `git diff --check`
   - targeted `rg` checks for changed symbols, UI text, protocol fields, resource IDs, or guard conditions
   - the narrowest known build or syntax check
3. Prefer the helper script for a compact snapshot:

```powershell
python C:\Users\84365\.codex\skills\asr3601-fix-closeout-reporter\scripts\closeout_snapshot.py `
  --repo D:\XM\360x_202403r1 `
  --rg "changed_symbol_or_protocol_field" `
  --build-command "ninja -C out/product/craneg_modem_watch lv_watch"
```

4. If a deeper verification run is needed, use `asr3601-fix-verifier` and include its result in the final closeout.
5. Decide memory:
   - Write/update `Codex\fix-patterns\` through `obsidian-fix-pattern-memory` when the fix is a reusable pattern, regression, cross-branch port, protocol mismatch, or hard-won project lesson.
   - Do not write memory for one-off wording, temporary local setup, unsupported experiments, or fixes without verified reusable value.
6. Prepare Zentao wording:
   - For code-fixed bugs, choose `已解决/fixed` and write a concise resolution note only if useful.
   - For platform/backend/app/test-environment issues, choose `外部原因/external` and include the evidence.
   - Do not submit to Zentao unless the user explicitly asks or approves the preview.
   - After submitting a code-fixed bug, leave it in `已解决`. Do not close it unless the request explicitly asks for QA/test closure.
   - For selected bugs that should be submitted in Zentao, enter `zentao-bug-resolver` and use the current branch as `resolvedBuild` for current APP协议/branch fixes.
   - If a fixed bug was mistakenly closed, use the resolver's `--activate-closed` flow: reactivate first, then resolve as `已解决`; never click `关闭` from development.

## Required Report Shape

Write concise Chinese. Include these fields unless irrelevant:

```text
问题：
根因：
修改：
影响范围：
验证：
风险：
未覆盖项：
记忆库：
禅道解决说明：
```

For `验证`, include command names and results, not just “已验证”. If a build cannot be run, state exactly why and which weaker checks passed.

For `修改`, summarize both files and behavior:

```text
修改文件：
- path/to/file.c：行为变化
```

For `风险`, call out variant and platform boundaries:

```text
标准版：
运动版：
phone/simulator：
APP/小程序/YL/AKQ/平台：
```

## Zentao Preview Shape

When the user asks “这个怎么写解决说明” or “禅道标记解决”, first produce a preview:

```text
建议解决方式：已解决 / 外部原因
resolvedBuild：trunk / 具体版本 / 留空
assignTo：self
解决说明：
...
是否需要提交：等待用户确认
```

After the user confirms submission, enter `zentao-bug-resolver`.

For current-branch firmware fixes, the submit command normally includes:

```powershell
node "$env:USERPROFILE\.codex\skills\zentao-bug-resolver\scripts\zentao_bug_resolver.js" --repo . --plan ".codex\zentao-resolve-plan.md" --build-current-branch --activate-closed --submit
```

## Helper Script

`scripts/closeout_snapshot.py` prints a Markdown snapshot with Git state, changed files, diff check, optional searches, optional build output, and a report template. It is read-only except for build commands passed by the caller.
