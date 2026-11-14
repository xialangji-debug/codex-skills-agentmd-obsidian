---
name: asr360x-bug-delivery-orchestrator
description: Coordinate explicitly ordered ASR360x Bugs, continuous repair/commit loops, or status and resume of an existing delivery. Keep one active Bug and reuse specialist receipts. Use for 按顺序修这几个Bug, 一直修复并提交, or 继续已有交付. New single-Bug composite work uses its specialist owners directly; list/next-Bug queries belong to zentao-bug-triage.
---

# ASR360x Bug Delivery Orchestrator

Own requested stage order, compact progress, and handoffs. Specialists own diagnosis, implementation, verification, and external actions.

## Choose The Route

| Request | Route |
| --- | --- |
| One Bug: existence, explanation, evidence, or fix | asr3601-lvgl-firmware-triage directly; no delivery state |
| New single-Bug composite request, such as 修复提交关禅道出版本 | The calling agent sequences the requested specialist owners directly and reuses their receipts |
| List/fetch Bugs or a bare ID without detail | zentao-bug-triage |
| Ordered selected Bugs or an explicit continuous repair/commit loop | Coordinate the authorized stages below |
| Status or resume of an existing delivery, including a legacy single-Bug delivery | Read its exact state and continue only incomplete currently authorized stages |

Infer scope from the full request and reuse prior authorization. Generic completion wording does not add commits, Zentao writes, releases, or branch changes.

Before the next action, use the latest request's target, selected Bugs, Git mode,
release/upload scope, and whether continuous repair remains authorized. Keep this
as a compact in-task scope statement. When the user changes it, apply
[current scope](references/current-scope.md); historical state is evidence, not a
replacement for the current request.

`查下一个` is navigation through zentao-bug-triage. `修复并提交，然后查下一个`
finishes the current Bug and investigates the next; it does not authorize repairing
the next one. Explicit `一直修复并提交，然后查下一个` authorizes the corresponding
ordered loop. Reuse this delivery's progress for navigation; do not create a second
queue or infer authority from an old state after the user narrows the request.

## Delivery Loop

1. Reuse one current project snapshot, build configuration, and release owner. Refresh missing or stale identity only where a stage needs it; a controller owns its checks.
2. Keep one active Bug. Fetch only that Bug's required detail/attachments, then hand to triage or porting. Reuse already-fetched evidence.
3. Accept the owner's diagnosis, diff, narrow verification, and memory receipt. Do not repeat those steps through another Skill. Share project identity and build caches across Bugs, never hypotheses, raw evidence, changed-file scope, or verification claims.
4. Perform requested commits with exact Bug paths and a focused Chinese subject. Check the current diff and staged diff before committing; retain unrelated work. Update the expected HEAD after the workflow's own commit.
5. Send selected IDs and exact-target fix receipts to zentao-bug-resolver only when resolution is authorized. The resolver owns live product/status/form checks. 已解决 remains QA pending.
6. Finish the active Bug's requested stages before loading the next Bug. Run one final integrated build if needed, or reuse the requested release controller's build evidence.
7. Hand release directly to the project-confirmed owner after selected Bugs finish. Formal/FOTA-test pairs use asr3602-fota-pair-release; no earlier standalone full build and no generic delivery_transaction.py probe without an established project profile.

For 快速出版本, preserve the modifier: one confirmed owner-controller call, no external preflight/post-success checks. If it fails or is ambiguous, report the stage, exact error, known side effects, and needed decision, then wait. Earlier delivery stages retain their own authorization boundaries.

## Persistent State

Use [delivery state](references/delivery-state.md) when per-Bug commits are explicitly part of the request and resumable state is needed. The existing stage sequence includes committed; do not fabricate a commit or stage to fit a narrower request.

For commitless ordered work, keep in-task receipts and perform only requested stages. In an existing delivery, use the documented finish path for a diagnosed already-fixed, no-change, or external outcome; do not invent a commit or fix note. Legacy states retain their original terminal stage until an explicit scope change. New states default to memory_decided; selecting zentao_resolved requires the user's resolution scope. Use the existing state's narrow command to withdraw pending work, keeping completed actions and evidence intact.

After an interruption, read status and check evidence for the incomplete stage before retrying an external action. An unexpected checkout/HEAD change invalidates the task snapshot. A wrong-product resolution stops release progression; use the resolver's corrective path only with the applicable authorization.

## Result

Return one compact row per Bug: stage, change, verification, commit state, memory target, and Zentao status. Add release outcome, blockers/device debt, and the state path if one exists. Quick Release success needs only the requested Bug/commit result, released version, and destination; derive these from the controller result.
