# Explicit Closeout And Re-verification

Use for a follow-up on an established Bug: completion status, verification
instructions, or explicitly requested re-verification. Diagnosis belongs to the
normal triage path; validation-debt aggregation belongs to memory reporting.

Reuse the Bug receipt's identity, changed files, verification, commit state,
memory target, and remaining device/platform debt. Compare current HEAD and dirty
state once. If they still match, report the existing result and run only the
missing verification layer requested by the user. A question about how to verify
can be answered with commands without executing them.

For a stale/missing receipt or explicitly requested fresh verification, use:

```powershell
python -X utf8 "$env:USERPROFILE\.codex\skills\asr3601-lvgl-firmware-triage\scripts\closeout_snapshot.py" --repo . --rg "<changed-symbol>" --build-command "<narrow-command>"
```

The helper owns variant/Git/diff checks and optional LVGL preflight. Do not repeat
those checks separately. Supply locale/i18n options only for relevant UI work.
Use the narrowest documented test/build and preserve unrelated changes.

Return the target, cause, changed behavior, reused/new checks, remaining debt,
Git state, and memory target. Static/build/upload success does not prove device,
platform, or QA acceptance. Update stronger exact-target evidence through
`obsidian-fix-pattern-memory`; remote resolution remains owned by
`zentao-bug-resolver` within the user's authorized scope.
