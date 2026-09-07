---
area: system
domains: []
scope:
  - vault/codex
kind: skill-index
codex_access: manage
trust: working
lifecycle: active
---

# Codex Skills Index

Use the current task's exposed Skill descriptions and the project's `AGENTS.md`
or `.codex-project/index.md` to select an owner. When local routing is missing,
read the installed index at `%USERPROFILE%\.codex\skills-index\index.md` on
Windows or `$CODEX_HOME/skills-index/index.md` on other systems. If `CODEX_HOME`
is unset, its default is `$HOME/.codex`.

The public index is generated from `public-sync-manifest.json`. Do not maintain
a second Skill inventory or domain-index list in this Vault template. Read the
selected Skill's `SKILL.md` for its procedure.

System Skills, plugins, release controllers, and project-specific tools are
installed separately. Their availability comes from the current session and
project routing, not from this template.

After changing local Skill registrations, run:

```powershell
python -X utf8 "$env:USERPROFILE\.codex\skills\skill-usage-tracker\scripts\skill_usage_tracker.py" registry-audit
```
