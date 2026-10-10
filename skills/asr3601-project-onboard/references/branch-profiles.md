# Branch profile operations

Use the shared store for a confirmed first registration, an intended update, or release-configuration history. These commands do not build, upload, flash, commit, or sync Git.

```powershell
python -X utf8 "$env:USERPROFILE\.codex\scripts\asr360x_profile_store.py" register --repo . --adapter <profile.json> --evidence "<source of confirmed parameters>"
python -X utf8 "$env:USERPROFILE\.codex\scripts\asr360x_profile_store.py" prepare --repo .
python -X utf8 "$env:USERPROFILE\.codex\scripts\asr360x_profile_store.py" check --repo .
python -X utf8 "$env:USERPROFILE\.codex\scripts\asr360x_profile_store.py" list --repo .
python -X utf8 "$env:USERPROFILE\.codex\scripts\asr360x_profile_store.py" restore-version --repo . --version "<exact yl_device_ver>"
```

Records bind the complete branch name, product/hardware identity, stable version family, and relevant build input hashes. Detached checkouts bind the commit. Do not copy a previous customer's external mapping when reusing build parameters.

`list` shows branch records and saved release versions. `restore-version` requires the checkout's branch, hardware, build inputs, and exact yl_device_ver to match the saved release. It restores configuration through the normal registry and preserves unregistered local edits. It does not switch Git or rewrite firmware version macros. Add `--read-only` to preview a store operation without writing configuration or cache files.

Schema 1 remains readable. Schema 2 permits omitting standard build.command and build.commandArgs; the shared reader derives them from target/OS/PS/chip. Preserve nonstandard arguments, layout overrides, Dump settings, and unknown fields. Consumers use the returned expandedPath.

A local profile differing from its record requires reviewing and registering the intended update. Corrupt files are preserved. No match upgrades build/device verification. Previous record revisions remain in history; formal release saves the package configuration after its integrity check.

Include the Git common directory's codex/build-profiles explicitly in backups; worktree snapshots excluding .git do not contain these records.
