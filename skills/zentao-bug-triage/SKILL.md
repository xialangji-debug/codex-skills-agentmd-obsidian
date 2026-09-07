---
name: zentao-bug-triage
description: Fetch a lightweight current-project Zentao Bug list, deep-fetch selected Bug IDs with their attachments, or explicitly reconcile exact-target history. Use for 当前bug, 当前分支bug, 抓bug, 看禅道bug, a bare Bug ID that needs fetching, 下载附件, or 回归/状态对账. This skill is read-only in Zentao; use zentao-bug-resolver for remote resolution.
---

# Zentao Bug Triage

Keep listing, deep investigation, and history reconciliation separate. A plain
list request must not preload every Bug's details or attachments.

## Mode Selection

| Request | Mode | Work performed |
|---|---|---|
| `抓bug` / `当前bug` / `这个分支有哪些bug` | List | Active rows and compact chat table only |
| `查 4045` / `修 4045` / selected IDs | Selected | Deep-fetch only those IDs and download their attachments |
| `全部深挖` / `回归对账` / historical status review | Deep/Reconcile | Explicit full details and exact-target reconciliation |

If the user already supplied full steps, actual/expected behavior, and local
evidence, skip Zentao fetching and use `asr3601-lvgl-firmware-triage`.

## List Fast Path

Run one command from the current firmware checkout:

```powershell
python -X utf8 "$env:USERPROFILE\.codex\skills\zentao-bug-triage\scripts\zentao_bug_fast_fetch.py" --repo .
```

The default list path does not open Bug detail pages, download attachments,
search fix-pattern memory, create repair work queues, inspect code, or reconcile
history. Read `chat-summary.md`, paste its compact table, and stop so the user can
choose one Bug. Do not infer repair eligibility from a title-only row.

## Selected Bug Path

Deep-fetch only the requested ID. Prefer one Bug at a time; accept multiple IDs
only when the user explicitly selected them together.

```powershell
python -X utf8 "$env:USERPROFILE\.codex\skills\zentao-bug-triage\scripts\zentao_bug_fast_fetch.py" --repo . --ids 4045
```

This path opens the selected detail, records current status and activation
history, downloads its attachments, and creates `work-items.md`. Build one Bug
capsule containing title, status, steps, actual, expected, latest activation,
attachment paths, product, and observed time. Hand only that capsule to
`asr3601-lvgl-firmware-triage`; do not carry another Bug's attachments,
hypotheses, or repair eligibility into the task.

## Deep And Reconcile Modes

Use these only when explicitly requested:

```powershell
# Deep-fetch all listed Bugs and their attachments.
python -X utf8 "$env:USERPROFILE\.codex\skills\zentao-bug-triage\scripts\zentao_bug_fast_fetch.py" --repo . --deep-all

# Deep-fetch and compare the exact target with the previous local baseline.
python -X utf8 "$env:USERPROFILE\.codex\skills\zentao-bug-triage\scripts\zentao_bug_fast_fetch.py" --repo . --deep-all --reconcile
```

Reconciliation may refresh only previously tracked IDs missing from the current
active list. Missing from a list is never itself a status transition.

## Required Boundaries

- Load credentials only from the configured encrypted local credential. Never
  print or store passwords in reports, memory, Git, or this Skill.
- Resolve the current repository, branch, firmware identity, and exact Zentao
  product from live checkout evidence. Similar product-name prefixes are not an
  exact match.
- Fetch `active` by default. Fetch resolved, closed, all, or historical records
  only when requested.
- List and investigation are read-only. They do not authorize source edits,
  branch changes, commits, device actions, releases, or Zentao writes.
- For a selected Bug, use the latest reactivation note as the current symptom.
  Treat `已解决` as development-resolved and QA-pending; only `已关闭` or explicit
  QA evidence supports QA verification.
- Low-level hardware, modem, driver, or platform-owned evidence may be reported,
  but must not be converted into a firmware fix without a concrete owning path.
- Preserve unrelated local changes.

The launcher initializes missing project context, validates the resulting
snapshot against live Git and `yl.h`, and refreshes stale context only after a
successful fetch. Do not duplicate those checks outside the launcher.

## Outputs And References

- `chat-summary.md`: user-facing list; identify each item as `<ID> <完整标题>`.
- `work-items.md`: selected deep-fetch work order only.
- `ignored-items.md`: deep-mode skip/waiting reasons only.
- `bugs.json` and `triage.md`: local snapshot evidence.

Read [classification rules](references/classification-rules.md) only for a deep
classification, [local storage](references/local-storage.md) only for cleanup or
snapshot management, and [project map](references/project-map.md) only when the
private current-project mapping is missing or ambiguous.
