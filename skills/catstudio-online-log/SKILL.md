---
name: catstudio-online-log
description: Prepare ASR CATStudio online LogViewer after flashing firmware: select Generic Target Online, ensure the current craneg_modem_watch .mdb.txt database, open the LogViewer filter panel, and apply a narrow wxpay/camera/MMI whitelist. Use for requests such as 打开CAT日志, 选择在线日志, 刷完机打开cat软件, 在线日志筛选, 微信支付扫码日志. This skill only prepares live logging; it does not flash firmware, receive YModem dump files, or build dump firmware.
---

# CATStudio Online Log

Use this after flashing firmware when the next step is to watch live CATStudio logs.

## Tool

Preferred MCP server:

```text
catstudio-online-log
```

Main tools:

- `catstudio_online_log_status`: inspect CATStudio process state, online config, selected `.mdb.txt`, and latest `Bin Logs`.
- `catstudio_prepare_online_log_viewer`: update `CATStudio_GenericTarget_Online.xml`, start CATStudio if needed, select `Generic Target Online`, open `Show Filter...`, and apply the right-side whitelist.

Fallback direct command:

```powershell
python C:\Users\84365\plugins\catstudio-online-log\scripts\catstudio_online_log_mcp.py --tool catstudio_prepare_online_log_viewer "{}"
```

## Defaults

- CATStudio root: `C:\Users\84365\Desktop\CATStudio_V3_1_4_89`
- Online config: `Exec\Config\CATStudio_GenericTarget_Online.xml`
- Database: newest `out\product\**\craneg_modem_watch.mdb.txt` under the current project.
- Filter whitelist: `MMI`, `HAL`, `MSG_IPC`, `APM`, `APLP`, `ATCMD`, `ATCommand`, `PRINTF`, `WXP`, `WXPAY`, `CAMERA`, `QRCODE`, `QR`, `QRDEC`, `SCAN`, `ZBAR`.

## Guardrails

- This workflow must not flash firmware and must not write NVM.
- This workflow must not receive dump/YModem files. For explicit dump capture, use `catstudio-log-extractor` / `catstudio-capture`.
- Treat `FILTER_NOT_APPLIED` as a real failure: capture logs without trusting the GUI filter, or fix the CATStudio UI automation.
- Always verify `configAfter.lastCpTextDb` points to the current firmware workspace before using logs for analysis.
