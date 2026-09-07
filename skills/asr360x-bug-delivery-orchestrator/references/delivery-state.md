# Resumable Delivery State

Use only when selected Bugs include authorized per-Bug commits. Do not force commitless work into this sequence:

```text
pending -> deep_fetched -> diagnosed -> fixed -> verified -> committed -> memory_decided -> zentao_resolved
```

Schema version 3 stores one active_bug, expected_head, terminal_stage, compact receipts, and diagnosed no-change outcomes. Schema versions 1 and 2 remain readable; ordinary advancement preserves their version. Explicit finish upgrades an older state to version 3 and reports the upgrade.

## Initialize And Advance

```powershell
python "$env:USERPROFILE\.codex\skills\asr360x-bug-delivery-orchestrator\scripts\delivery_state.py" init `
  --repo . --bugs 2935,2931 --terminal-stage memory_decided
```

Use memory_decided when fixes/commits are requested without Zentao resolution. Use zentao_resolved only for explicitly authorized resolution. Add --release-requested only when a release was requested.

Advance only after the owner supplies evidence:

```powershell
python "$env:USERPROFILE\.codex\skills\asr360x-bug-delivery-orchestrator\scripts\delivery_state.py" advance `
  --repo . --bug 2935 --stage verified --evidence "<actual narrow validation>"
```

For committed add --commit <sha>; this updates expected_head. For a behavior-changing fix, memory_decided means canonical memory recorded: pass --fix-id, --memory-note, and --target-id with real evidence. Use finish below for a diagnosed no-change outcome; never fabricate a note or commit to advance an inapplicable stage.

For a diagnosed Bug requiring no new code change, record its evidence directly:

```powershell
python "$env:USERPROFILE\.codex\skills\asr360x-bug-delivery-orchestrator\scripts\delivery_state.py" finish --repo . --bug 2935 --outcome already_fixed --evidence "<current source/build or external-owner evidence>"
```

Outcomes are `already_fixed`, `no_change`, or `external`. Only the active Bug at
diagnosed may take this path. It creates no commit, fix note, or verification
claim. If the configured terminal stage is zentao_resolved, also supply
`--resolution-evidence` from the authorized resolver; local classification does
not satisfy a requested remote resolution.

The tool rejects a later Bug while the active one is incomplete. Once its terminal stage or supported outcome is recorded, it activates the next Bug. Keep implementation and validation evidence separate per Bug.

## Resume And Release

```powershell
python "$env:USERPROFILE\.codex\skills\asr360x-bug-delivery-orchestrator\scripts\delivery_state.py" status --repo .
```

Read status before resuming. Do not replay completed commits or remote writes. Resolve unexpected HEAD drift before continuing; the workflow's own recorded commit is an expected change.

After all selected Bugs finish and the explicitly requested owner release succeeds:

```powershell
python "$env:USERPROFILE\.codex\skills\asr360x-bug-delivery-orchestrator\scripts\delivery_state.py" release `
  --repo . --status released --evidence "<controller release receipt>"
```

Reuse the controller receipt. Recording progress must not become another release verification pass. A release request alone does not authorize Zentao resolution.
