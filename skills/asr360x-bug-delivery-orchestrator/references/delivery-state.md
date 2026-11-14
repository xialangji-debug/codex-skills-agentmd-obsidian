# Resumable Delivery State

Use for an explicitly ordered/continuous multi-Bug task with authorized per-Bug
commits and a need to resume. Existing single-Bug deliveries remain resumable;
new single-Bug composites use direct specialist receipts. Do not force commitless
work into this sequence:

```text
pending -> deep_fetched -> diagnosed -> fixed -> verified -> committed -> memory_decided -> zentao_resolved
```

Schema version 3 stores one active_bug, expected_head, terminal_stage, compact receipts, and diagnosed no-change outcomes. Schema versions 1 and 2 remain readable; ordinary advancement preserves their version. Explicit finish upgrades an older state to version 3 and reports the upgrade. Explicit narrow upgrades to version 4 to retain scope changes and a stopped-continuation flag; it does not rewrite completed stages.

## Initialize And Advance

```powershell
python "$env:USERPROFILE\.codex\skills\asr360x-bug-delivery-orchestrator\scripts\delivery_state.py" init `
  --repo . --bugs 2935,2931 --terminal-stage memory_decided
```

New states default to memory_decided. Use zentao_resolved only for explicitly
authorized resolution; old states without terminal_stage retain their historical
zentao_resolved meaning. Add --release-requested only when a release was requested.
Reuse the exact delivery ID returned by init. Mutating commands require
--delivery so concurrent chats cannot select one another's most recently updated state.

Advance only after the owner supplies evidence:

```powershell
python "$env:USERPROFILE\.codex\skills\asr360x-bug-delivery-orchestrator\scripts\delivery_state.py" advance `
  --repo . --delivery <delivery-id> --bug 2935 --stage verified --evidence "<actual narrow validation>"
```

For committed add --commit <sha>; this must be a new current HEAD descending from
the previously expected HEAD and updates expected_head. Other stages cannot use
--commit. All stage changes check the branch; non-commit changes also require the
expected HEAD. Unrelated dirty work need not be committed. For a behavior-changing
fix, memory_decided means canonical memory recorded: pass --fix-id, --memory-note,
and --target-id with real evidence. Use finish below for a diagnosed no-change
outcome; never fabricate a note or commit to advance an inapplicable stage.

For a diagnosed Bug requiring no new code change, record its evidence directly:

```powershell
python "$env:USERPROFILE\.codex\skills\asr360x-bug-delivery-orchestrator\scripts\delivery_state.py" finish --repo . --delivery <delivery-id> --bug 2935 --outcome already_fixed --evidence "<current source/build or external-owner evidence>"
```

Outcomes are `already_fixed`, `no_change`, or `external`. Only the active Bug at
diagnosed may take this path. It creates no commit, fix note, or verification
claim. If the configured terminal stage is zentao_resolved, also supply
`--resolution-evidence` from the authorized resolver; local classification does
not satisfy a requested remote resolution.

The tool rejects a later Bug while the active one is incomplete. Once its terminal stage or supported outcome is recorded, it activates the next Bug. Keep implementation and validation evidence separate per Bug.

## Resume And Release

```powershell
python "$env:USERPROFILE\.codex\skills\asr360x-bug-delivery-orchestrator\scripts\delivery_state.py" status --repo . --delivery <delivery-id>
```

Read status before resuming. Do not replay completed commits or remote writes. Resolve unexpected HEAD drift before continuing; the workflow's own recorded commit is an expected change.

When the user narrows the request, update only the relevant pending scope:

```powershell
python "$env:USERPROFILE\.codex\skills\asr360x-bug-delivery-orchestrator\scripts\delivery_state.py" narrow `
  --repo . --delivery <delivery-id> --cancel-release --no-zentao --evidence "仅提交然后同步，不再发布或关禅道"
```

Use only the flags implied by the actual request. --cancel-release withdraws the
pending release; --no-zentao changes the terminal stage to memory_decided; --stop
stops this plan's continuation when its per-Bug commit sequence or selected Bug
scope no longer applies. Keep the remaining narrower work in task receipts;
do not manufacture state transitions. Earlier commits, resolutions, completed
releases, failure receipts, and per-Bug evidence remain recorded. Status stays
read-only even when a plan is stopped.

After the user explicitly authorizes resuming the retained plan, use `resume
--repo . --delivery <delivery-id> --evidence "<current continuation request>"`.
This only clears the stopped flag after checkout checks. It does not restore
withdrawn release or resolution scope. Expanding those actions requires fresh
user scope and the relevant owner; the narrow interface cannot add them.

After all selected Bugs finish and the explicitly requested owner release succeeds:

```powershell
python "$env:USERPROFILE\.codex\skills\asr360x-bug-delivery-orchestrator\scripts\delivery_state.py" release `
  --repo . --delivery <delivery-id> --status released --evidence "<controller release receipt>"
```

Reuse the controller receipt. Recording progress must not become another release
verification pass. A release request alone does not authorize Zentao resolution.
The same successful receipt is idempotent; a released status cannot become pending
or blocked, and its receipt cannot be replaced. The owner may have committed a
release header, so this recording step does not repeat the owner's HEAD checks.

## Maintainer Regression

After changing delivery-state behavior, run `python -X utf8 scripts/test_delivery_state.py`
from this Skill directory. It uses isolated local Git/state fixtures and covers
stage order, no-change outcomes, narrowed scope, resumed continuation and preserved
publication facts. Set `CODEX_TEST_VALIDATION_ROOT` to a task validation directory
when collecting results. This is a tool-maintenance test, not a per-Bug step.
