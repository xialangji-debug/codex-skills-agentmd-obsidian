---
name: asr3602-local-build-flash
description: Build a normal local ASR360x firmware package, flash an existing verified package, or perform one build/flash/current-session CATStudio capture chain. Use for 出固件, 编译固件, 编译一个包, 刷固件, 刷到串口机器, 本地编译刷机, or 编译刷机抓日志. Do not use for releases, FOTA, uploads, or DumpTest.
---

# ASR360x Local Build And Flash

Select one mode and load only its required context.

| Request | Mode | Required context |
|---|---|---|
| `出固件` / `编译一个包` | Build only | Build profile; no device or CATStudio |
| `刷这个包` | Flash existing | Package manifest/hash plus physical device |
| `编译并刷机` | Build and flash | Build profile plus physical device |
| `编译刷机抓日志` | Flash and capture | Build/flash receipt plus current CATStudio session |

## Build Only Fast Path

Reuse the task snapshot and invoke the controller once with `-NoFlash`:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.codex\skills\asr3602-local-build-flash\scripts\local_build_flash.ps1" -Repo . -BuildCommand "<project-confirmed command>" -NoFlash
```

Use the exact verified `normal-test` build profile. Do not read device context,
probe USB/COM, open CATStudio, or run a second artifact search. Consume the
controller's package path, SHA256, manifest, and build result.

## Flash Existing Or Build And Flash

For an existing package:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.codex\skills\asr3602-local-build-flash\scripts\local_build_flash.ps1" -Repo . -NoBuild -Package "<firmware.zip>" -Port <confirmed-port>
```

For build and flash, omit `-NoBuild`/`-NoFlash` and pass the exact build command.
Immediately before flashing, let the controller revalidate the profile, package
hash, chip compatibility, and physical USB identity. Do not perform a separate
flash or reselect the newest ZIP outside the controller.

Reject package names containing `source`, `dump`, or `acceptance`. A COM port is
transport metadata, not device identity; do not use Bluetooth serial ports.

## Flash And Capture

Enter this mode only when the user explicitly asks for both flashing and current
log capture. Build once with `-NoFlash -CleanTargetOutput -RequireFreshPackage`,
then pass that exact package path and SHA256 to the combined flash/capture owner.
Do not flash once and call CATStudio capture a second time.

Read [flash and capture](references/flash-capture.md) only for this composite
mode's evidence contract.

## Boundaries

- Do not update `yl.h`, create release folders/readmes, upload, or publish. Route
  formal release and FOTA to their owners.
- Do not remove watchdog configuration or select/build a Dump package. Route
  DumpTest to the current project's dump owner.
- Preserve unrelated local changes. Dirty files may affect reproducibility but
  do not authorize staging, cleanup, or discard.
- Do not guess build parameters from a repository name. If the verified profile
  and user-supplied command disagree, stop with the exact mismatch.
- Build/package, flash, current-session capture, business evidence, and device/QA
  acceptance are separate results.

Report only the selected mode's command/result, exact package and SHA256, flash
target/result when applicable, capture result when applicable, and relevant dirty
state. Do not print unused-mode fields.
