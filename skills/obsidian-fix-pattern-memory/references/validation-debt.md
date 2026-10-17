# Validation Debt And Campaign Modes

Read this file only for explicit validation-debt, Campaign, release-readiness, or
open-loop reconciliation requests.

## State Meanings

- `BLOCKED` and `DEVICE_VERIFICATION_PENDING` remain unresolved validation debt.
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
