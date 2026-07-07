---
name: weflow-chat-export-analysis
description: Export and analyze local WeFlow or WeChat chat history that the user can access on this Windows PC. Use when the user asks to export WeFlow/WeChat conversations, repeatedly retrieve chat records, analyze a group chat, export messages and images, continue analysis from a WeFlow session ID, or build reports from local chat history without reading or decrypting raw WeChat databases directly.
---

# WeFlow Chat Export Analysis

## Safety Boundary

Use this skill only for chats the user can already access on this Windows account through WeFlow or WeChat. Keep processing local. Do not upload chat logs, images, WeFlow keys, API keys, tokens, or raw database files to external services unless the user explicitly asks and understands the privacy impact.

Prefer WeFlow's own export worker over direct database access. The bundled script reads WeFlow's local configuration, decrypts only the WeFlow `safe:` fields needed by the worker in process memory, and does not write decrypted keys to disk or reports.

## Quick Start

Run the bundled exporter:

```powershell
py C:\Users\84365\.codex\skills\weflow-chat-export-analysis\scripts\weflow_chat_export.py --session-id 45018762878@chatroom --chat-name "Agent 合成反应堆" --output-dir C:\Users\84365\Documents\WeFlow-Exports\agent-reactor --analyze
```

If the user does not know the session ID, try the current or last WeFlow session:

```powershell
py C:\Users\84365\.codex\skills\weflow-chat-export-analysis\scripts\weflow_chat_export.py --session-id last --analyze
```

The script writes a WeFlow raw JSON export plus derived files beside each session:

- `messages-full.md`: readable message timeline
- `messages-full.jsonl`: normalized records for programmatic analysis
- `messages-full.csv`: spreadsheet-friendly table
- `images-index.md`: image thumbnails, paths, sizes, SHA256
- `manifest-full.json`: counts, time range, file list
- `analysis-brief.md`: deterministic stats and leads for the agent to inspect

## Workflow

1. Identify the target chat. Use a known session ID such as `45018762878@chatroom`, or use `--session-id last` when the user means the last selected WeFlow conversation.
2. Run `scripts/weflow_chat_export.py` with `--analyze` and `--include-images` unless the user only wants text.
3. Read `manifest-full.json` first for counts, time range, and derived file paths.
4. Read `messages-full.md` or `messages-full.jsonl` for the conversation text.
5. Read `images-index.md`, then inspect referenced image files when image content affects the answer.
6. Produce the user's requested analysis in Chinese, citing local output paths and concrete message/image numbers.

## Useful Options

- `--session-id <id>`: Export one session. May be repeated. Use `last` to use WeFlow's `lastSession`.
- `--chat-name <name>`: Human-readable name used in derived reports.
- `--output-dir <dir>`: Root export directory. If omitted, the script creates a timestamped folder under `Documents\WeFlow-Exports`.
- `--since YYYY-MM-DD` and `--until YYYY-MM-DD`: Filter derived Markdown/CSV/JSONL outputs after export. The raw WeFlow JSON remains complete.
- `--no-images`: Export text without image media.
- `--app-src <dir>`: Use an already extracted WeFlow `app.asar` source directory if auto-detection fails.
- `--refresh-app-src`: Re-extract WeFlow `app.asar` into the script cache.

## Failure Handling

If export fails because `exportWorker.js` cannot be found, rerun with `--refresh-app-src`; the script will try to extract WeFlow's `app.asar` using `npx --yes @electron/asar`.

If secret decryption fails, make sure the command runs as the same Windows user that installed and uses WeFlow. Do not ask the user to paste decrypted keys into chat.

If message counts look right but nicknames remain as `wxid_...`, continue the analysis anyway and refer to speakers by visible IDs; WeFlow contact cache may not contain every group member name.
