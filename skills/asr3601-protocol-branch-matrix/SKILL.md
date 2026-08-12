---
name: asr3601-protocol-branch-matrix
description: Maintain and use the local ASR3601/Crane SDK protocol reference library for APP, mini-app, vendor, platform, and branch-support questions. Use when the user provides protocol PDFs/DOCX/XLSX/images/text to save or update, asks whether a report follows the protocol, which path owns it, whether it is platform-side or firmware-side, whether the current version supports it, or whether a branch can receive the change. Route concrete bug fixes to asr3601-lvgl-firmware-triage, cross-branch ports to asr3601-cross-branch-porting, and pure Zentao fetching/listing to zentao-bug-triage.
---

# ASR3601 Protocol Branch Matrix

Use this skill as the protocol and branch-support front door. It keeps protocol documents in the user's Obsidian vault and uses them to decide whether a behavior belongs to firmware code, APP/mini-app/vendor protocol mismatch, platform parsing, or branch/product support.

## Fixed Paths

Protocol library:

```text
%USERPROFILE%\Documents\Obsidian\CodexVault\Codex\references\asr3601-protocols
```

Required files:

```text
raw\        original protocol files, never overwritten
extracted\  searchable Markdown/text extracted from originals
index.md    file versions, applicability, keywords, source mapping
matrix.md   APP / mini-app / vendor / platform path and branch matrix
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
4. Update `matrix.md` when the protocol changes APP, mini-app, vendor, platform, branch support, command fields, report functions, or known caveats.
5. Preserve old versions. Mark superseded versions in `index.md` instead of overwriting them.

If extraction is incomplete, record the gap in `index.md` and continue with the usable evidence.

## Protocol Question Workflow

For “是否符合协议/哪边问题/当前分支是否支持”:

1. Identify the protocol path:
   - APP
   - XCX / 小程序
   - YL
   - vendor protocol
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

   Read `.codex-project/variant.md` first when present. Confirm repo, branch, commit, `yl_device_ver`, chip, OS, protocol, customer/product variant, build parameters, and Zentao mapping. If the fingerprint disagrees with current Git or `yl.h`, refresh it with `asr3601-project-onboard` and do not reuse the stale protocol conclusion.

4. Search firmware code by stable clues from the protocol, not by broad guesses:
   - APP/mini-app/vendor keywords
   - report/event/function names
   - field names and enum values
   - known project terms discovered from the current checkout and private project context; do not bundle customer-specific identifiers
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
- Concrete bug report with screenshots/logs/repro steps: use `asr3601-lvgl-firmware-triage` for the direct Codex investigation, then return here only for protocol ambiguity.
- Current-branch firmware code fix: use `asr3601-lvgl-firmware-triage` after this skill frames the protocol conclusion.
- Cross-branch or sibling-project migration: use `asr3601-cross-branch-porting` after identifying source/target protocol support.
- Verified reusable protocol fixes: update `Codex\fix-patterns\` through `obsidian-fix-pattern-memory` unless the user says not to record.
- Release packaging: use the project-local private release workflow; this skill only decides protocol support and evidence.

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
