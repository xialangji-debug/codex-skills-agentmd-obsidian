---
name: asr3601-lvgl-firmware-triage
description: Explain, verify, fix, or explicitly close out one current-branch ASR360x/Crane/LVGL firmware issue. Use for 有没有这个问题, 先判断再修, 修复完了吗, 重新验证, narrow bug fixes, reference UI changes, or feature-closure audits. Route cross-branch ports, multi-bug delivery, and validation-debt Campaigns to their owners.
---

# ASR3601 LVGL Firmware Triage

Own one issue from evidence through the authorized fix and its verification. Use the established project route; do not repeat project classification or add an intake handoff.

## Entry And Evidence

1. Reuse the task's route and current snapshot. Otherwise read project AGENTS/index and only the local context the task needs.
2. For a source question, inspect live source directly. Before an edit, capture branch, HEAD, and dirty state once if not already current. Preserve unrelated changes and excluded variants.
3. Inspect supplied screenshots, videos, logs, documents, or artifacts first. Extract the trigger, actual result, expected result, and affected state for this Bug only.
4. Use scoped rg for known symbols, filenames, text, fields, or errors. For an unknown call relationship use the project code index. Run index health checks only after a failure or evidence of stale results.
5. Trace entry -> guard/state -> update -> storage/resource -> side effect; inspect both UI creation and refresh paths. Confirm index hits in live source. Expand when evidence conflicts, state has multiple writers, or the requested known-good comparison requires it.
6. State 存在 / 当前已修 / 未确认 with decisive evidence. A lookup-only request ends with that answer. An authorized fix continues below without another approval.

Use catstudio-log-extractor for CATStudio packages; use the protocol owner when the active protocol or responsibility is unresolved. Search fix-patterns with 1-3 terms only for explicit memory requests, similar/regression/cross-version cases, or a clearly identified log/error. Read at most three direct matches and stop on no match.

## Fast Fix

Use this path for one concrete current-branch fix. Keep a compact in-task record of Bug, evidence, checkout, affected files, and expected behavior.

1. Apply the smallest target-native fix. Reuse local helpers, LVGL v7 conventions, resource/text IDs, and multilingual layout rules. Check relevant state priority, callbacks, object lifetime, configured resolution, and persistence.
2. Review this Bug's diff and run git diff --check plus the narrowest meaningful project test or build. Reuse passing evidence unless a change, failure, or unresolved concern invalidates it.
3. For an immediate formal/FOTA-test pair, perform source-level checks before the focused authorized commit; the pair controller supplies the two full builds. Claim build_passed only after they succeed.
4. Commit only when requested, using this Bug's exact paths. Scope beyond a few files warrants an explanation, not an automatic stop. Branch changes, devices, releases, or remote writes go to their owner when authorized.
5. After a qualifying behavior-changing fix, use obsidian-fix-pattern-memory once and pass its note/fix_id/target_id to the caller. Keep static/build evidence separate from device/platform/QA acceptance.

Do not start a second closeout workflow after these checks. Share project identity with a later Bug, but keep diagnosis, attachments, diff, and verification separate.

Return one compact receipt in Chinese: conclusion and cause, changes and impact, verification, commit or uncommitted state, memory target, and remaining device/platform debt.

## Conditional Modes

- Explicit closeout or re-verification: read [closeout](references/closeout.md). Reuse the existing receipt; do not repeat Fast Fix by default.
- Validation debt, pending device checks, or Campaign: use `obsidian-fix-pattern-memory` reporting mode.
- Reference UI: read [UI and feature modes](references/advanced-modes.md) when rebuilding a UI from a reference.
- Feature Closure: read the same reference for an audit of hidden menus, removed customer features, runtime reporting, or compatibility-retained IDs. Audits are read-only unless edits are authorized.
- Recurring implementation pattern: load [project patterns](references/project-patterns.md) only when the issue matches.
- Source-target comparison or migration: use asr3601-cross-branch-porting.
- Explicit ordered multi-bug or composite delivery: pass the receipt to asr360x-bug-delivery-orchestrator; do not redo intake.
