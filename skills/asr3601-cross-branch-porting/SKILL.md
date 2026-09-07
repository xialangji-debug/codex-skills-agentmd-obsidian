---
name: asr3601-cross-branch-porting
description: Compare or port ASR360x/Crane/LVGL firmware changes between explicit source and target branches, versions, or sibling projects. Use for 移植, source-versus-known-good regression comparison, ordered cherry-picks, 创建整合分支, or 冲突就停. A single current-branch bug without a source-target comparison belongs to firmware triage.
---

# ASR3601 Cross-Branch Porting

Own source-target comparison, target-native adaptation, and target verification. Reuse a triage receipt when present; do not choose a second independent fix.

## Establish The Comparison

Infer source, target, defect/feature, exclusions, and validation from the request and workspace. Capture source/target repo, branch, commit, dirty state, version, and the chip/OS/protocol/product/build facts relevant to compatibility. Reuse current snapshots and confirm uncertain facts in source; a product name alone does not establish a protocol. Zentao identity is needed only for Zentao work.

Before a branch/worktree switch, report the current and target checkout plus related dirty state and obtain the required switch authorization. An already explicit approval for that switch is reusable. Do not modify unselected projects.

For a similar fix, regression, or port, search only work fix-patterns with 1-3 terms and read direct matches. Stop on no match. Memory suggests candidates; current target code decides applicability.

## Semantic Port

1. Inspect source artifacts and the target's existing path. For a known commit, check ancestry and use git show/diff/blame as appropriate to the requested comparison.
2. Identify what is already present, directly transferable, requires adaptation, or is outside scope. Before a substantial patch, explain behavioral/interface differences, dependencies, excluded variants, and the proposed validation.
3. Apply only target-relevant changes. Preserve LVGL v7/local helpers, variant guards, resource and language IDs, screen dimensions, page registration, build macros, and compatibility contracts.
4. Check all relevant paths: UI creation/refresh/resource registration, or parse/storage/events/timers/reboot as the behavior requires. Avoid copying debug-only or unrelated source changes.
5. Inspect required new files with git status. Protect source/resources from a clean/release flow; stage them only when authorized. Stop a destructive cleanup that would erase required untracked input.
6. Run diff checks and the target's narrow meaningful validation. For immediate FOTA-pair delivery, let the pair builds provide full build evidence. State unavailable build/device validation precisely.
7. Use obsidian-fix-pattern-memory once for each completed behavior-changing root-cause port, adding this exact target to the canonical note. Pass the receipt forward; do not copy the note schema or rerun closeout.

Report what was ported/adapted/excluded, source and target, impact, verification, commit/staging state, memory target, and remaining risk. List further active-project candidates only when asked.

## Ordered Integration

Read [ordered integration](references/ordered-integration.md) only for an explicit ordered commit integration. The helper requires a clean worktree and stops at the first conflict. Semantic adaptation above remains necessary when source and target behavior differ.
