---
name: asr3601-bug-intake-orchestrator
description: Orchestrate first-pass intake for concrete ASR3601/ASR3602/Crane SDK/LVGL children-watch firmware bug reports before deep fixing. Use when the user provides a specific bug report with 重现步骤, 结果/期望, screenshots, videos, CATStudio logs, downloaded Zentao bug detail text, or asks “有没有这个问题”, “存不存在”, “先看是不是修过”, “这个分支还要不要改”, or “先判断再修”. Do not use for pure Zentao/current-bug-list fetching such as “抓 bug/当前 bug/禅道有哪些 bug”; use zentao-bug-triage directly for those. Route to catstudio-log-extractor, asr3601-lvgl-firmware-triage, asr3601-cross-branch-porting, asr3601-fix-verifier, and obsidian-fix-pattern-memory as needed.
---

# ASR3601 Bug Intake Orchestrator

Use this skill as the front door for concrete firmware bug reports. Its job is to turn messy bug evidence into a branch-aware first decision before edits start.

## Core Rule

Classify before editing. If the user asks whether the bug exists, whether it was already fixed, or whether the current branch needs a change, answer that from evidence first.

If the user is asking to fetch or list bugs from Zentao, do not continue here. Use `zentao-bug-triage` directly.

Do not replace specialist skills. Route to them deliberately:

- `zentao-bug-triage`: Zentao/current branch bug lists, bug IDs, assigned bugs, activation history, attachments.
- `catstudio-log-extractor`: CATStudio `.zip`, `.icl/.ild`, extracted log folders, crash/protocol/device evidence.
- `asr3601-lvgl-firmware-triage`: current-branch code reasoning, existence checks, narrow fixes.
- `asr3601-cross-branch-porting`: 移植, similar branch, regression, source/target comparison.
- `asr3601-fix-verifier`: after a patch or port, before final reporting.
- `obsidian-fix-pattern-memory`: similar issue lookup before investigation and reusable fix-pattern write after verified fixes.

## Intake Snapshot

Collect or infer these fields before code edits:

```text
来源：截图 / 复现步骤 / CATStudio / Zentao / 用户口述 / 历史问题
项目路径：
当前分支：
当前提交：
dirty worktree：
产品/协议变体：360x / C10 公版 / C10 乐智 / LT52 / APP 协议 / 小程序协议 / YL / AKQ / 未确认
用户目标：只判断 / 修复 / 移植 / 抓 bug / 关闭禅道 / 写报告
步骤：
实际结果：
期望结果：
附件/日志：
初步模块：
历史记忆命中：
第一结论：
```

For Git workspaces, run non-destructive context checks early:

```powershell
git status --short
git branch --show-current
git rev-parse --short HEAD
```

If the directory is not a Git repo, record `不可用` for branch/commit and continue from artifacts.

## Evidence Gates

Apply the first matching gate:

- Pure bug-list/fetch request: for “抓 bug”, “当前 bug”, “这个分支有哪些 bug”, “看禅道 bug”, or a bare Zentao ID without local detail, use `zentao-bug-triage` first.
- Screenshot/video attached: inspect the visual artifact first. Extract visible page, text, icons, state, and approximate trigger path before searching code.
- CATStudio/log package attached: use `catstudio-log-extractor` with `--fast-evidence` first. Expand to `--evidence-pack` only when the compact evidence is insufficient.
- User says only 禅道/Zentao/当前 bug/抓 bug/有哪些 bug: stop this skill and use `zentao-bug-triage` first.
- User provides already-fetched Zentao detail text, activation note, attachment path, or asks whether a selected bug still exists: continue here, then route to `asr3601-lvgl-firmware-triage` or `asr3601-cross-branch-porting`.
- User says 移植/别的版本/当前分支有没有修过/同类问题/回归: do the Obsidian `fix-patterns/` lookup, then route to `asr3601-cross-branch-porting` if source-target comparison is needed.
- User asks only 有没有/存不存在/是不是修过: inspect likely entry points and history before proposing a patch.
- Protocol/upstream ambiguity: identify whether the behavior belongs to APP, XCX, YL, AKQ, modem/platform, or backend before editing firmware code.

