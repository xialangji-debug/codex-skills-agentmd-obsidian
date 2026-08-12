# Fix Record Schema

## Ownership

`obsidian-fix-pattern-memory` is the only writer of canonical fix-pattern state.
Other skills submit evidence or status events through `scripts/fix_memory.py`.

## Identity

- `fix_id` identifies one root cause across projects and branches.
- `repo_id` is a one-way hash of the Git remote or local root. Never store the raw path.
- `variant_id` is a one-way hash of the exact local variant name.
- `target_id` hashes `repo_id + branch + version + variant_id`.
- `bug_ids` associates one target application with one or more external Bug IDs.

## Independent State Axes

| Axis | Values |
|---|---|
| implementation | `not_applied`, `applied`, `committed`, `superseded`, `failed` |
| verification | `unverified`, `static_checked`, `build_passed`, `device_verified`, `platform_verified`, `qa_verified`, `needs_review` |
| zentao | `unknown`, `active`, `resolved`, `closed`, `reactivated` |
| relation | `candidate`, `applied`, `reference`, `not_applicable` |

`resolved` means development marked the Bug solved and QA is still pending. Only
`closed` or explicit equivalent QA evidence can produce `qa_verified`.

## Reference Selection

Choose the most recent eligible target at the strongest evidence level:

```text
qa_verified > platform_verified > device_verified > build_passed
> static_checked > unverified
```

A newer weak target never replaces an older stronger reference. A reactivated
reference is downgraded to `needs_review`; select the next eligible target and
retain the old ID as `last_reference_target`.

## Reactivation

- Same target and materially same symptom: `reactivated_same`; mark that target
  `failed + needs_review`.
- Different target or materially changed symptom: `reactivated_variant`; retain
  the old target state and require code review before linking a new target.
- Missing from an active list is never evidence. Read the detail status first.

## Privacy

Canonical notes and local state may contain branch names and Bug IDs because they
remain in the local work vault. Reusable skill repositories must contain only this
schema, generic code, and synthetic fixtures. Never commit raw repository paths,
usernames, service hosts, customer mappings, device identities, or live snapshots.
