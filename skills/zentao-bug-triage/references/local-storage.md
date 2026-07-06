# Local Storage

Primary machine-readable cache:

```text
%USERPROFILE%\.codex\zentao-bug-triage\snapshots\
```

Recommended layout:

```text
snapshots\
  <YYYYMMDD_HHMMSS>_<branch-slug>\
    bugs.json
    triage.md
    work-items.md
    ignored-items.md
    attachments\
      bug-<id>\
```

Obsidian summary, when the vault exists:

```text
C:\Users\84365\Documents\Obsidian\CodexVault\Codex\projects\zentao\
```

Save only:

- snapshot time
- repo path
- branch
- short commit
- Zentao URL
- selected project/product
- bug IDs/titles/status/category/difficulty/advice
- local attachment paths
- version/branch requirement notes when explicitly fetched
- temporary `work-items.md` only under the local snapshot, for bugs Codex should inspect/fix
- temporary `ignored-items.md` only under the local snapshot, for skipped/waiting bugs and reasons

Do not save:

- passwords
- cookies
- session tokens
- full private chat logs
- unnecessary large logs copied into Markdown

Temporary cleanup:

```powershell
node "%USERPROFILE%\.codex\skills\zentao-bug-triage\scripts\zentao_bug_snapshot.js" --cleanup "<snapshot-dir>"
```

The cleanup command deletes only `work-items.md`, `ignored-items.md`, and `attachments\` inside a valid snapshot directory.
