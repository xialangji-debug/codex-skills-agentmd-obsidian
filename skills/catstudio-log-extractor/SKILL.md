---
name: catstudio-log-extractor
description: Extract and summarize ASR/CATStudio log packages for AI triage and evidence-pack generation. Use when Codex receives CATStudio `.zip`, extracted CATStudio log folders, `.icl` logs, LogViewer exports, live CATStudio logging requests, automatic current-log capture, YModem dump receive requests, or dump-log evidence requests. Handles Device0 DIAG/App-DIAG/GKI/DSP data such as MMI/LOG, memory, crash, system, network, SIM, LTE, WiFi, GPS/location, power, CPU, or protocol traces without using the CATStudio GUI. Use --fast-evidence for the first pass; expand to --evidence-pack when broad crash/network/memory evidence is needed.
---

# CATStudio Log Extractor

## Quick Start

Use the bundled script instead of placing tools in a firmware project:

```powershell
python "%USERPROFILE%\.codex\skills\catstudio-log-extractor\scripts\extract_catstudio_logs.py" "<CATStudio log.zip>" --profile mmi
```

Default output goes beside the input file. Use `--output-dir <dir>` for a separate destination.

## Live CATStudio MCP

When the user asks to grab the current device log, inspect live CATStudio state, capture dump logs, receive a YModem dump file, or package evidence after a repro, prefer the local MCP server `catstudio-capture` when available.

Intent split:

- Plain `抓日志`, `保存日志`, or `暂停日志`: use the log-only workflow. Invoke CATStudio Stop, wait for `.icl/.ild` to become stable, then copy the pair; do not call YModem dump tools. CATStudio Pause only freezes viewer refresh and is not a save boundary.
- Explicit `抓dump`, `接收dump`, or `YModemDump`: use the dump workflow. Dump files default to `%USERPROFILE%\Desktop\工具\dump`.

Configured server:

```text
%USERPROFILE%\plugins\catstudio-capture\scripts\catstudio_capture_mcp.py
```

Main tools:

- `catstudio_capture_status`: locate CATStudio, current `Bin Logs`, latest `.icl/.ild`, serial ports, and blocker processes.
- `catstudio_list_logs`: list recent CATStudio binary log pairs.
- `catstudio_prepare_online_log_viewer`: configure the current project `.mdb.txt`, start CATStudio, and prepare Generic Target Online/LogViewer.
- `catstudio_grab_latest_log`: Stop by default, then copy the stable `.icl/.ild` pair and optionally run this skill's extractor to create evidence files.
- `catstudio_stop_and_save_log`: explicit plain-log workflow for `抓日志`; it invokes Stop, waits for stable files, and copies them.
- `catstudio_pause_and_save_log`: deprecated compatibility alias that now invokes Stop.
- `catstudio_ymodem_status`: inspect whether direct YModem dump receive is safe, including `CATStudio`, `adownload`, and `aboot` blockers. Use only on explicit dump requests.
- `catstudio_receive_ymodem_dump`: receive one dump file over serial YModem into `%USERPROFILE%\Desktop\工具\dump` by default. It refuses unless `confirm=true`; it does not close CATStudio unless `closeCatstudio=true`.

Boundary: this MCP is evidence capture only. It must not modify firmware files, build packages, flash devices, or remove the watchdog config. When the user explicitly needs dump-capable firmware built or flashed, enter the owning ASR checkout through `.codex-project/local.md`; stop if that project has no local dump workflow.

If the MCP tools are not visible in the current session, the configuration may have been added after Codex started. Use the script directly as a fallback, or restart/reload Codex to expose the MCP tools.

## Acceptance Contract

- Treat `captureStatus=PASSED` as transport/capture proof only: CATStudio Online configuration is verified, the Stop action targets the bound CATStudio PID, the copied ICL/ILD pair belongs to the same session baseline, and ICL growth reaches the configured threshold. Never substitute an older directory-wide `latest` log.
- Treat `keywords` only as extraction hints. A hit or miss does not decide business behavior.
- Use `requiredKeywords` and `requiredRegex` as case-insensitive all-of assertions against record TSV files generated from the current session. Ignore `_evidence.md` keyword metadata when deciding matches.
- Report `businessStatus=PASSED` only when every required pattern matches. Report `FAILED` with each missing pattern when any assertion is absent. Report `NOT_REQUESTED` when no assertion was supplied, and never describe that state as business verification.
- Include the capture session ID/start, CATStudio PID, package path/SHA256, physical USB ID, ICL/ILD paths and sizes, growth, extractor outputs, and each required pattern's match file/line in composite-flow evidence.
- Keep this Skill evidence-only. Let `aboot_flash_then_capture` coordinate the composite flash/capture operation; do not independently flash from this Skill.

For broad or deep issue triage, use evidence-pack mode:

```powershell
python "%USERPROFILE%\.codex\skills\catstudio-log-extractor\scripts\extract_catstudio_logs.py" "<CATStudio log.zip>" --evidence-pack --output-dir "<triage-output>"
```

This writes:

- `*_catstudio_mmi.tsv`
- `*_catstudio_crash.tsv`
- `*_catstudio_network.tsv`
- `*_catstudio_memory.tsv`
- `*_catstudio_system.tsv`
- `*_catstudio_summary.tsv`
- `*_evidence.md`

For a fast first pass, especially protocol, UI, micro-chat, APP command, or other MMI-heavy issues, use:

```powershell
python "%USERPROFILE%\.codex\skills\catstudio-log-extractor\scripts\extract_catstudio_logs.py" "<CATStudio log.zip>" --fast-evidence --output-dir "<triage-output>"
```

This writes only the compact `mmi` TSV plus summary/evidence files, records default keyword hits, and reuses cached outputs when the same zip and options are run again. Add narrow keywords when known:

```powershell
python "%USERPROFILE%\.codex\skills\catstudio-log-extractor\scripts\extract_catstudio_logs.py" "<CATStudio log.zip>" --fast-evidence --keyword TXT --keyword CHAT1 --output-dir "<triage-output>"
```

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
python "%USERPROFILE%\.codex\skills\catstudio-log-extractor\scripts\extract_catstudio_logs.py" "<log.zip>" --profile mmi --profile memory --summary
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

- Business/app/protocol/UI/micro-chat issue: start with `--fast-evidence`.
- Location/server issue: start with `--profile mmi`, then add `--profile network --require-keyword location` if MMI is insufficient.
- Memory/catastrophic slowdown: `--profile mmi --profile memory --summary`.
- Network/SIM/registration/data issue: `--profile mmi --profile network --require-keyword <specific term>` when possible.
- Crash/reboot/fatal: `--profile mmi --profile crash --profile system --summary`.
- Unknown firmware bug with attached CATStudio evidence: start with `--fast-evidence`, then expand to `--evidence-pack` only if MMI/keyword evidence is insufficient.

After creating reusable findings from a log workflow, update the project fix-pattern memory if it is likely to recur across branches or projects.
