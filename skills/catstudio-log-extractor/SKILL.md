---
name: catstudio-log-extractor
description: Extract and summarize ASR/CATStudio log packages for AI triage. Use when Codex receives CATStudio `.zip`, extracted CATStudio log folders, `.icl` logs, LogViewer exports, or requests to automatically export Device0 DIAG/App-DIAG/GKI/DSP data such as MMI/LOG, memory, crash, system, network, SIM, LTE, WiFi, GPS/location, power, CPU, or protocol traces without using the CATStudio GUI.
---

# CATStudio Log Extractor

## Quick Start

Use the bundled script instead of placing tools in a firmware project:

```powershell
python <CODEX_HOME>\skills\catstudio-log-extractor\scripts\extract_catstudio_logs.py "<CATStudio log.zip>" --profile mmi
```

Default output goes beside the input file. Use `--output-dir <dir>` for a separate destination.

## Profiles

- `mmi`: compact `Device 0 / DIAG / MMI / LOG` text for application/business triage. This preserves the old 11-column AI-friendly output.
- `memory`: MMI plus memory-related DIAG records, including `Csw_mem`, `MEMORY`, `malloc`, `alloc`, `free`, heap/stack terms, and CPU usage hints.
- `system`: MMI plus platform/system hints such as `SW_PLAT`, `HW_PLAT`, `PM`, CPU frequency, sleep/suspend/wakeup, reset, dump, and power terms.
- `network`: MMI plus LTE/RRC/NAS/SIM/WiFi/MIFI/LWIP/AT/GPS/location-related records. This can be large.
- `crash`: MMI plus fatal/assert/reset/watchdog/dump/fail/error/panic-style records.
- `all`: every recognized DIAG record. Use only when a broad offline scan is needed.
- `custom`: only records selected by `--include`, `--keyword`, or legacy `--cat1/--cat2/--cat3`.

Multiple profiles are allowed:

```powershell
python <CODEX_HOME>\skills\catstudio-log-extractor\scripts\extract_catstudio_logs.py "<log.zip>" --profile mmi --profile memory --summary
```

## Custom Selection

Use `--include` for category paths:

```powershell
--include MMI/LOG
--include Csw_mem
--include LTE_PS/ERRC_CSR
--include USIMLOG/*/LOG001
```

Use `--keyword` to add records whose category, DB format string, or payload preview contains a term:

```powershell
--profile custom --keyword "Available memory" --keyword watchdog
```

Use `--require-keyword` to narrow a selected profile:

```powershell
--profile network --require-keyword location
```

## Output Notes

- `mmi` writes compact columns: `Index, PC Time, Comm Time, Cat1, Cat2, Cat3, ModuleID, MessageID, PacketCounter, Length, Data`.
- Other profiles write extended columns including DB source, format string, payload type, text/preview, and truncated hex.
- CATStudio GUI exports include many extra columns and `Data Hex`, so they are larger. This script optimizes for AI triage.
- Non-MMI DIAG/GKI/DSP records are often binary payloads decoded by CATStudio with database format metadata. The script preserves IDs, categories, format strings, printable previews, and hex; it does not fully emulate every CATStudio struct decoder.

## Recommended Triage

- Business/app/location/server issue: start with `--profile mmi`.
- Memory/catastrophic slowdown: `--profile mmi --profile memory --summary`.
- Network/SIM/registration/data issue: `--profile mmi --profile network --require-keyword <specific term>` when possible.
- Crash/reboot/fatal: `--profile mmi --profile crash --profile system --summary`.

After creating reusable findings from a log workflow, update the project fix-pattern memory if it is likely to recur across branches or projects.
