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
