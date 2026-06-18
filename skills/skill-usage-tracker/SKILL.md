---
name: skill-usage-tracker
description: Track Codex skill usage counts and lightweight post-use feedback by scanning local session logs and writing a local SQLite database. Use when the user asks for skill usage statistics, wants to record feedback for a skill/turn, asks which skills are frequently or rarely used, or asks how feedback is attributed when multiple skills are used in one turn.
---

# Skill Usage Tracker

Use this skill to inspect or update local skill-usage telemetry. It is intentionally local-only:

- Reads Codex session JSONL files under `%USERPROFILE%\.codex\sessions` and `%USERPROFILE%\.codex\archived_sessions`.
- Writes a local SQLite database under `%USERPROFILE%\.codex\skill-usage\usage.sqlite`.
- Does not send telemetry anywhere.

## Stable Trigger Model

This skill does not rely on another skill magically firing after every skill use. Codex skills are prompt-time instructions, not guaranteed background listeners.

The reliable path is:

1. Run the scanner to detect usage from session logs.
2. Store detected usage events in SQLite.
3. Ask for lightweight feedback only when useful.
4. Attribute overall feedback to the turn; attribute feedback to a specific skill only when the user says which skill helped or was unnecessary.

## Commands

Run from any working directory:

```powershell
python <CODEX_HOME>\skills\skill-usage-tracker\scripts\skill_usage_tracker.py report
```

Useful commands:

```powershell
python <CODEX_HOME>\skills\skill-usage-tracker\scripts\skill_usage_tracker.py scan
python <CODEX_HOME>\skills\skill-usage-tracker\scripts\skill_usage_tracker.py report
python <CODEX_HOME>\skills\skill-usage-tracker\scripts\skill_usage_tracker.py latest
python <CODEX_HOME>\skills\skill-usage-tracker\scripts\skill_usage_tracker.py pending
python <CODEX_HOME>\skills\skill-usage-tracker\scripts\skill_usage_tracker.py feedback --rating useful --note "PDF skill helped; browser was unnecessary" --best pdf --unneeded browser
```

For a specific turn:

```powershell
python <CODEX_HOME>\skills\skill-usage-tracker\scripts\skill_usage_tracker.py feedback --turn <turn_id> --rating ok --skill pdf=useful --skill browser=unneeded
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
- Recent usage.
- Direct skill feedback counts when available.
- Note that usage counts are estimates based on local logs.
