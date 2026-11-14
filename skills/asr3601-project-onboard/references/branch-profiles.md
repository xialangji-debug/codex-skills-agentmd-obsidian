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

Publication dates and both F/T and S/ST sequence suffixes leave the build family
unchanged, including versions without a timestamp. Existing records with an older
S/ST family representation remain readable; historical records are not rewritten
to satisfy this normalization. Product/hardware, branch, and tracked build-input
bindings still have to match. Current binding covers the root Makefile and
CMakeLists.txt when present; it is not a complete dependency-graph scanner.

### Root Build Input Review

A change only to root Makefile/CMakeLists.txt hashes returns
`BUILD_INPUT_REVIEW_REQUIRED`; it does not invalidate the confirmed parameters.
The owner reviews the changed definitions against the selected target, OS,
PS_MODE, CHIP_ID, layout, and build command. Use the recorded commit/diff when
it matches the old hash; otherwise use available source evidence and state any
missing baseline. Do not infer harmlessness from the filename or strip comments
with a generic Make/CMake parser.

For comments or unrelated targets whose change leaves these settings valid,
refresh the binding with the review evidence, then continue the authorized flow:

```powershell
python -X utf8 "$env:USERPROFILE/.codex/scripts/asr360x_profile_store.py" refresh-inputs --repo . --evidence "<changed definitions and why this target's settings remain valid>"
```

This reuses the registered parameters and preserves history and local edits. It
does not require another user confirmation. When the settings actually need an
update, use normal registration with the verified values; ask only for facts not
available in current source, records, or instructions. Historical release snapshots
remain exact and immutable; this refresh does not relax restore-version checks.
Quick Release still stops after a controller failure, including this review status.

### Optional Configuration Values

When a confirmed target depends on a deeper JSON configuration not covered above,
its profile can opt into `configurationInputs`. Select only the relevant values
using repository-relative paths and JSON Pointers, then register the intended
profile update through the existing command. For example, if this target uses
the ASR3602 single-Flash layout, its bootloader allocation can be bound with:

```json
"configurationInputs": [
  {
    "path": "releasepack/config/partition/ASR3602_SINGLE_FLASH_LAYOUT.json",
    "pointer": "/partitions/0/partitions/0/size"
  }
]
```

This optional field works with profile schema 1 or 2. Registration stores the
selected JSON value in `contextBinding`; prepare, build preflight, release
snapshot/restore and controller view refresh compare that same value. A changed
allocation prevents reusing the old configuration. Formatting, unrelated note
fields and ordinary source changes do not affect these selectors. Existing root
Makefile/CMakeLists.txt changes use the focused review above.

Pointers support object keys, array indexes and standard `~0`/`~1` escapes; zero,
false and null are valid selected values, distinct from missing paths. Select a
leaf or a relevant subtree, not the entire file (empty pointer). Missing files,
missing values or malformed selectors report the exact configuration issue.
This reads JSON, without evaluating C/Make expressions or scanning dependencies.
An absent or empty list preserves existing profiles; do not add selectors or
re-register projects that have no demonstrated need. Confirm the selected file
and array position actually apply to the target before enabling this field.

`list` shows branch records and saved release versions. `restore-version` requires the checkout's branch, hardware, build inputs, and exact yl_device_ver to match the saved release. It restores configuration through the normal registry and preserves unregistered local edits. It does not switch Git or rewrite firmware version macros. Add `--read-only` to preview a store operation without writing configuration or cache files.

Schema 1 remains readable. Schema 2 permits omitting standard build.command and build.commandArgs; the shared reader derives them from target/OS/PS/chip. Preserve nonstandard arguments, layout overrides, Dump settings, and unknown fields. Consumers use the returned expandedPath.

A local profile differing from its record requires reviewing and registering the intended update. Corrupt files are preserved. No match upgrades build/device verification. Previous record revisions remain in history; formal release saves the package configuration after its integrity check.

Include the Git common directory's codex/build-profiles explicitly in backups; worktree snapshots excluding .git do not contain these records.

## Controller View Refresh

Inside a controller that already owns preparation and preflight, reuse its receipt:

```powershell
python -X utf8 "$env:USERPROFILE/.codex/skills/asr3601-project-onboard/scripts/project_onboard.py" --repo . --refresh-view --configuration-receipt "<preflight.json>"
```

The receipt must have PASSED status, the same repository/branch, and an unchanged
adapter hash. Bound adapters must still match live product/hardware/build inputs;
ordinary named-branch commits and release dates do not invalidate those settings.
The generated view reports REUSED, not a new preflight or build result. Legacy
unbound adapters cannot refresh the view from a receipt: unchanged HEAD alone
cannot exclude dirty hardware or build-input changes. Preserve their existing
view without falling back to another preparation. This optional refresh returns
`REFRESH_SKIPPED_UNBOUND`, no writes, and exit 0, so a legacy build does not fail
because its view cannot be refreshed; this is not configuration verification.
Real receipt/binding drift returns exit 2. `--dry-run` previews without writes.
Conflicting prepare/write/check modes are rejected. Existing AGENTS.md and local.md
remain project-owned, and stale receipts do not overwrite views.
