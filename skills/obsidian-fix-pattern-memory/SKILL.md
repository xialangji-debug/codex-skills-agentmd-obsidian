---
name: obsidian-fix-pattern-memory
description: Search, create, merge, and update canonical local Obsidian fix-pattern memory with per-project/branch/version target records and independent implementation, verification, and Zentao states. Use for 读取记忆库, 根据记忆, 记一下, every completed behavior-changing fix, 收工更新, similar issues, regressions, cross-branch reuse, device/platform/QA verification, automatic Zentao snapshot transitions, or reactivated bugs that must downgrade one exact target without erasing other verified targets.
---

# Obsidian Fix Pattern Memory

Use local Markdown directly. Never use Basic Memory MCP.

```text
%USERPROFILE%\Documents\Obsidian\CodexVault\Codex\fix-patterns
```

This skill is the only writer of canonical fix-pattern state. Other skills submit
target evidence or status events through `scripts/fix_memory.py`; they must not
invent separate note schemas.

## Lookup

1. Identify module, symptom/log words, files/functions, project family, branch,
   and version.
2. Search only `fix-patterns/` with one to three precise terms.
3. Read up to three genuine matches. Do not pad with unrelated notes or scan the
   whole vault.
4. Treat memory match confidence and repair eligibility as independent decisions.
5. A high-confidence match requires compatible symptoms/root cause or code symbols;
   project, branch, customer, or device text alone is insufficient.

“读取记忆/根据记忆” alone is read-only. If the same request then produces an
actual behavior fix, record that completed fix under the normal write policy.

## Automatic Write Boundary

Record every completed behavior-changing code, configuration, or resource fix,
including a Fast Fix. Static or build evidence creates a `working` target; it does
not claim device/platform/QA verification.

Do not auto-record:

- explanation or investigation without a fix;
- comments, formatting, generated churn, or pure documentation wording;
- reverted experiments or temporary diagnostics;
- software installation, cleanup, or local environment repair unrelated to product behavior;
- anything the user explicitly says not to record.

For a high-confidence same root cause, update the existing canonical note. For a
medium ambiguous match, keep a separate working note or ask before merging. Never
silently merge two different root causes.

## Canonical Model

Keep one full note per root cause:

- `fix_id`: stable root-cause identity.
- reusable symptoms, signatures, root cause, files/functions, fix, verification,
  and cautions.
- `reference_target`: strongest and newest eligible implementation.
- one concise target row per exact repo/branch/version/variant.
- Bug IDs and latest evidence on the matching target row.

The script stores only one-way `repo_id` and `variant_id` hashes in managed state;
it never stores an absolute repository path or username. See
`references/fix-record-schema.md` for fields and transitions.

Reference order:

```text
qa_verified > platform_verified > device_verified > build_passed
> static_checked > unverified
```

A newer weak target does not replace an older stronger reference. Reactivation of
the reference downgrades only that exact target and selects the next eligible one.

## Record A Fix

For a new root cause, provide actual knowledge fields and write the target state:

```powershell
python -X utf8 "$env:USERPROFILE\.codex\skills\obsidian-fix-pattern-memory\scripts\fix_memory.py" upsert `
  --repo . --title "UI state is not refreshed after an event" `
  --slug "ui-state-refresh-after-event" --bug 1001 `
  --keyword "refresh" --keyword "event" --scope "ASR firmware" `
  --symptoms "The page keeps the previous state after the event." `
  --root-cause "The state write path did not emit the existing refresh notification." `
  --key-file "gui/example.c:refresh_view" `
  --fix "Emit the existing notification after the state update." `
  --verification-method "diff check and target build; device regression still pending" `
  --verification build_passed --implementation applied --write
```

New written notes require `--symptoms`, `--root-cause`, and `--fix`. For an exact
existing match, pass `--note <path>` and only the fields that genuinely changed.

## Record Evidence Events

Use one exact note and current target context:

```powershell
python -X utf8 "$env:USERPROFILE\.codex\skills\obsidian-fix-pattern-memory\scripts\fix_memory.py" event `
  --note <fix-pattern.md> --repo . --bug 1001 --event device_verified `
  --evidence "target device regression passed" --write
```

Events:

```text
fixed, build_passed, committed, device_verified, platform_verified,
zentao_resolved, zentao_closed, reactivated_same, reactivated_variant,
not_applicable, superseded
```

`zentao_resolved` means QA pending. `zentao_closed` upgrades the exact target to
`qa_verified`. `reactivated_same` marks it `failed + needs_review`.
`reactivated_variant` never changes the old target automatically.

## Cross-Project Candidates

For “其他版本要不要一起改”, list only explicitly active projects:

```powershell
python -X utf8 "$env:USERPROFILE\.codex\skills\obsidian-fix-pattern-memory\scripts\fix_memory.py" candidates `
  --note <fix-pattern.md>
```

The command omits absolute paths and returns unassessed targets only. It does not
claim the root cause exists there and never switches or edits a project.

## Migration And Validation

Preview legacy notes first:

```powershell
python -X utf8 "$env:USERPROFILE\.codex\skills\obsidian-fix-pattern-memory\scripts\fix_memory.py" migrate
python -X utf8 "$env:USERPROFILE\.codex\skills\obsidian-fix-pattern-memory\scripts\fix_memory.py" validate
```

Use `migrate --write` only after reviewing the candidate list. Migration adds IDs
and an empty target matrix; it does not guess historical branches or verification.

`new_fix_pattern.py` and `memory_trust.py` remain legacy compatibility tools. Use
`fix_memory.py` for all new workflows.

## Privacy And Reporting

Keep live notes, snapshots, Bug data, project mappings, branches, customer names,
and service details local. Reusable repositories may contain only generic scripts,
schema documentation, and synthetic tests.

After a write, report the note path, `fix_id`, exact target state, evidence level,
and whether other targets are only candidates. If no write occurred, state the
specific exclusion reason.
