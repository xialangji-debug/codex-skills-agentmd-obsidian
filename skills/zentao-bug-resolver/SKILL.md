---
name: zentao-bug-resolver
description: Resolve selected YueLan Zentao bugs after firmware fixes or triage decisions are complete. Use when the user asks to mark Zentao/禅道 bugs as solved/已解决, reopen accidentally closed bugs and change them back to 已解决, choose between 已解决 and 外部原因, write required platform-side remarks, submit bug resolution forms, or make a reviewed resolve plan from previously fetched ASR3601/ASR3602 firmware bug work-items. This skill is for development-side resolution only; it must not close bugs for QA/test.
---

# Zentao Bug Resolver

Use this skill after selected bugs have already been inspected or fixed. It is the downstream step after `zentao-bug-triage`: triage/fix first, then preview and submit the Zentao resolution form.

## Safety Rules

- Do not store Zentao passwords in this skill, reports, memory, or final answers. Use the existing credential source from `zentao-bug-triage`.
- Never resolve all fetched bugs automatically. Only resolve bug IDs the user selected or IDs present in an explicit resolve plan.
- Default to preview mode. Run the script without `--submit` first; it writes a local report and does not save the Zentao form.
- Use `--submit` only when the user clearly asks to solve/mark those bugs in Zentao or has approved the preview.
- Development-side closeout stops at `已解决`. Never click `关闭`; QA/test owns final closure unless the user explicitly says the tester has verified and asks Codex to close it.
- If a fixed bug was accidentally `已关闭`, reactivate it first, then submit the resolve form with solution `已解决`. Do not leave it closed and do not close it again after resolving.
- Do not resolve `ignored-items.md` bugs unless the user explicitly moved them into scope.
- For reactivated bugs, use the latest activation note and the current fix/verification evidence as the decision source.
- Preserve unrelated local source changes.

## Decision Rules

- Choose `fixed` / `已解决` when the current branch contains a code-side fix or the issue is verified already fixed in this build. For ASR3601/ASR3602 current-branch firmware work, use the current branch/version as `resolvedBuild` unless the user gives a specific release version.
- Choose `external` / `外部原因` when evidence shows the issue is platform, backend, data, account, network, applet, test environment, or non-watch-code behavior. A remark is required and must explain why it is external/platform-side.
- Do not use `duplicate`, `bydesign`, `notrepro`, `postponed`, or `willnotfix` unless the user explicitly asks for that solution or the Zentao evidence is unambiguous. Add a remark for these choices.
- For non-branch-specific work, `trunk` / `主干` is still acceptable when no concrete build exists. For current APP协议/branch work, prefer `--build-current-branch` or `resolvedBuild: current-branch`.
- Preserve the current assignee by default. Only change it when the user explicitly requests an assignee with `assignTo` or `--assign-to`.
- For a plain `fixed` resolution, leave the comment empty unless the user explicitly provides one. External and other non-fixed resolutions still require a remark.

## Workflow

1. Confirm local context:
   - Run `git status --short`, `git branch --show-current`, and `git rev-parse --short HEAD`.
   - Confirm the selected bug IDs and whether each item is code-fixed or external/platform-side.
   - If a `work-items.md` exists from `zentao-bug-triage`, read it before deciding; do not rely on titles only.

2. Create a resolve plan when more than one bug is involved or when any item is external:

```markdown
# Zentao Resolve Plan

## Bug #2957 录音过程中收到的微聊消息不会弹出未读弹窗
resolution: fixed
resolvedBuild: trunk

## Bug #2959 小程序设置AI防欺凌后未上报预警位置
resolution: external
resolvedBuild:
comment:
平台侧未按当前协议识别手表已上报的防欺凌定位字段，设备端日志显示上报链路正常，需要平台按协议字段解析。
```

For current-branch firmware fixes, prefer:

```markdown
resolvedBuild: current-branch
```

3. Preview the Zentao form operations:

```powershell
node "$env:USERPROFILE\.codex\skills\zentao-bug-resolver\scripts\zentao_bug_resolver.js" --repo . --plan ".codex\zentao-resolve-plan.md"
```

The script automatically discovers the bundled `node_modules` and `.pnpm\node_modules` paths. Do not set `NODE_PATH` manually.

For current-branch code fixes, preview with the branch as the resolved build:

```powershell
node "$env:USERPROFILE\.codex\skills\zentao-bug-resolver\scripts\zentao_bug_resolver.js" --repo . --plan ".codex\zentao-resolve-plan.md" --build-current-branch
```

For simple fixed bugs that need no remark:

```powershell
node "$env:USERPROFILE\.codex\skills\zentao-bug-resolver\scripts\zentao_bug_resolver.js" --repo . --ids 2799,2917,2937,2957 --minimal
```

`--minimal` only accepts `--ids`. It selects `fixed`, leaves the comment empty, and preserves the existing assignee. If the current branch is not a Zentao build option, the script falls back to `trunk` and records that fallback in the report.

4. Review the generated report. It must show:
   - ID and title.
   - Selected solution label/value.
   - Resolved build label/value.
   - Whether the assignee was preserved or explicitly changed.
   - Whether the comment is empty.
   - Any validation error.

5. Submit only after approval:

```powershell
node "$env:USERPROFILE\.codex\skills\zentao-bug-resolver\scripts\zentao_bug_resolver.js" --repo . --plan ".codex\zentao-resolve-plan.md" --submit
```

If the user says previously fixed bugs were accidentally closed, submit with reactivation enabled:

```powershell
node "$env:USERPROFILE\.codex\skills\zentao-bug-resolver\scripts\zentao_bug_resolver.js" --repo . --plan ".codex\zentao-resolve-plan.md" --build-current-branch --activate-closed --submit
```

This script path:

- reads each bug status first;
- skips bugs already `已解决` unless `--force-resolve` is passed;
- rejects `已关闭` bugs unless `--activate-closed` is passed;
- activates closed bugs with a development-process note;
- sets solution `已解决`, sets `resolvedBuild`, fills the note, submits, and reopens the detail page;
- fails loudly unless the final status is `已解决`.

6. After submission, report which bugs were actually submitted and which failed. If a bug was external, include the exact remark summary in the final answer.

## Resources

- `scripts/zentao_bug_resolver.js`: opens YueLan Zentao resolve forms, validates solution/build/assignee/comment choices, writes preview reports, and submits only with `--submit`.
- `references/resolve-plan-format.md`: detailed plan format and decision examples.
