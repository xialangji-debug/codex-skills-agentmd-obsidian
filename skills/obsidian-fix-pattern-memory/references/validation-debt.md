# Validation Debt And Campaign Modes

Read this file only for explicit validation-debt, Campaign, release-readiness, or
open-loop reconciliation requests.

## State Meanings

- `BLOCKED` and `DEVICE_VERIFICATION_PENDING` remain unresolved validation debt.
- `FUNCTIONAL_VERIFICATION_PENDING` means tool/document/platform acceptance is still pending;
  `ACCEPTANCE_SCOPE_PENDING` means the evidence object is not yet identified. Both remain blocked.
- `READY_FOR_QA` means the required device/platform evidence exists and only QA
  closure remains.
- `COMPLETE` means the requested evidence layers are complete.

Campaign mode groups managed targets by domain, project, branch, version, and
variant. Legacy notes remain isolated by source.

## Reviewed Historical Work Items

The default report omits `lifecycle: deprecated/archived` notes and exact targets
listed in `Codex/agent/validation-history-review.json` whose note and target
SHA-256 fingerprints still match. This optional, user-reviewed register controls
work-list visibility only; canonical implementation/verification/Zentao states
remain owned by the fix notes. Do not create or renew register entries during
routine fix recording. Any note or target change invalidates its old decision.
Failed, reactivated, unverified, and needs-review targets cannot be hidden by it.

Use `--include-history` to inspect the full evidence debt, including historical
work-list decisions and retired records. Never describe filtered-out items as
new device/platform/QA passes. An empty managed target list still uses explicit
legacy verification text, so identity-only migration cannot silently erase debt.

```powershell
python -X utf8 "$env:USERPROFILE\.codex\skills\obsidian-fix-pattern-memory\scripts\validation_debt_report.py" --domain asr --project lt52 --branch release --since 2026-08-01 --campaign
```

For open-loop reconciliation, produce a standalone delta:

```powershell
python -X utf8 "$env:USERPROFILE\.codex\skills\obsidian-fix-pattern-memory\scripts\validation_debt_report.py" --campaign --open-loops "$env:USERPROFILE\Documents\Obsidian\CodexVault\Codex\agent\open-loops.md" --open-loops-delta "$env:TEMP\validation-open-loops-delta.md"
```

Only machine-marked validation-debt entries participate. Human-authored unmarked
items remain untouched. Counts distinguish root-cause notes from exact target
rows.

## Work identity and validation scope

Machine work-item markers use `v2-<sha256>` over `(fix_id, target_id)`; legacy
records use source filename when no fix identity exists. Renaming a managed note
does not change its work identity. A target id alone is not a unique root cause.
Old unambiguous markers get migration suggestions; ambiguous markers list every
candidate and never select one silently. A missing item after filtering is not
proof of completion. Duplicate composite identities fail delta generation.

Scope selectors live in [validation-policy.json](validation-policy.json).
Rules are evaluated in order; fields in one rule are AND, patterns within a field
are OR, using case-insensitive shell globs. An alternate policy can be selected
with `--validation-policy <path>`. Tooling areas and configured control projects
precede firmware domains. Unknown scopes remain pending; `domain=none` does not
mean complete. This changes report wording and readiness only, never evidence.
Legacy explicit verification text remains authoritative and is not reinterpreted.
Failed/reactivated states always require review even if an older state says QA passed.

Use `--overview` for a concise current work view. It reads the enabled repositories
in `~/.codex/active-projects.json` (override with `--active-projects`) and their live
Git branches. `--current-branches` filters the full report by those branches and
fails if a repository cannot be read or is detached. A branch match is navigation,
not device identity or proof of a reproduced defect. Reports never rewrite the
canonical open-loops page automatically. Invalidated historical decisions may be
preserved under `superseded_entries`; only `entries` participates in filtering.
