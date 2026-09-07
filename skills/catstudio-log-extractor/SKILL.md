---
name: catstudio-log-extractor
description: Extract ASR/CATStudio offline logs, capture the current session, receive an explicitly requested YModem dump, or apply selected-Bug evidence presets. Use for CATStudio ZIP/ICL/ILD files, LogViewer exports, 当前设备抓日志, 抓 dump, and YModem. Start with the narrow mode and expand when its evidence is insufficient.
---

# CATStudio Log Extractor

## Route Once

| Request | Direct path |
|---|---|
| Local `.zip`, `.icl/.ild`, or extracted folder | Run `extract_catstudio_logs.py --fast-evidence` |
| Current device log | Use the `catstudio-capture` MCP log-only workflow |
| Explicit `抓 dump` / `YModem` | Use the MCP YModem workflow |
| Build or flash, then capture | Hand off once to `asr3602-local-build-flash` |
| C10 Bug 3996/4003/4045/4046 attachments | Run `extract_bug_evidence.py --bugs <ids>` |

Do not load device, Dump, or business-acceptance procedures for a local file extraction. Do not flash firmware from this Skill.

## Fast Offline Path

```powershell
python "$env:USERPROFILE\.codex\skills\catstudio-log-extractor\scripts\extract_catstudio_logs.py" "<log.zip>" --fast-evidence --output-dir "<output>"
```

Add only known issue terms with repeated `--keyword`. Expand to `--evidence-pack` only when the compact MMI evidence is insufficient. Read [offline-profiles.md](references/offline-profiles.md) only for a non-default profile or custom category selection.

## C10 Presets

```powershell
python "$env:USERPROFILE\.codex\skills\catstudio-log-extractor\scripts\extract_bug_evidence.py" --bugs 4003,4045,4046
```

Presets live in `profiles/c10-bugs.json`. `3996` is marked video-only; never invent CATStudio evidence when no log archive exists. Use `--attachments <dir>` for a specific selected-Bug snapshot and `--list-presets` to inspect available presets.

## Live And Dump Paths

For current-device log capture or explicit YModem Dump, read [live-capture.md](references/live-capture.md). Keep these boundaries:

- Plain `抓日志` means Stop, wait for a stable current-session `.icl/.ild` pair, copy it, then optionally extract.
- `Pause` is not a save boundary.
- Only an explicit Dump request may enter YModem receive.
- Capture success proves transport and session identity, not firmware behavior.
- Keywords are extraction hints. Business behavior passes only when the requested patterns are present in the current-session record TSV.

## Report

Report the input/session identity, outputs, directly supported evidence, missing evidence, and the narrow next step. Keep platform, device, and QA conclusions separate from parser hits. Update fix-pattern memory only when the evidence leads to a completed behavior-changing fix.
