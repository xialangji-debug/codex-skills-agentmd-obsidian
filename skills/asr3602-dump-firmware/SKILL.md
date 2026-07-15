---
name: asr3602-dump-firmware
description: Build and flash a dump-capable LT52 ASR3602/3602 firmware from the lt52_XCX_GB_WK workspace by temporarily removing the EEHandlerConfig.nvm watchdog entry from releasepack/reliabledata/asr3602_evb/config.json, building craneg_modem_watch, restoring the file so the deletion is never committed, and using adownload.exe to flash the package. Use when the user asks for "出能抓dump的固件", "dump固件", "3602 dump固件", "删看门狗出固件", "刷dump固件", or asks to make and flash a dump test firmware.
---

# ASR3602 Dump Firmware

## Core Rule

Treat `releasepack/reliabledata/asr3602_evb/config.json` entry
`{ "id": "CDF", "image": "EEHandlerConfig.nvm" }` as the ASR3602 watchdog config.
For dump-capture firmware, remove only this JSON object for the build package, then restore the file byte-for-byte before any commit/stage work. Do not delete `EEHandlerConfig.nvm` itself unless the user explicitly asks.

## Boundary With Dump Capture

This skill only prepares and flashes dump-capable firmware. It does not capture CATStudio logs, receive YModem dump files, close CATStudio, or parse evidence after the device crashes.

When the user asks for `抓dump日志`, `接收dump`, `YModemDump`, `dump文件`, or `CATStudio dump`, use `catstudio-log-extractor` and the `catstudio-capture` MCP instead. After this skill finishes flashing, hand off to `catstudio-capture` only if the user wants to collect dump evidence.

## Preferred Automation

Run the bundled PowerShell script from the repo root or pass `-Repo` explicitly:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\84365\.codex\skills\asr3602-dump-firmware\scripts\build_dump_firmware.ps1 -Repo C:\Users\84365\Desktop\inside\lt52_XCX_GB_WK
```

Default behavior:

- Save the original `config.json` text to a temp backup.
- Remove the `EEHandlerConfig.nvm` watchdog entry from `asr3602_evb/config.json`.
- Build with `make craneg_modem_watch TARGET_OS=ALIOS PS_MODE=LITE_LTEONLY CHIP_ID=CRANEL`.
- Restore `config.json` immediately after the build, even if the build fails.
- Select `out/product/craneg_modem_watch/craneg_modem_watch_asr3602_8+8mb.zip`.
- Flash with `prebuilts/misc/windows-x86/adownload.exe -u -a -s 115200 -r -q <zip>`.

Useful options:

```powershell
# Use a known serial port instead of USB auto mode.
powershell -ExecutionPolicy Bypass -File C:\Users\84365\.codex\skills\asr3602-dump-firmware\scripts\build_dump_firmware.ps1 -Port COM7

# Ask adownload to send AT fallback before download mode when a normal serial port is available.
powershell -ExecutionPolicy Bypass -File C:\Users\84365\.codex\skills\asr3602-dump-firmware\scripts\build_dump_firmware.ps1 -Port COM7 -AtFallback

# Build only, leave the dump package for manual flashing.
powershell -ExecutionPolicy Bypass -File C:\Users\84365\.codex\skills\asr3602-dump-firmware\scripts\build_dump_firmware.ps1 -NoFlash
```

Use `-SkipBuild -NoFlash` only to validate the script mechanics against an existing package.

## Manual Fallback

If the script cannot run, do the same sequence manually:

1. Confirm the repo and current branch are the intended LT52 ASR3602 workspace.
2. Read `.codex-project\variant.md` when present and confirm repo, branch, commit, dirty state, `yl_device_ver`, CHIP_ID, TARGET_OS, PS_MODE, protocol, customer/product variant, and Zentao mapping. Refresh it with `asr3601-project-onboard` when missing or stale.
3. Run `git status --short` and note unrelated user changes; do not revert them.
4. Save the exact original text of `releasepack/reliabledata/asr3602_evb/config.json`.
5. Remove only the JSON object whose `id` is `CDF` and `image` is `EEHandlerConfig.nvm`.
6. Build:

```powershell
make craneg_modem_watch TARGET_OS=ALIOS PS_MODE=LITE_LTEONLY CHIP_ID=CRANEL
```

7. Restore `config.json` from the saved original immediately after build completion/failure.
8. Verify the watchdog deletion is not left in the working tree:

```powershell
git diff -- releasepack/reliabledata/asr3602_evb/config.json
```

9. Flash the non-source package:

```powershell
prebuilts\misc\windows-x86\adownload.exe -u -a -s 115200 -r -q out\product\craneg_modem_watch\craneg_modem_watch_asr3602_8+8mb.zip
```

For a known serial port, use:

```powershell
prebuilts\misc\windows-x86\adownload.exe -p COM7 -a -s 115200 -r -q out\product\craneg_modem_watch\craneg_modem_watch_asr3602_8+8mb.zip
```

## Reporting

In the final response, state:

- Whether the build succeeded.
- The package path used for flashing.
- Whether flashing succeeded or why it was not attempted.
- That `releasepack/reliabledata/asr3602_evb/config.json` was restored and the watchdog deletion was not staged/committed.
- If dump evidence collection is still needed, state that the next step is `catstudio-capture` MCP / `catstudio-log-extractor`, not another firmware build.
