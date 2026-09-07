---
name: asr360x-bug-delivery-orchestrator
description: Coordinate explicit multistage ASR360x bug delivery or an ordered list of selected Bugs, with one active Bug and reused specialist receipts. Use for 修复提交关禅道出版本 or ordered multi-bug work. Single-Bug lookup/fix belongs to firmware triage; fetching lists or a bare Bug ID belongs to zentao-bug-triage.
---

# ASR360x Bug Delivery Orchestrator

Own requested stage order, compact progress, and handoffs. Specialists own diagnosis, implementation, verification, and external actions.

## Choose The Route

| Request | Route |
| --- | --- |
| One Bug: existence, explanation, evidence, or fix | asr3601-lvgl-firmware-triage directly; no delivery state |
| List/fetch Bugs or a bare ID without detail | zentao-bug-triage |
| Explicit composite delivery or ordered selected Bugs | Coordinate the authorized stages below |
| Status or resume of an existing delivery | Read its state and continue only incomplete authorized stages |

Infer scope from the full request and reuse prior authorization. Generic completion wording does not add commits, Zentao writes, releases, or branch changes.

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

For commitless composite work, keep in-task receipts and perform only requested stages. In an existing ordered delivery, use the documented finish path for a diagnosed already-fixed, no-change, or external outcome; do not invent a commit or fix note. Preserve legacy states and their requested terminal stage; schema version 3 adds these outcomes without satisfying remote resolution from local classification alone.

After an interruption, read status and check evidence for the incomplete stage before retrying an external action. An unexpected checkout/HEAD change invalidates the task snapshot. A wrong-product resolution stops release progression; use the resolver's corrective path only with the applicable authorization.

## Result

Return one compact row per Bug: stage, change, verification, commit state, memory target, and Zentao status. Add release outcome, blockers/device debt, and the state path if one exists. Quick Release success needs only the requested Bug/commit result, released version, and destination; derive these from the controller result.
