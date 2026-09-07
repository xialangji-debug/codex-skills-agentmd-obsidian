---
name: obsidian-fix-pattern-memory
description: Search or maintain canonical Obsidian fix-patterns and exact-target evidence, or report validation debt and Campaigns. Use for 读取记忆库, 根据记忆, 记一下, behavior-changing fixes, regression lookup, evidence/status updates, 待真机, 验证债务, 待回归, Campaign, or 发布前验收清单. Routine recording uses one direct path; reporting and maintenance are explicit modes.
---

# Obsidian Fix-Pattern Memory

Canonical notes live under:

```text
%USERPROFILE%\Documents\Obsidian\CodexVault\Codex\fix-patterns
```

Use `scripts/fix_memory.py` as the only canonical-note writer. Never use Basic Memory MCP or
invent a second state schema.

## Fast Record Path

After a behavior-changing fix, consume the current Bug receipt:

1. If the receipt already records this fix and verification in an exact canonical
   target, reuse it without another write. For new evidence, call `upsert --note`
   or the matching `event` once on that note. Do not search again.
2. If `memory_target` is empty, search `fix-patterns/` once with one to three
   root-cause, symbol, or symptom terms.
3. Update one high-confidence root-cause match. If none exists, create one note.
   Keep ambiguous roots separate instead of merging by project/customer name.
4. Stop after the write. Do not run full `validate`, migration, domain audit, or
   cross-project candidates during routine recording.

```powershell
python -X utf8 "$env:USERPROFILE\.codex\skills\obsidian-fix-pattern-memory\scripts\fix_memory.py" upsert --note <canonical.md> --repo . --bug <id> --implementation applied --verification <level> --write
```

For a new root cause, include title, slug, keywords, scope, symptoms, root cause,
key files/functions, fix, verification method, and explicit
`--domain asr|esp32|none`. The script requires the knowledge fields before it
writes a new note.

## Lookup Path

For explicit memory lookup, regression, similar issue, or cross-branch work,
search only `fix-patterns/` with one to three precise terms and read at most three
genuine matches. A high-confidence match needs compatible symptoms/root cause or
code symbols; project, branch, device, or customer text alone is insufficient.

`读取记忆` or `根据记忆` authorizes lookup only. A later behavior fix follows the
Fast Record Path.

## Evidence Event Path

Update only the exact target row:

```powershell
python -X utf8 "$env:USERPROFILE\.codex\skills\obsidian-fix-pattern-memory\scripts\fix_memory.py" event --note <canonical.md> --repo . --bug <id> --event <event> --evidence "<evidence>" --write
```

Build/static evidence never becomes device/platform/QA verification. `resolved`
means development-resolved and QA-pending; only `closed` or equivalent explicit
QA evidence supports `qa_verified`. Reactivation downgrades only the exact target
with the materially same symptom.

## Validation Debt Reports

For pending device/platform/QA checks or Campaigns, run the read-only report:

```powershell
python -X utf8 "$env:USERPROFILE\.codex\skills\obsidian-fix-pattern-memory\scripts\validation_debt_report.py" --fix-patterns "$env:USERPROFILE\Documents\Obsidian\CodexVault\Codex\fix-patterns" [filters]
```

Use project/branch/version/domain filters and `--campaign` for the requested
scope. Read [validation debt](references/validation-debt.md) for grouping,
readiness meanings, or open-loop reconciliation. Write a draft/delta only to an
explicitly requested standalone path; do not rewrite canonical open-loops.
Reporting does not trigger ordinary fix recording or upgrade evidence.

## Write Boundary

Record completed behavior-changing code, configuration, or resource fixes. Do
not auto-record explanation-only work, comments/formatting, reverted experiments,
temporary diagnostics, unrelated environment cleanup, or anything the user says
not to record. Never save credentials, full chats, large logs, or private account
data.

After a write, report the note path, `fix_id`, exact target state, evidence level,
and whether any other targets remain candidates.

Read [fix record schema](references/fix-record-schema.md) only when interpreting
identity/state transitions. Read [maintenance operations](references/maintenance.md)
only for migration, validation, domain correction, or cross-project candidate
audits.
