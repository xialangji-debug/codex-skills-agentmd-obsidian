# Fix-Pattern Maintenance Operations

Read this file only for explicit maintenance, migration, validation, domain
correction, or cross-project candidate work. Do not run these commands after an
ordinary fix record.

## Validate And Migrate

Preview legacy migration first:

```powershell
python -X utf8 "$env:USERPROFILE\.codex\skills\obsidian-fix-pattern-memory\scripts\fix_memory.py" migrate
python -X utf8 "$env:USERPROFILE\.codex\skills\obsidian-fix-pattern-memory\scripts\fix_memory.py" validate
```

Use `migrate --write` only after reviewing its exact candidates. Migration adds
managed identity/state fields; it must not invent historical branches or
verification.

## Domain Audit

```powershell
python -X utf8 "$env:USERPROFILE\.codex\skills\obsidian-fix-pattern-memory\scripts\fix_memory.py" audit-domains --only-domain esp32
```

Review every proposed correction before adding `--write`. Managed project keys
and explicit firmware-family evidence are stronger than filenames; leave neutral
or ambiguous notes unchanged.

## Cross-Project Candidates

```powershell
python -X utf8 "$env:USERPROFILE\.codex\skills\obsidian-fix-pattern-memory\scripts\fix_memory.py" candidates --note <canonical.md>
```

This is read-only. It lists unassessed active-project targets and never claims
the root cause exists there, switches branches, or authorizes edits.

## Legacy Tools

`new_fix_pattern.py` and `memory_trust.py` are compatibility tools. Use
`fix_memory.py` for new writes and events.
