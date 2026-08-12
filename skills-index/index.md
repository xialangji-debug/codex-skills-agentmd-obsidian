# Codex Skill Index

Use this index only when skill routing is unclear, a named skill is not visible in `available skills`, or the user asks to organize skills.

| Request | Read next |
|---|---|
| 360x firmware bug triage, bug existence, cross-branch fixes | `firmware/index.md` |
| Zentao bug fetching, selected bug details, bug resolving | `zentao/index.md` |
| Protocol documents, APP/mini-app/vendor/platform questions | `protocol/index.md` |
| CATStudio logs, crash/log evidence packs | `logs/index.md` |
| Firmware release, fnOS upload, build/package release | `release/index.md` |
| Obsidian fix-patterns, memory updates | `memory/index.md` |
| Archived or disabled skills | `archive/index.md` |
| Explicit local-model implementation inside allowlisted projects | `local-coder-executor`; primary Codex plans and reviews |
| Skill registry drift, stale routes, trigger failures | Run active `skill-usage-tracker` command `registry-audit`, then read this index only if routing remains unclear |

Keep specialist skills flat under `%USERPROFILE%\.codex\skills`. Primary Codex coordinates multi-step work by invoking the owning global Skill for each operation.
