---
name: asr3602-local-build-flash
description: Build a normal local ASR360x firmware package, automatically select the connected device's flash transport, or perform one build/flash/current-session CATStudio capture chain. Use for 出固件, 编译固件, 编译一个包, 自动刷机, 刷机我测试, 刷到串口机器, 本地编译刷机, or 编译刷机抓日志. Do not use for releases, FOTA, uploads, or DumpTest.
---

# ASR360x Local Build And Flash

The controller restores/prepares the registered branch profile internally. Reuse its result; do not run another full onboarding step or require navigation Markdown before this operation.

Select one mode and load only its required context.

| Request | Mode | Required context |
|---|---|---|
| `出固件` / `编译一个包` | Build only | Build profile; no device or CATStudio |
| `刷这个包` | Flash existing | Package manifest/hash plus physical device |
| `编译并刷机` | Build and flash | Build profile plus physical device |
| `编译刷机抓日志` | Flash and capture | Build/flash receipt plus current CATStudio session |

`刷机我测试` authorizes flashing; the user performs subsequent acceptance.
Reuse the current verified package, or build once if the requested changes still
need a package. `给我包，我自己刷` selects build only. Skill maintenance or a
request for a flashing plan does not authorize operating a connected device.

## Build Only Fast Path

Reuse the task snapshot and invoke the controller once with `-NoFlash`:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.codex\skills\asr3602-local-build-flash\scripts\local_build_flash.ps1" -Repo . -BuildCommand "<project-confirmed command>" -NoFlash
```

Use the exact verified `normal-test` build profile. Do not read device context,
probe USB/COM, open CATStudio, or run a second artifact search. Consume the
controller's package path, SHA256, manifest, and build result.

For a preceding [resource change](../asr3601-lvgl-firmware-triage/references/resource-delivery.md),
reuse this build's resource generation and artifact checks. Report the relevant
output briefly; expand only for a concrete issue or an explicit audit request.
Additional resource receipts are not required for build completion.

## Flash Existing Or Build And Flash

For an existing package:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.codex\skills\asr3602-local-build-flash\scripts\local_build_flash.ps1" -Repo . -NoBuild -Package "<firmware.zip>"
```

For build and flash, omit `-NoBuild`/`-NoFlash` and pass the exact build command.
Immediately before flashing, let the controller revalidate the profile, package
hash, chip compatibility, and physical USB identity. Do not perform a separate
flash or reselect the newest ZIP outside the controller.

The bridge chooses the live transport automatically. The registered normal USB
profile uses its unique main Modem interface with AT download triggering (`-f`);
the registered boot-ROM download profile uses USB download mode. Port numbers
are discovered at runtime. `-Port` is an optional exact-interface constraint,
not a stale-port fallback. Unknown USB profiles, missing/unhealthy interfaces,
multiple targets, or a mismatched explicit port return a selection blocker.
The selected physical identity is pinned and rechecked by the flash owner.
These transport profiles do not establish board or firmware compatibility.

Use `-FlashTimeoutSec` only when a different total download timeout is needed
(default 900 seconds). Consume the single attempt's result file, exit code and
terminal events. A timeout, unknown terminal state or failure does not trigger
another download; preserve the log and current device state before diagnosing.
Do not end a running request at "started" or "100%" without its final receipt.

Reject package names containing `source`, `dump`, or `acceptance`. A COM port is
transport metadata, not device identity; do not use Bluetooth serial ports.

The controller delegates the final transport operation to the installed
aboot-download owner through `flash_verified_package.py`. Active CATStudio,
adownload, or Aboot processes cause a conflict result; neither the controller nor
the flash owner kills them by name. Use the exact capture/session owner's existing
Stop/finalize procedure when interruption is authorized, then reuse the same package.
There is no general ASR background-collector pause/resume lease; do not import the
ESP32 collector's recovery assumptions into this flow.

After successful writing, the receipt reuses the owner's final device snapshot
to report whether normal USB interfaces were observed on the same identity or
USB location. PID/COM changes alone are not a failure. Missing or uncorrelated
normal-mode enumeration leaves startup unverified; even a matching enumeration
does not prove firmware version, screen, touch, or functional acceptance.

After an aboot tool update or when diagnosing loaded code, use
`aboot_status({"runtimeOnly": true})` to read its entry identity without device
probes. This is an update diagnostic, not a routine flash prerequisite.

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
