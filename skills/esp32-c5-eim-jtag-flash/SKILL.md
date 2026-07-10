---
name: esp32-c5-eim-jtag-flash
description: Build and flash ESP32-C5 ESP-IDF projects installed by Espressif Installation Manager (EIM), especially when VS Code or idf.py UART flashing reports "No serial data received", "Serial port auto-detection failed", or cannot enter download mode. Use for ESP32-C5 firmware flashing, COM port checks, EIM PowerShell activation, and OpenOCD/JTAG fallback with board/esp32c5-builtin.cfg.
---

# ESP32-C5 EIM JTAG Flash

## Workflow

Use this skill when the user wants to compile, flash, or recover an ESP32-C5 project on Windows with EIM-managed ESP-IDF.

1. Prefer the EIM PowerShell profile over legacy `export.ps1`.
   - Typical profile: `C:\Espressif\tools\Microsoft.v6.0.2.PowerShell_profile.ps1`
   - It sets `IDF_PATH`, `IDF_TOOLS_PATH`, `IDF_PYTHON_ENV_PATH`, PATH entries, and the `idf.py` wrapper.
2. Detect the board before flashing.
   - Prefer devices with `VID_303A&PID_1001`.
   - Expected serial label can be `USB Serial Device (COMxx)` or localized equivalent.
   - The matching USB JTAG interface can appear as `USB JTAG/serial debug unit`.
3. For the known `C:\Users\84365\Desktop\esp32_c5` board, prefer direct JTAG (`-ForceJtag`) because UART download mode has repeatedly failed with `No serial data received`.
4. Try UART flashing only if the user specifically wants to test normal serial flashing:
   - `idf.py -p COMxx -b 115200 flash`
   - If 115200 succeeds, faster speeds can be tried later.
5. If UART flashing fails with `Failed to connect to ESP32-C5: No serial data received`, use OpenOCD/JTAG fallback:
   - OpenOCD config: `board/esp32c5-builtin.cfg`
   - Program offsets:
     - bootloader: `0x2000`
     - partition table: `0x8000`
     - app: `0x10000`
6. Treat `Verify OK` for the bootloader, partition table, and app as a successful flash.

## Script

Use `scripts/flash_esp32c5_eim_jtag.ps1` for the common workflow.

Examples:

```powershell
# Dry run from the project root, showing the commands without flashing.
powershell -ExecutionPolicy Bypass -File C:\Users\84365\.codex\skills\esp32-c5-eim-jtag-flash\scripts\flash_esp32c5_eim_jtag.ps1 -DryRun

# Build, try UART on COM13, then fall back to JTAG if UART fails.
powershell -ExecutionPolicy Bypass -File C:\Users\84365\.codex\skills\esp32-c5-eim-jtag-flash\scripts\flash_esp32c5_eim_jtag.ps1 -ProjectDir C:\Users\84365\Desktop\esp32_c5 -Port COM13

# Skip UART and flash through OpenOCD/JTAG directly.
powershell -ExecutionPolicy Bypass -File C:\Users\84365\.codex\skills\esp32-c5-eim-jtag-flash\scripts\flash_esp32c5_eim_jtag.ps1 -ProjectDir C:\Users\84365\Desktop\esp32_c5 -ForceJtag

# Fastest repeat flash after a successful build: skip UART and skip build.
powershell -ExecutionPolicy Bypass -File C:\Users\84365\.codex\skills\esp32-c5-eim-jtag-flash\scripts\flash_esp32c5_eim_jtag.ps1 -ProjectDir C:\Users\84365\Desktop\esp32_c5 -ForceJtag -SkipBuild
```

## Manual Commands

If the script is not suitable, run the same steps manually:

```powershell
. C:\Espressif\tools\Microsoft.v6.0.2.PowerShell_profile.ps1
idf.py build
idf.py -p COM13 -b 115200 flash
```

When UART fails but OpenOCD can see the chip:

```powershell
. C:\Espressif\tools\Microsoft.v6.0.2.PowerShell_profile.ps1
openocd -f board/esp32c5-builtin.cfg `
  -c "init" `
  -c "reset halt" `
  -c "program_esp build/bootloader/bootloader.bin 0x2000 verify" `
  -c "program_esp build/partition_table/partition-table.bin 0x8000 verify" `
  -c "program_esp build/esp32_ai_printer.bin 0x10000 verify" `
  -c "reset run" `
  -c "shutdown"
```

## Diagnostics

Use these checks before blaming the ESP-IDF installation:

```powershell
[System.IO.Ports.SerialPort]::GetPortNames() | Sort-Object
Get-PnpDevice -Class Ports -PresentOnly
Get-PnpDevice -PresentOnly | Where-Object {
  $_.FriendlyName -match 'Espressif|USB Serial|USB JTAG|CP210|CH340|CH910|UART|Serial' -or
  $_.InstanceId -match 'VID_303A|VID_10C4|VID_1A86|VID_0403'
}
```

Important interpretation:

- `COMxx` exists and OpenOCD detects the chip: environment and USB/JTAG are probably fine.
- UART flash fails with `No serial data received`: the board did not enter ROM download mode; try BOOT/RESET manually or use JTAG fallback.
- OpenOCD reports ESP32-C5 chip revision and JTAG taps: JTAG flashing is available.
- No ESP serial/JTAG device appears: check board power, data cable, USB port, driver, and whether the board is switched on.

## Project-Specific Defaults

For `C:\Users\84365\Desktop\esp32_c5`, the known working setup is:

- ESP-IDF: `C:\esp\v6.0.2\esp-idf`
- Tools: `C:\Espressif\tools`
- EIM profile: `C:\Espressif\tools\Microsoft.v6.0.2.PowerShell_profile.ps1`
- Detected board: `VID_303A&PID_1001`, previously `COM13`
- App binary: `build\esp32_ai_printer.bin`

Do not treat missing UART logs after a JTAG flash as proof that flashing failed; verify by OpenOCD `Verify OK` and board behavior first.
