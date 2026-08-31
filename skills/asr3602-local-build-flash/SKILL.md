---
name: asr3602-local-build-flash
description: Build and optionally flash a normal local ASR3602/360x firmware package without doing a release upload or dump-watchdog modification, and coordinate verified post-flash CATStudio capture when flashing and log capture are both explicit. Use when the user says "出固件", "编译固件", "编译一个包", "刷固件", "刷到串口机器", "本地编译刷机", "自动刷包并抓日志", "编译刷机抓日志", or "刷机后自动抓日志", for a zip whose filename contains neither source nor dump.
---

# ASR3602 Local Build Flash

## Overview

Use this skill for a local build/flash loop only. It compiles the current firmware with the project-confirmed build command, finds a normal package whose filename contains neither `source` nor `dump`, and flashes it to a connected device through aboot/adownload when requested.

## Boundaries

- Do not update `yl.h`, create release folders, write release readmes, or upload to fnOS. If the user says "出版本", "上传", "fnOS", or "release", use `akq-firmware-release`.
- Do not remove `EEHandlerConfig.nvm` or make dump-capable firmware. If the user says "dump 固件", "删看门狗", or "抓 dump", require the owning checkout's `.codex-project\local.md`; this normal-build Skill must never select or flash a dump package.
- Do not guess build parameters from the repo name alone. Prefer `.codex-project\build.md`, current project notes, recent successful terminal output, or explicit user-provided commands.
- Preserve unrelated local source changes. Report dirty files before building if they may affect the output.
- Require `.codex-project/asr3602-build-profile.json` to pass the shared
  `normal-test` preflight. Use its exact build command; reject a caller-provided
  command, target, chip, OS, or PS mode that differs. Candidate adapters cannot
  build or flash through this normal workflow. Verified profiles may use the
  legacy `ASR3602_BUILD_VERIFIED` label or generic `ASR360X_BUILD_VERIFIED`;
  physical flash support remains a separate device-preflight decision.

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
     - LT52 APP public: `make craneg_modem_watch TARGET_OS=THREADX PS_MODE=LITE_LTEONLY CHIP_ID=CRANEL`
     - ASR3603: `make craneg_modem_watch TARGET_OS=THREADX PS_MODE=LTEGSM CHIP_ID=CRANEG`
   - If no command is confirmed, ask before compiling.

3. Build and find the artifact:
   - Prefer `scripts\local_build_flash.ps1` with `-BuildCommand`.
   - Pass the exact project command without manually appending `ROOT_DIR` or
     `OUT`. The shared ASR360x runtime injects idempotent POSIX values from
     `-Repo`, including when the Windows checkout path contains spaces.
   - Use the newest `.zip` under `out\product\<target>` whose filename contains neither `source` nor `dump`, unless the package path is explicit.
   - Reject explicit package paths containing `source`, `dump`, or `acceptance`;
     those artifacts do not belong to this normal-flash workflow.
   - Write `normal-test-manifest.json` beside the selected ZIP with
     `build_profile=normal-test`, full HEAD, dirty summary, exact command,
     adapter SHA256, and package SHA256.

4. Flash when requested:
   - Immediately before flashing, rerun the `normal-test` preflight and recompute
     both adapter and package SHA256. Any drift blocks flashing.
   - Run the shared `aa-skill-router/scripts/embedded_target_preflight.ps1` first. Require project/artifact/CHIP_ID/USB identity agreement; COM alone is insufficient.
   - Prefer an exposed aboot/download MCP if available in the current session.
   - If no MCP is exposed, use local `adownload.exe` fallback.
   - Use a confirmed ASR modem/download COM port. Do not use Bluetooth serial ports.
   - Report final flash status and the package path.

5. Use Normal Flash + Capture Mode only when the user explicitly requests both flashing and normal log capture:
   - If compilation is requested, run `local_build_flash.ps1` with `-NoFlash -CleanTargetOutput -RequireFreshPackage`. `-CleanTargetOutput` removes only the selected generated `out/product/<target>` directory after strict path validation; it must not run repository-wide `make clean` or touch source files. Select only the package generated or updated by that build.
   - Pin the script's exact absolute `packagePath` and `packageSha256`. Pass both as `releasePackage` and `expectedPackageSha256` to `aboot_flash_then_capture`; never let the MCP reselect a different newest package after the build.
   - Require the returned package SHA256, project target, CHIP_ID compatibility, live branch/commit, and unique physical USB ID to match. Block on any mismatch, any path outside the target output, or any filename containing `source` or `dump`.
   - Let `aboot_flash_then_capture` perform the single flash and current-session CATStudio Stop/save. Do not flash first with this script and do not call CATStudio capture a second time afterward.
   - Pass `requiredKeywords` or `requiredRegex` only for real business assertions. Keep `keywords` as extraction hints. Treat `businessStatus=NOT_REQUESTED` as capture-only evidence, not business verification.
   - Keep release folder/readme/fnOS/`yl.h` work and watchdog/dump modifications outside this mode.

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
- Firmware SHA256 and pinned physical device ID.
- Whether flashing succeeded or was skipped.
- Flash stage, current-session capture stage, ICL/ILD paths and growth, extractor status, and business evidence status when Normal Flash + Capture Mode is used.
- Any dirty files that may affect reproducibility.
