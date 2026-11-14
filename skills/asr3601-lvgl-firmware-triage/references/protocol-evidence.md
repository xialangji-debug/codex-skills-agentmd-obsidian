# Protocol References And Branch Support

Use this mode directly for protocol imports, report compliance, firmware/platform attribution, or branch-support comparisons. It does not require a Bug, a source fix, or project preparation. Keep protocol documents in the work Vault and use the applicable source/version to distinguish firmware code, APP/XCX/YL/AKQ mismatch, platform parsing, and branch/product support.

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

Keep original Markdown bytes unchanged. For originals without frontmatter,
register each exact `raw/` path and SHA-256 under `external_sources` in this
library's `index.md`; never refresh a mismatched hash without investigating.
The architecture audit validates registered originals and their local links.
Give extracted Markdown the required Vault frontmatter: `area: engineering`,
`domains: [asr]`, `scope: [topic/protocol]`, `kind: source-extract`,
`codex_access: read`, `trust: derived`, `lifecycle: active`, and a relative
`source` path to its original. Preserve extraction gaps and evidence limits.

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
3. For code comparison, reuse the current task snapshot or inspect the relevant
   live branch/version and parser/formatter. Read only the identity fields that
   determine protocol applicability. A generated protocol label is a search hint;
   confirm active support in source/configuration and the applicable document.
   Refresh stale facts needed by the comparison, not the full build/device/Zentao
   context for every field question.

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
- Concrete bug report with screenshots/logs/repro steps: use `asr3601-lvgl-firmware-triage` for the direct Codex investigation, then use this reference only for protocol ambiguity.
- Current-branch firmware code fix: use `asr3601-lvgl-firmware-triage` after this mode frames the protocol conclusion.
- Cross-branch or sibling-project migration: use `asr3601-cross-branch-porting` after identifying source/target protocol support.
- Verified reusable protocol fixes: update `Codex\fix-patterns\` through `obsidian-fix-pattern-memory` unless the user says not to record.
- Release packaging for AKQ: use `akq-firmware-release`; this mode only decides protocol support and evidence.

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
