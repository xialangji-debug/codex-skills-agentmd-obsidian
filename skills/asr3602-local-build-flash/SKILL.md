---
name: asr3602-local-build-flash
description: Build and optionally flash a normal local ASR3602/360x firmware package without doing a release upload or dump-watchdog modification. Use when the user says "出固件", "编译固件", "编译一个包", "刷固件", "刷到串口机器", "本地编译刷机", or asks to compile a current 360x project and flash the generated non-source zip to a connected device.
---

# ASR3602 Local Build Flash

## Overview

Use this skill for a local build/flash loop only. It compiles the current firmware with the project-confirmed build command, finds the generated non-source firmware zip, and flashes it to a connected device through aboot/adownload when requested.

## Boundaries

- Do not update `yl.h`, create release folders, write release readmes, or upload to fnOS. If the user says "出版本", "上传", "fnOS", or "release", use `akq-firmware-release`.
- Do not remove `EEHandlerConfig.nvm` or make dump-capable firmware. If the user says "dump 固件", "删看门狗", or "抓 dump", use `asr3602-dump-firmware` first.
- Do not guess build parameters from the repo name alone. Prefer `.codex-project\build.md`, current project notes, recent successful terminal output, or explicit user-provided commands.
- Preserve unrelated local source changes. Report dirty files before building if they may affect the output.

## Workflow

1. Identify context:
   - Confirm the repo root, branch, short commit, and dirty status.
   - Read the current project's `AGENTS.md` and `.codex-project\build.md` when present.
   - Identify the product/protocol variant only as context; do not switch projects or Zentao mappings here.

2. Confirm the build command:
   - Use the exact command recorded in project context or supplied by the user.
   - Common examples from this machine are:
     - ASR3602 watch: `make craneg_modem_watch TARGET_OS=ALIOS PS_MODE=LITE_LTEONLY CHIP_ID=CRANEL`
     - LT52 APP public: `make craneg_modem_watch TARGET_OS=THREADX PS_MODE=LITE_LTEONLY CHIP_ID=CRANEL`
     - ASR3603: `make craneg_modem_watch TARGET_OS=THREADX PS_MODE=LTEGSM CHIP_ID=CRANEG`
   - If no command is confirmed, ask before compiling.

3. Build and find the artifact:
   - Prefer `scripts\local_build_flash.ps1` with `-BuildCommand`.
   - Use the newest non-source `.zip` under `out\product\<target>` unless the package path is explicit.
   - Treat `*_source.zip` as not flashable unless the user explicitly asks for source packaging.

4. Flash when requested:
   - Prefer an exposed aboot/download MCP if available in the current session.
   - If no MCP is exposed, use local `adownload.exe` fallback.
   - Use a confirmed ASR modem/download COM port. Do not use Bluetooth serial ports.
   - Report final flash status and the package path.

## Script

Run from the repo root or pass `-Repo`:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.codex\skills\asr3602-local-build-flash\scripts\local_build_flash.ps1" -Repo . -BuildCommand "make craneg_modem_watch TARGET_OS=ALIOS PS_MODE=LITE_LTEONLY CHIP_ID=CRANEL"
```

Useful options:

```powershell
# Build only and report the selected package.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.codex\skills\asr3602-local-build-flash\scripts\local_build_flash.ps1" -Repo . -BuildCommand "make craneg_modem_watch TARGET_OS=ALIOS PS_MODE=LITE_LTEONLY CHIP_ID=CRANEL" -NoFlash

# Flash an existing package without rebuilding.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.codex\skills\asr3602-local-build-flash\scripts\local_build_flash.ps1" -Repo . -NoBuild -Package "out\product\craneg_modem_watch\firmware.zip" -Port COM14

# Dry-run the resolved actions.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.codex\skills\asr3602-local-build-flash\scripts\local_build_flash.ps1" -Repo . -BuildCommand "make craneg_modem_watch TARGET_OS=ALIOS PS_MODE=LITE_LTEONLY CHIP_ID=CRANEL" -DryRun
```

## Reporting

In the final response, state:

- Build command used.
- Whether build succeeded or was skipped.
- Firmware zip selected.
- Whether flashing succeeded or was skipped.
- Any dirty files that may affect reproducibility.
