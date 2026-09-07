# Local Usage And Telemetry

Read this file for usage statistics, trends, feedback, or explicitly requested collection setup. Registry-only work does not need telemetry or session logs.

## Query Before Import

```powershell
python "$env:USERPROFILE\.codex\skills\skill-usage-tracker\scripts\skill_usage_tracker.py" report
python "$env:USERPROFILE\.codex\skills\skill-usage-tracker\scripts\skill_usage_tracker.py" trends
python "$env:USERPROFILE\.codex\skills\skill-usage-tracker\scripts\skill_usage_tracker.py" latest
python "$env:USERPROFILE\.codex\skills\skill-usage-tracker\scripts\skill_usage_tracker.py" pending
```

These query the local SQLite database by default. Add --scan only when a fresh incremental import is needed. Use --source official, logs, or both to select evidence. Actual reads/injections/tool calls are the default; --include-inferred also shows lower-confidence command/name evidence.

Prefer existing official non-failure skill.injected OTel records at .codex/skill-usage/otel/otlp.jsonl. The fallback scanner reads .codex/sessions and .codex/archived_sessions and stores events/byte offsets in .codex/skill-usage/usage.sqlite. It ignores injected catalogs/base instructions/tool descriptions and detects actual plugin namespaces. Counts remain evidence-derived estimates.

## Collection

Skills are prompt-time instructions, not guaranteed background listeners. For explicitly requested OTel collection, use otel-serve with the existing local configuration. Do not start a receiver simply to report usage.

```powershell
python "$env:USERPROFILE\.codex\skills\skill-usage-tracker\scripts\skill_usage_tracker.py" scan
python "$env:USERPROFILE\.codex\skills\skill-usage-tracker\scripts\skill_usage_tracker.py" otel-serve
```

Use scan --since <ISO-timestamp> for first cursor migration when older history is already imported. Keep telemetry local; do not send logs elsewhere.

## Feedback And Reporting

Overall feedback belongs to the turn. Attribute it to a specific Skill only when the user names that Skill; do not copy one rating to all Skills used.

```powershell
python "$env:USERPROFILE\.codex\skills\skill-usage-tracker\scripts\skill_usage_tracker.py" feedback `
  --turn <turn-id> --rating ok --skill pdf=useful --skill browser=unneeded
```

Report requested counts, trends, recent usage, or direct feedback with the source and freshness. Treat rarely-used Skills as review candidates, not automatic deletion targets.
