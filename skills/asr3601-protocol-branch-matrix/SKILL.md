---
name: asr3601-protocol-branch-matrix
description: Maintain and use the local ASR3601/Crane SDK protocol reference library for APP, XCX/小程序, YL, AKQ, platform, and branch-support questions. Use when the user provides protocol PDFs/DOCX/XLSX/images/text to save or update, asks “这个上报符合协议吗”, “APP协议/小程序协议/YL/AKQ 是哪条路径”, “平台侧还是代码原因”, “当前版本有没有支持这个协议”, “这个分支能不能移植/是否已经合入”, or needs protocol evidence compared with current ASR3601 firmware code. Route concrete bug fixes to asr3601-lvgl-firmware-triage, cross-branch ports to asr3601-cross-branch-porting, and pure Zentao fetching/listing to zentao-bug-triage.
---

# ASR3601 Protocol Branch Matrix

Use this skill as the protocol and branch-support front door. It keeps protocol documents in the user's Obsidian vault and uses them to decide whether a behavior belongs to firmware code, APP/XCX/YL/AKQ protocol mismatch, platform parsing, or branch/product support.

## Fixed Paths

Protocol library:

```text
C:\Users\84365\Documents\Obsidian\CodexVault\Codex\references\asr3601-protocols
```

Required files:

```text
raw\        original protocol files, never overwritten
extracted\  searchable Markdown/text extracted from originals
index.md    file versions, applicability, keywords, source mapping
matrix.md   APP / XCX / YL / AKQ / platform path and branch matrix
```

Do not store credentials, API keys, passwords, tokens, or private login material.

## Protocol File Update Workflow

When the user sends a new or updated protocol file:

1. Save the original under `raw\` with a date/version/source name such as `YYYYMMDD-app-protocol-v3-user.pdf`.
2. Extract searchable text into `extracted\` when practical:
   - PDF: use available PDF tooling or text extraction.
   - DOCX/XLSX: use structured document/spreadsheet tooling when available.
   - Image/screenshot: visually inspect and transcribe only the relevant protocol fields.
3. Update `index.md` with protocol name, version/date, original file, extracted file, applicable project/branch/path, keywords, and replacement relationship.
4. Update `matrix.md` when the protocol changes APP, XCX/小程序, YL, AKQ, platform, branch support, command fields, report functions, or known caveats.
5. Preserve old versions. Mark superseded versions in `index.md` instead of overwriting them.

If extraction is incomplete, record the gap in `index.md` and continue with the usable evidence.

## Protocol Question Workflow

For “是否符合协议/哪边问题/当前分支是否支持”:

1. Identify the protocol path:
   - APP
   - XCX / 小程序
   - YL
   - AKQ
   - platform/common backend
   - unknown, needs evidence
2. Search `index.md`, `matrix.md`, and only the relevant extracted protocol files with concrete terms from the user request:
   - command/event/report name
   - field name
   - enum value
   - platform name
   - code filename/function if provided
3. Inspect the current project branch when code comparison is needed:

```powershell
git status --short
git branch --show-current
git rev-parse --short HEAD
```

4. Search firmware code by stable clues from the protocol, not by broad guesses:
   - APP/XCX/YL/AKQ keywords
   - report/event/function names
   - field names and enum values
   - known project terms such as `akq_xcx_protocal`, `yl`, `ylsc_show`, `AquaBot`, `IMEI`, `ICCID`, `location`, `battery`, `SIM`
5. Decide with one of these labels:
   - 固件未发送
   - 固件发送字段不一致
   - 平台未识别
   - 当前分支不支持
   - 其他分支已支持，当前缺失
   - 产品/客户/平台变体差异
   - 协议资料不足

Always cite decisive evidence: protocol file/version, `matrix.md` row, code file/function, branch/commit, log line, or missing runtime proof.

## Routing Rules

- Pure “抓 bug/当前 bug/禅道有哪些 bug”: use `zentao-bug-triage`.
- Concrete bug report with screenshots/logs/repro steps: use `asr3601-bug-intake-orchestrator`, then return here only for protocol ambiguity.
- Current-branch firmware code fix: use `asr3601-lvgl-firmware-triage` after this skill frames the protocol conclusion.
- Cross-branch or sibling-project migration: use `asr3601-cross-branch-porting` after identifying source/target protocol support.
- Verified reusable protocol fixes: update `Codex\fix-patterns\` through `obsidian-fix-pattern-memory` unless the user says not to record.
- Release packaging for AKQ: use `akq-firmware-release`; this skill only decides protocol support and evidence.

## Output Shape

For protocol file updates:

```text
已保存原件：
已提取文本：
已更新索引：
已更新矩阵：
未完成/需要补充：
```

For protocol/code decisions:

```text
结论：
协议路径：
当前分支/提交：
协议依据：
代码依据：
属于哪一侧：
下一步：
风险/缺口：
```

If the next step is a code fix or port, explicitly name the specialist skill to enter next.
