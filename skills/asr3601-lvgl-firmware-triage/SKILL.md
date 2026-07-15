---
name: asr3601-lvgl-firmware-triage
description: Perform code-level triage, explanation, and narrow fixes for ASR3601/Crane SDK children-watch firmware issues using LVGL v7 project evidence. Use after a concrete bug report has been framed, or when the user directly asks to inspect/fix current-branch firmware behavior in D:\XM\360x_202403r1, D:\XM\crane-2024.03_r4, D:\XM\c10gongban, D:\XM\c10lezhi, ASR3601, Crane SDK, LVGL, watch/phone/sport variants, low-battery, SIM, power, location, protocol, UI, O2/subscript, resource, screenshot/log evidence, or “为什么/如何修复/先告诉我能不能做”. For raw bug intake with uncertain routing, use asr3601-bug-intake-orchestrator first. Must answer whether the issue exists before editing when asked and finish with 存在/原因/修改/影响/验证/风险.
---

# ASR3601 LVGL Firmware Triage

Use this skill for code-level investigation and narrow firmware fixes after the bug has a concrete frame. If the task is still a mixed intake problem, let `asr3601-bug-intake-orchestrator` classify it first.

## Start Here

1. Read local project instructions first: `AGENTS.md`, build notes, and any user-attached screenshots, videos, logs, PDFs, or protocol notes.
2. Read `.codex-project/variant.md` when present and confirm repo, branch, commit, dirty state, `yl_device_ver`, chip, OS, protocol, customer/product variant, build parameters, and Zentao mapping. If the fingerprint is missing or stale, refresh it through `asr3601-project-onboard` before editing.
3. Identify the active workspace and product variant before editing. Distinguish at least:
   - `D:\XM\360x_202403r1`
   - `D:\XM\crane-2024.03_r4`
   - standard watch, sport watch, and phone/simulator targets
4. If the user asks “有没有/能不能做/先告诉我”, answer the existence and feasibility question before making edits.
5. Prefer `rg`, CodeGraph, and existing project symbols/resources over broad filesystem scanning or invented names.
6. Avoid changing unrelated variants. If the user says “不动运动版” or similar, explicitly preserve that boundary.

## Mandatory Evidence Gate

Before editing, obey these gates:

- If the user asks “有没有/还存在吗/先告诉我/能不能做”, answer that status from evidence first.
- If a screenshot, video, log zip, CATStudio folder, protocol PDF, or named artifact is attached, inspect that artifact before broad code theory.
- If a CATStudio zip/folder/.icl is attached, use `catstudio-log-extractor`; for broad triage prefer `--evidence-pack`.
- If the task is similar issue, regression, or cross-branch, perform the narrow `fix-patterns/` lookup through `obsidian-fix-pattern-memory`.
- After making a firmware fix, use `asr3601-fix-verifier` before the final report when a local verification path exists.

## Intake Routing

Before deeper investigation, classify the request:

```text
普通当前分支缺陷：
跨分支/跨版本移植：
类似问题/回归：
日志/截图/协议证据分析：
只问能不能做/有没有：
```

- If the task is ordinary current-branch triage, continue in this skill.
- If the task clearly says “移植/别的版本/当前分支/另一个工程/JC2/同类问题/回归” or needs source-target comparison, use `asr3601-cross-branch-porting` as the specialist workflow after this classification.
- If the task is similar issue, regression, or has clear searchable log keywords, perform the narrow Obsidian `fix-patterns` lookup required by the user's `AGENTS.md`; otherwise do not read the whole memory vault.
- If both triage and porting apply, this skill owns the problem frame and `asr3601-cross-branch-porting` owns the migration plan.

## Required Triage Frame

For recurring firmware/UI bugs, keep the investigation in this fixed frame before asking follow-up questions:

```text
现象 -> 可能模块 -> 验证点 -> 修复路径 -> 影响范围 -> 验证方式
```

Use evidence already provided by the user first. If the user provides steps, expected/actual result, screenshots, videos, logs, or a named branch, extract the missing fields yourself instead of asking for them again. Ask only when the active workspace, source branch, target variant, or exclusion boundary cannot be inferred safely.

Load `references/project-patterns.md` when the task matches calculator branch porting, low-battery/SIM overlap, pixel-level UI offsets, screenshot-driven UI triage, or any recurring pattern named there.

## Investigation Workflow

1. Convert the report into a concrete hypothesis:
   - trigger steps
   - observed result
   - expected result
   - involved app/page/module
   - attached evidence such as screenshots, logs, protocol fields, or PDFs
2. Locate code by stable terms from the evidence:
   - UI text keys, screen/page names, enum names, protocol fields, event IDs, timers, callbacks, image/resource names
   - examples: low battery, SIM removal, location plan, friend add, IMEI, charge icon, O2, calculator, wallpaper, screen dimensions
3. Trace behavior before editing:
   - entry event -> state check -> UI update -> resource/text lookup -> timer/network/protocol side effects
   - for UI defects, find both layout creation and update/refresh paths
   - for protocol defects, find parse, storage, display, and acknowledgment paths
4. Decide whether the bug exists:
   - cite the concrete condition or missing branch if it exists
   - say “未确认/未发现” only after checking the likely entry points and evidence
5. Choose the smallest local fix that matches project patterns.

## Recurring Pattern Rules

- For calculator branch porting, compare source and target branches first, identify menu/resource/build-macro differences, port only the needed calculator files/functions, and preserve excluded variants such as sport watch.
- For low-battery, power-save, and SIM-removal overlap, determine state priority before editing. Verify every display path, timer, callback, and refresh path that can reopen the lower-priority popup.
- For pixel-level UI offset fixes, locate both creation and update/refresh code. Prefer local coordinate/style changes scoped to the active page and variant; avoid broad layout refactors or language-breaking hardcoded widths.
- For screenshot-driven triage, extract visible text, icon/resource names, page state, approximate coordinates, and trigger state from the image/video, then search those stable clues before guessing function names.

## Fix Rules

- Reuse existing text resources; do not invent user-visible Chinese copy when the user asks to find matching text.
- Preserve existing LVGL v7 conventions and helper wrappers.
- Keep layout fixes stable across languages: constrain width, enable scroll/long mode, and account for Russian/Baltic/Bulgarian/Macedonian strings when relevant.
- For low-power, SIM, and location flows, check state priority carefully so a lower-priority reminder does not cover shutdown, low-battery, or power-save UI.
- For screen-size or wallpaper work, verify configured resolution, resource dimensions, and scaling/cropping paths before changing assets.
- For branch/feature porting, compare source and target branches first, then port only the needed files/functions and protect excluded variants.
- Avoid broad refactors unless required to fix shared behavior safely.

## Verification

Run the narrowest available validation from project instructions. Prefer simulator/UI build targets when available, for example `make pc_simulator_watch`, `make pc_simulator_watch_sport`, or the target named by `AGENTS.md`. If a full build is unavailable, run syntax/search checks and explain the gap.

For each fix, report:

- 问题是否存在
- 根因
- 修改了什么
- 影响范围，尤其是否影响运动版/手机版/其他语言
- 验证结果或未验证原因
- 剩余风险

Prefer this Chinese final shape for bug triage and fixes:

```text
存在/未确认：
原因：
修复路径/修改：
影响范围：
验证：
风险：
```

## References

Read `references/project-patterns.md` when the task involves one of the recurring project-specific bug types or when you need reminders about preferred search terms and risk checks.
