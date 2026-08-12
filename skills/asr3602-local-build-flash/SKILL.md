---
name: asr3602-local-build-flash
description: Build and optionally flash a normal local ASR3602/360x firmware package without doing a release upload or dump-watchdog modification. Use when the user says "出固件", "编译固件", "编译一个包", "刷固件", "刷到串口机器", "本地编译刷机", or asks to compile a current 360x project and flash a generated zip whose filename contains neither source nor dump.
---

# ASR3602 Local Build Flash

## Overview

Use this skill for a local build/flash loop only. It compiles the current firmware with the project-confirmed build command, finds a normal package whose filename contains neither `source` nor `dump`, and flashes it to a connected device through aboot/adownload when requested.

## Boundaries

- Do not update version metadata, create release folders, write release readmes, or upload. If the user says "出版本", "上传", or "release", use the private project-local release workflow from `.codex-project/local.md`.
- Do not remove `EEHandlerConfig.nvm` or make dump-capable firmware. If the user says "dump 固件", "删看门狗", or "抓 dump", require the owning checkout's `.codex-project\local.md`; this normal-build Skill must never select or flash a dump package.
- Do not guess build parameters from the repo name alone. Prefer `.codex-project\build.md`, current project notes, recent successful terminal output, or explicit user-provided commands.
- Preserve unrelated local source changes. Report dirty files before building if they may affect the output.

## Workflow

1. Identify context:
   - Confirm the repo root, branch, short commit, and dirty status.
   - Read the current project's `AGENTS.md`, `.codex-project\variant.md`, and `.codex-project\build.md` when present.
   - Confirm the variant fingerprint: `yl_device_ver`, chip, OS, protocol, customer/product variant, build parameters, and Zentao mapping. Refresh it with `asr3601-project-onboard` if it is missing or stale.
   - Identify the product/protocol variant only as context; do not switch projects or Zentao mappings here.

2. Confirm the build command:
   - Use the exact command recorded in project context or supplied by the user.
   - Common examples from this machine are:
     - ASR3602 watch: `make craneg_modem_watch TARGET_OS=ALIOS PS_MODE=LITE_LTEONLY CHIP_ID=CRANEL`
     - Product-specific exceptions belong in `.codex-project/build.md`; do not bundle real device/version mappings in this Skill.
     - ASR3603: `make craneg_modem_watch TARGET_OS=THREADX PS_MODE=LTEGSM CHIP_ID=CRANEG`
   - If no command is confirmed, ask before compiling.

3. Build and find the artifact:
   - Prefer `scripts\local_build_flash.ps1` with `-BuildCommand`.
   - Use the newest `.zip` under `out\product\<target>` whose filename contains neither `source` nor `dump`, unless the package path is explicit.
   - Reject explicit package paths containing `source` or `dump`; those artifacts do not belong to this normal-flash workflow.

4. Flash when requested:
   - Run the shared `aa-skill-router/scripts/embedded_target_preflight.ps1` first. Require project/artifact/CHIP_ID/USB identity agreement; COM alone is insufficient.
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

# Flash an existing package without rebuilding, using a freshly confirmed port.
$confirmedPort = Read-Host "Confirmed ASR download COM port"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.codex\skills\asr3602-local-build-flash\scripts\local_build_flash.ps1" -Repo . -NoBuild -Package "out\product\craneg_modem_watch\firmware.zip" -Port $confirmedPort

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
