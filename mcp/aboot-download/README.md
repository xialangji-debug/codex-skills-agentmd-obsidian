# Aboot Download MCP

Local MCP server for ASR `adownload.exe` firmware flashing.

## Tools

- `aboot_status`: inspect tool paths, ASR USB devices, visible COM ports, and blocking processes.
- `aboot_list_release_packages`: find recent firmware zip packages.
- `aboot_kill_download_processes`: stop stale `adownload.exe`, optionally close CATStudio and AbootDownload GUI.
- `aboot_flash`: run `adownload.exe` with structured options and save the flash log.

CATStudio Logger/UeConsole may hold ASR serial ports open. AbootDownload GUI may also leave `aboot.exe` worker processes around. `aboot_flash` refuses to close either app unless `closeCatstudio` or `closeAbootGui` is explicitly `true`.
