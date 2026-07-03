---
name: skill-usage-tracker
description: Track Codex skill usage counts, official OpenTelemetry skill-injection data, 7/30 day trends, unused-skill cleanup suggestions, and lightweight post-use feedback by importing local OTLP captures or scanning local session logs into SQLite. Use when the user asks for skill usage statistics, official telemetry, trend reports, cleanup candidates, wants to record feedback for a skill/turn, asks which skills are frequently or rarely used, or asks how feedback is attributed when multiple skills are used in one turn.
---

# Skill Usage Tracker

Use this skill to inspect or update local skill-usage telemetry. It is intentionally local-only:

- Prefer official Codex OpenTelemetry when `%USERPROFILE%\.codex\skill-usage\otel\otlp.jsonl` exists.
- Reads Codex session JSONL files under `%USERPROFILE%\.codex\sessions` and `%USERPROFILE%\.codex\archived_sessions`.
- Writes a local SQLite database under `%USERPROFILE%\.codex\skill-usage\usage.sqlite`.
- Does not send telemetry anywhere.

## Stable Trigger Model

This skill does not rely on another skill magically firing after every skill use. Codex skills are prompt-time instructions, not guaranteed background listeners.

The reliable path is:

1. Start the local OTLP receiver when official Codex OpenTelemetry is enabled.
2. Import official non-failure `skill.injected` metrics/logs from the local OTLP JSONL capture.
3. Fall back to scanning session logs for older history or when no OTLP capture exists.
4. Store detected usage events in SQLite.
5. Ask for lightweight feedback only when useful.
6. Attribute overall feedback to the turn; attribute feedback to a specific skill only when the user says which skill helped or was unnecessary.

## Commands

Run from any working directory:

```powershell
python C:\Users\84365\.codex\skills\skill-usage-tracker\scripts\skill_usage_tracker.py report
```

Useful commands:

```powershell
python C:\Users\84365\.codex\skills\skill-usage-tracker\scripts\skill_usage_tracker.py scan
python C:\Users\84365\.codex\skills\skill-usage-tracker\scripts\skill_usage_tracker.py report
python C:\Users\84365\.codex\skills\skill-usage-tracker\scripts\skill_usage_tracker.py trends
python C:\Users\84365\.codex\skills\skill-usage-tracker\scripts\skill_usage_tracker.py otel-serve
python C:\Users\84365\.codex\skills\skill-usage-tracker\scripts\skill_usage_tracker.py latest
python C:\Users\84365\.codex\skills\skill-usage-tracker\scripts\skill_usage_tracker.py pending
python C:\Users\84365\.codex\skills\skill-usage-tracker\scripts\skill_usage_tracker.py feedback --rating useful --note "PDF skill helped; browser was unnecessary" --best pdf --unneeded browser
```

Source selection:

```powershell
python C:\Users\84365\.codex\skills\skill-usage-tracker\scripts\skill_usage_tracker.py report --source official
python C:\Users\84365\.codex\skills\skill-usage-tracker\scripts\skill_usage_tracker.py report --source logs
python C:\Users\84365\.codex\skills\skill-usage-tracker\scripts\skill_usage_tracker.py report --source both
```

For a specific turn:

```powershell
python C:\Users\84365\.codex\skills\skill-usage-tracker\scripts\skill_usage_tracker.py feedback --turn <turn_id> --rating ok --skill pdf=useful --skill browser=unneeded
```

## Feedback Rules

When one turn uses one skill:

- Usage count increments for that skill.
- Overall feedback can be treated as turn feedback.
- If the user explicitly rates the skill, record direct skill feedback too.

When one turn uses multiple skills:

- Usage count increments once per detected skill event.
- Overall feedback belongs to the turn.
- Do not average or copy the overall rating to every skill.
- Only record skill-level feedback for skills the user explicitly names, such as `--best pdf`, `--unneeded browser`, or `--skill pdf=useful`.

This avoids giving credit to unrelated skills just because they appeared in the same answer.

## Reporting

Prefer concise reports by default. Include:

- Most used skills.
- Rarely used or unused skills.
- Official non-failure `skill.injected` counts when local Codex OTel capture is available.
- 7/30 day trend report with stale or never-used skill cleanup suggestions.
- Recent usage.
- Direct skill feedback counts when available.
- Note that usage counts are estimates based on local logs.
