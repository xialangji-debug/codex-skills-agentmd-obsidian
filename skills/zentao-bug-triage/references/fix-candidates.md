# Repair candidates after Bug lookup

The snapshot's memory_linkage.js performs read-only clue discovery. It reuses the
canonical fix-pattern format owned by obsidian-fix-pattern-memory. The registry
is ~/.codex/active-projects.json; only enabled ASR projects supply managed source
targets. Keep project names and paths out of reusable matching rules.

## List versus selected Bug

A list query ends with compact candidates and lookup completeness. Do not open
every Bug's detail, inspect all repositories, or call a title match portable.
The score ranks text relevance only. It does not measure compatibility.

For a selected Bug, use its current steps, actual/expected behavior, attachments
and latest activation. Reuse the provided candidates. Read at most three directly
relevant canonical notes; prioritize shared root causes or exact symbols over
shared product names. No candidate is also a useful result, with bounded coverage.

## Source and target comparison

Use asr3601-cross-branch-porting for a concrete source-target comparison:

- Resolve the current target from live checkout evidence. Compare the candidate's
  exact source branch/commit and relevant code with that target, using git show,
  diff, log or blame without switching branches. Previously recorded branches
  remain useful even when another branch is now checked out.
- A committed row supplies a recorded commit to inspect, not proof that the
  commit contains the fix. An applied row may point to HEAD before an uncommitted
  fix; inspect the corresponding working changes or report the source unavailable.
- Check root cause, existing equivalent implementation, dependencies, protocol,
  chip/OS, build macros and product-specific contracts that affect this Bug.
  A missing target row in memory never proves the target lacks the repair.
- If memory has no useful match, use one to three precise symptom/symbol terms
  to search the relevant module or bounded local Git history in enabled sibling
  projects. Stop when those searches yield nothing; do not scan all branch code
  or fetch remotes automatically. Keep each Bug's evidence separate.

Return one of: 已有等效修复 / 可直接复用 / 需要适配 / 不适用 / 证据不足.
Include source project, branch and commit or working changes; matching reason;
target evidence; adaptations; and the recorded verification level. These labels
require source comparison and cannot come from the text matcher alone.

Keep static_checked, build_passed, device_verified, platform_verified and
qa_verified distinct. Failed, superseded, reactivated, needs_review and
not_applicable source targets cannot recommend a repair. Legacy prose is a clue
with unassessed provenance. Do not promote its wording to structured acceptance.

## Action boundary

Lookup and comparison do not change firmware, branches, canonical notes or
Zentao state. When a fix is already authorized, continue through the owning
implementation skill without asking again. Record an actual completed fix once
through obsidian-fix-pattern-memory. Do not turn every candidate into a new note
or validation-debt item.
