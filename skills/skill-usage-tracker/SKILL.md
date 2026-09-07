---
name: skill-usage-tracker
description: Audit local Skill registrations and routing, or report explicitly requested usage, trends, and feedback. Use for skill 整理, 触发不到, 索引同步, 失效/重复技能, frontmatter problems, or skill usage statistics. Registry maintenance does not require session-log scanning or telemetry setup.
---

# Skill Usage Tracker

## Choose One Operation

| Request | Operation |
| --- | --- |
| Registration, routing, duplicates, disabled Skills, frontmatter | Read-only registry audit below |
| Usage counts, trends, recent activity, or feedback | Read [usage and telemetry](references/usage-telemetry.md) |
| Enable local telemetry collection | Read the same reference and use only the requested setup |

## Registry Audit

Run before changing registrations or routing:

```powershell
python "$env:USERPROFILE\.codex\skills\skill-usage-tracker\scripts\skill_usage_tracker.py" registry-audit --strict --json
```

This reads registrations and indexes without applying suggestions. Review missing/stale routes, duplicate or invalid directories, frontmatter errors, and active skills omitted from the index. Distinguish active personal, system, disabled, and plugin-cache entries. A cache match is only a candidate until the current available-skills list exposes its prefixed name.

The report separates registered personal/system Skills, disabled folders, plugin
cache candidates, and session-visible names. Without --available-names-file,
session exposure is unknown. The legacy active and plugins_or_available fields
remain compatibility totals, not session-capability counts.

Optional inputs: --active-root, --disabled-root, --index, --available-names-file,
--retired-skills, and --archive-index. By default, archive inventory is checked
against retired-skills.yaml and skills-index/archive/index.md beside the active
root when either exists. The Archived Entries table must match recoverable
folders; historical removals belong in a separate section.

Keep active personal Skills flat under .codex/skills and inactive ones under .codex/skills.disabled. Update the owning routing indexes with any authorized rename/move. Do not delete or disable a Skill from low usage alone.

After edits, run the registry audit again. Report actual registration/route problems and changes; do not present plugin-cache totals as active capabilities.
