---
name: asr360x-bug-delivery-orchestrator
description: Coordinate selected ASR3601/ASR3602/360x/Crane/LVGL firmware bugs through deep fetch, current-branch diagnosis, narrow fixes, verification, one Chinese commit per bug, fix-pattern memory decisions, Zentao resolution, and an explicitly requested firmware release. Use when the user combines steps such as “修复、中文提交、关禅道”, “修复提交关禅道出版本”, asks to process several bug IDs sequentially, or wants resumable delivery status across those stages.
---

# ASR360x Bug Delivery Orchestrator

Coordinate existing specialist skills; do not duplicate their implementation.

## Boundaries

- Treat “关禅道” from development as mark `已解决`, not QA `关闭`, unless the user explicitly confirms tester authority and requests closure.
- Release only when the user explicitly says `出版本`, `上传`, `fnOS`, or `release`.
- Make one focused Chinese commit per bug unless the user explicitly asks to combine them.
- Never advance a stage without its evidence. Preserve unrelated local changes.
- A successful build does not equal device, platform, or QA verification.

## Specialist Routing

| Stage | Owner |
|---|---|
| Project fingerprint | `asr3601-project-onboard` |
| Deep fetch/detail/attachments | `zentao-bug-triage` |
| Current-branch diagnosis/fix | `asr3601-bug-intake-orchestrator` then `asr3601-lvgl-firmware-triage` |
| Cross-branch work | `asr3601-cross-branch-porting` |
| Verification | `asr3601-fix-verifier` |
| Closeout/memory decision | `asr3601-fix-closeout-reporter` and `obsidian-fix-pattern-memory` |
| Zentao resolution | `zentao-bug-resolver` |
| Explicit release | matching release skill, normally `akq-firmware-release` |

## Workflow

1. Initialize a local delivery state before editing:

```powershell
python "$env:USERPROFILE\.codex\skills\asr360x-bug-delivery-orchestrator\scripts\delivery_state.py" init --repo . --bugs 2935,2931,2868,2867
```

Add `--release-requested` only when release was explicitly requested.

2. Process bugs in the user-specified order. Advance only after the owner skill produced evidence:

```text
pending -> deep_fetched -> diagnosed -> fixed -> verified -> committed -> memory_decided -> zentao_resolved
```

3. Record every transition:

```powershell
python "$env:USERPROFILE\.codex\skills\asr360x-bug-delivery-orchestrator\scripts\delivery_state.py" advance `
  --repo . --bug 2935 --stage verified --evidence "diff check + target build passed"
```

For `committed`, also pass `--commit <short-sha>`. For `memory_decided`, record the note path or why memory was skipped.

4. Resolve selected bugs only after `committed` and `memory_decided`. Never infer Zentao success from a local plan; record the submitted result URL/status.

5. Release only after all selected bugs are `zentao_resolved` and the state says release was requested:

```powershell
python "$env:USERPROFILE\.codex\skills\asr360x-bug-delivery-orchestrator\scripts\delivery_state.py" release `
  --repo . --status released --evidence "uploaded release folder and verified artifacts"
```

6. Resume with `status`; do not repeat completed external actions:

```powershell
python "$env:USERPROFILE\.codex\skills\asr360x-bug-delivery-orchestrator\scripts\delivery_state.py" status --repo .
```

## Commit Gate

Before each commit:

- confirm branch, `HEAD`, and dirty files;
- stage only the current bug's files;
- run `git diff --cached --check` and targeted verification;
- use a Chinese subject that states the behavior change;
- record the resulting short SHA in delivery state.

## Final Report

Return one row per bug:

```text
ID | 当前阶段 | 修改 | 验证 | 提交 | 记忆 | 禅道
```

Then state release status, remaining blockers, and the local state file path.
