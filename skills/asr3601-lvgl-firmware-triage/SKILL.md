---
name: asr3601-lvgl-firmware-triage
description: Investigate or fix one current-branch ASR360x/Crane/LVGL issue, or independently maintain protocol references and compare branch support. Use for 有没有这个问题, 先判断再修, 修复完了吗, 重新验证, UI changes, feature-closure audits, 导入协议, 更新协议, APP/小程序/YL/AKQ 协议核对, 上报合规, or 协议支持矩阵. Protocol work does not require a Bug. Cross-branch ports, ordered multi-bug work, and validation-debt Campaigns use their owners.
---

# ASR3601 LVGL Firmware Triage

Own one issue from evidence through the authorized fix and its verification, or
the standalone protocol mode below. Use the established project route; do not
repeat project classification or add an intake handoff.

## Protocol Documents And Support

For `导入协议`, protocol-file updates, protocol compliance, firmware/platform
attribution, or branch-support/matrix questions, go directly to
[protocol evidence](references/protocol-evidence.md). This mode preserves raw
documents, extracted text, source hashes, index, and support matrix in the work
Vault. It does not require a Bug, a fix, or build-profile preparation. Read only
the current identity/source needed for an actual branch comparison, then return
the requested document update or protocol conclusion.

## Entry And Evidence

1. Reuse the task's route and current snapshot. Otherwise read project AGENTS/index and only the local context the task needs.
2. For a source question, inspect live source directly. Before an edit, capture branch, HEAD, and dirty state once if not already current. Preserve unrelated changes and excluded variants.
3. Inspect supplied screenshots, videos, logs, documents, or artifacts first. Extract the trigger, actual result, expected result, and affected state for this Bug only.
4. Use scoped rg for known symbols, filenames, text, fields, or errors. For an unknown call relationship use the project code index. Run index health checks only after a failure or evidence of stale results.
5. Trace entry -> guard/state -> update -> storage/resource -> side effect; inspect both UI creation and refresh paths. Confirm index hits in live source. Expand when evidence conflicts, state has multiple writers, or the requested known-good comparison requires it.
6. During Bug investigation, check related existing fixes before the final diagnosis or choosing a fix. Reuse the selected-Bug candidate receipt when present. Otherwise search fix-patterns with 1-3 precise symptom/root-cause/symbol terms and read at most three direct matches. Follow the [candidate assessment procedure](../zentao-bug-triage/references/fix-candidates.md); concrete source-target comparisons belong to asr3601-cross-branch-porting. Do not run this lookup for an ordinary source explanation.
7. State 存在 / 当前已修 / 未确认 with decisive evidence, plus the candidate assessment or bounded no-match result. A lookup-only request ends with that answer. An authorized fix continues below without another approval.

Use catstudio-log-extractor for CATStudio packages; read [protocol evidence](references/protocol-evidence.md) when the active protocol or responsibility is unresolved. Reuse the Bug candidate lookup above; other memory lookup applies to explicit memory requests, similar/regression/cross-version cases, or a clearly identified log/error. Stop on no match.

## Fast Fix

Use this path for one concrete current-branch fix. Keep a compact in-task record of Bug, evidence, checkout, affected files, and expected behavior.

For feature removal, storage reduction, or a single-Flash conversion, apply
[feature preservation](references/feature-preservation.md) before editing and at
completion. For image/font/resource-index/build-rule or UI layout changes, apply
[resource delivery](references/resource-delivery.md). Load only the matching
reference; carry its short result in the same fix receipt.

1. Apply the smallest target-native fix. Reuse local helpers, LVGL v7 conventions, resource/text IDs, and multilingual layout rules. Check relevant state priority, callbacks, object lifetime, configured resolution, and persistence.
2. Review this Bug's diff and run git diff --check plus the narrowest meaningful project test or build. Reuse passing evidence unless a change, failure, or unresolved concern invalidates it.
3. For an immediate formal/FOTA-test pair, perform source-level checks before the focused authorized commit; the pair controller supplies the two full builds. Claim build_passed only after they succeed.
4. Commit only when requested, using this Bug's exact paths. Scope beyond a few files warrants an explanation, not an automatic stop. Branch changes, devices, releases, or remote writes go to their owner when authorized.
5. After a qualifying behavior-changing fix, use obsidian-fix-pattern-memory once and pass its note/fix_id/target_id to the caller. Keep static/build evidence separate from device/platform/QA acceptance.

Do not start a second closeout workflow after these checks. Share project identity with a later Bug, but keep diagnosis, attachments, diff, and verification separate.

Keep the complete fix receipt for downstream owners, including commit and memory target metadata. The user-facing Chinese result should cover the conclusion, key changes, actual verification, and material gaps; show internal metadata only when it helps the next action or is requested.

## Conditional Modes

- Explicit closeout or re-verification: read [closeout](references/closeout.md). Reuse the existing receipt; do not repeat Fast Fix by default.
- User test feedback on an existing fix: use `obsidian-fix-pattern-memory` User Test Feedback with the matching receipt. Reuse its target rather than re-running intake or inferring the tested package from the current checkout.
- Validation debt, pending device checks, or Campaign: use `obsidian-fix-pattern-memory` reporting mode.
- Reference UI: read [UI and feature modes](references/advanced-modes.md) when rebuilding a UI from a reference.
- Feature Closure: read the same reference for an audit of hidden menus, removed customer features, runtime reporting, or compatibility-retained IDs. Audits are read-only unless edits are authorized.
- Recurring implementation pattern: load [project patterns](references/project-patterns.md) only when the issue matches.
- Source-target comparison or migration: use asr3601-cross-branch-porting.
- Explicit ordered multi-bug, continuous repair, or an existing delivery resume: pass the receipt to asr360x-bug-delivery-orchestrator; do not redo intake. For a single-Bug composite request, the primary agent calls the requested commit, Zentao, build, or release owners directly and reuses this receipt.
