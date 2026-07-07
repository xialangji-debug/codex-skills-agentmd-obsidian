---
name: wechat-chat-export
description: Export the currently open WeChat desktop chat or group chat that the user can already view, using Windows UI automation, clipboard capture, scrolling, and best-effort parsing to Markdown, JSONL, CSV, and raw text. Use when the user asks to extract, archive, summarize, or structure visible WeChat chat history without reading/decrypting WeChat databases, stealing keys, or bypassing client access controls.
---

# WeChat Chat Export

## Boundaries

Use only the logged-in WeChat desktop window and chat content visible or scroll-loadable in that client. Do not decrypt WeChat databases, inspect process memory for keys, bypass access controls, or extract chats the user cannot view in the client.

## Quick Start

1. Ask the user to open WeChat desktop and select the target chat.
2. Run discovery if needed:

```powershell
py C:\Users\84365\.codex\skills\wechat-chat-export\scripts\wechat_chat_export.py discover
```

3. Export the current chat window:

```powershell
py C:\Users\84365\.codex\skills\wechat-chat-export\scripts\wechat_chat_export.py export --cycles 80 --yes
```

4. Review the generated `manifest.json`, `raw.txt`, `messages.jsonl`, `messages.md`, and `messages.csv` under the output directory.

## Workflow

- Prefer `export` for the normal automated flow: focus WeChat, select/copy visible message text, scroll upward, repeat, deduplicate, and write outputs.
- Use `from-clipboard` when the user manually selects/copies chat text first and only wants parsing/export.
- Use `discover` when the WeChat window is not found or when multiple candidate windows exist; use `discover --all` only for troubleshooting window titles/classes.
- If `drag` selection produces empty captures, retry with `--select ctrl-a`; if that still fails, use manual selection plus `from-clipboard`.

## Useful Options

```powershell
py C:\Users\84365\.codex\skills\wechat-chat-export\scripts\wechat_chat_export.py export --cycles 120 --title "WeChat" --select drag --yes
py C:\Users\84365\.codex\skills\wechat-chat-export\scripts\wechat_chat_export.py export --cycles 40 --select ctrl-a --yes
py C:\Users\84365\.codex\skills\wechat-chat-export\scripts\wechat_chat_export.py from-clipboard
```

- `--cycles`: number of copy/scroll attempts.
- `--title`: substring used to choose a WeChat window.
- `--select drag`: drag-select the message pane before copying.
- `--select ctrl-a`: click the message pane, then send Ctrl+A/C.
- `--pane-left`, `--pane-top`, `--pane-right`, `--pane-bottom`: ratios for the chat history pane inside the WeChat window. Tune these if the script selects the wrong area.

## Verification

Check `manifest.json` for capture counts and warnings. Open `raw.txt` first; if it contains the expected messages but parsed files look weak, preserve `raw.txt` and improve parsing heuristics before rerunning destructive cleanup.

## Troubleshooting

- Empty output usually means the input box, not the message pane, had focus. Click the message history area and retry.
- If WeChat is running as administrator, run the terminal/Codex with the same privilege level or Windows may block synthetic input.
- OCR is not included. Images, stickers, voice messages, and files are exported as visible copied placeholders or filenames only when WeChat puts them on the clipboard as text.
- Duplicate or partial messages can happen when the same viewport is copied across adjacent scroll cycles; use raw captures as the source of truth.