## Memory Lookup

Use the user's Obsidian Markdown vault directly. Do not use Basic Memory MCP.

For similar issues, regressions, cross-branch ports, or clear log/protocol keywords:

1. Choose 1-3 concrete search terms from the symptom, module, protocol field, file name, or bug title.
2. Search only:

```text
C:\Users\84365\Documents\Obsidian\CodexVault\Codex\fix-patterns
```

3. Read only directly relevant matches.
4. If no match is found, stop; do not broaden to the whole vault unless the user explicitly asks for memory review.

Useful project pages when the path is already known:

- `Codex/projects/asr3601-360x_202403r1.md`
- `Codex/projects/asr3601-c10gongban.md`
- `Codex/projects/asr3601-c10lezhi.md`
- `Codex/projects/asr3601-crane-lvgl-watch.md`

## Routing Decision

After the snapshot and evidence gates, choose one path:

```text
纯 Zentao 批量/单号抓取：zentao-bug-triage
已获取 bug 详情后的存在性判断：this skill -> asr3601-lvgl-firmware-triage
日志证据优先：catstudio-log-extractor -> asr3601-lvgl-firmware-triage
当前分支是否存在：asr3601-lvgl-firmware-triage
跨分支/类似修复：obsidian-fix-pattern-memory lookup -> asr3601-cross-branch-porting
已经修改完：asr3601-fix-verifier
平台/硬件/驱动/后端：说明证据和需要的日志，不直接改固件
```

## Trigger Matrix

Use this quick matrix to avoid conflicts:

| User wording | First skill |
|---|---|
| 抓一下当前分支 bug / 看看禅道有哪些 bug | `zentao-bug-triage` |
| bug 2957 帮我下载附件/看详情 | `zentao-bug-triage` |
| 这是重现步骤/截图，先看有没有这个问题 | `asr3601-bug-intake-orchestrator` |
| 已经有 bug 详情和附件路径，判断当前分支是否修过 | `asr3601-bug-intake-orchestrator` |
| 明确让我现在修这个代码问题 | `asr3601-bug-intake-orchestrator` -> `asr3601-lvgl-firmware-triage` |
| 从 LT52/别的版本移植这个修复 | `asr3601-cross-branch-porting` |
| 修完了验证/收尾 | `asr3601-fix-verifier` |

If multiple paths apply, keep this ownership:

```text
本 skill：问题归一化、证据门、路由、第一结论
Zentao：抓取、历史、附件、bug 表
CATStudio：日志提取和 evidence pack
Firmware triage：当前分支代码判断和窄修
Cross-branch：源/目标对比和移植
Verifier：修复后验证和收尾
Memory：历史相似问题查找和可复用经验沉淀
```

## First Decision Labels

Use one of these labels in the first report:

```text
存在，需要修：
当前 checkout 已修：
上游/其他分支已修，当前缺失：
可能已修，但需要设备/日志证明：
未确认，需要补日志/视频/复现时间：
平台/后端/硬件/驱动侧，不建议直接改固件：
需求/产品变体差异，不属于缺陷：
```

For each label, cite the decisive evidence: file/function, commit timing, log line, screenshot state, Zentao activation note, or missing runtime proof.

## Search Strategy

Prefer narrow searches from stable clues:

- UI text, page name, icon/resource name, screenshot-visible state.
- Protocol command, field name, event ID, report package name.
- App/module names such as alarm, phone, akq_xcx_protocal, yl, ylsc_show, AquaBot.
- Bug-specific terms from latest activation note or attachment, not only the title.

Avoid whole-repo sweeps until targeted searches fail.

For time-vs-fix questions, compare bug creation/update/activation time with relevant git commits touching the owning files.

## Output Shape

Before edits, answer in concise Chinese:

```text
第一结论：
当前分支/提交：
证据来源：
历史命中：
疑似模块：
下一步：
需要转入的 skill：
```

When the user then says to fix it, continue through the specialist workflow and finish with:

```text
存在/已修/未确认：
原因：
修改：
影响范围：
验证：
记忆库：
风险：
```

If no memory entry is written after an important reusable fix, say why.
