# Live Capture And Dump

Use the local `catstudio-capture` MCP server when available.

## Log-only path

For `抓日志`, `保存日志`, or `暂停日志`:

1. Inspect the current CATStudio process and session with `catstudio_capture_status`.
2. Use `catstudio_grab_latest_log` or `catstudio_stop_and_save_log` so Stop targets the bound PID.
3. Wait for the current `.icl/.ild` pair to stabilize, copy that pair, and optionally run fast extraction.

`catstudio_pause_and_save_log` is a compatibility alias that invokes Stop. Never substitute an older directory-wide latest log.

## Explicit Dump path

For `抓dump`, `接收dump`, or `YModemDump` only:

1. Use `catstudio_ymodem_status` to inspect CATStudio, `adownload`, and `aboot` blockers.
2. Use `catstudio_receive_ymodem_dump` with explicit confirmation.
3. Keep its default output under `%USERPROFILE%\Desktop\工具\dump` unless the user names another location.

Do not close CATStudio unless the request authorizes it. Dump-capable build or flash work belongs to the current project's device controller.

## Acceptance

`captureStatus=PASSED` proves only the current CATStudio PID/session, stable file pair, configured target, and minimum ICL growth. Record session ID/start, PID, physical USB ID, ICL/ILD paths and sizes, package path/SHA256, and extractor outputs when a composite flow needs a receipt.

Use `requiredKeywords` and `requiredRegex` as case-insensitive all-of assertions against current-session record TSV files. Ignore `_evidence.md` keyword metadata when deciding a match.

- All requested patterns present: `businessStatus=PASSED`.
- Any requested pattern absent: `businessStatus=FAILED`, naming each missing pattern.
- No assertion requested: `businessStatus=NOT_REQUESTED`.

Never describe `NOT_REQUESTED` as business verification.
