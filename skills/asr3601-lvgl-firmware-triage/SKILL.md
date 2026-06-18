---
name: asr3601-lvgl-firmware-triage
description: Intake, triage, explain, and fix ASR3601/Crane SDK children-watch firmware issues using LVGL v7 project evidence. Use when Codex works in or discusses <ASR3601 工程路径>, <Crane SDK 工程路径>, ASR3601, Crane SDK, LVGL, children-watch firmware, watch/phone/sport variants, low-battery behavior, SIM card removal, overlapping power/SIM popups, location scheduling, IMEI/friend protocol behavior, screen size, wallpaper scaling, charging icons, calculator branch porting, pixel-level UI offset fixes, screenshot-driven UI triage, O2/subscript text display, screenshots, logs, protocol PDFs, cross-branch/similar/regression classification, or user requests like “这个问题有没有/为什么/如何修复/先告诉我能不能做”.
---

# ASR3601 LVGL Firmware Triage

Use this skill to keep firmware bug work evidence-led, scoped to the correct product variant, and easy for the user to judge before or after code changes.

## Start Here

1. Read local project instructions first: `AGENTS.md`, build notes, and any user-attached screenshots, videos, logs, PDFs, or protocol notes.
2. Identify the active workspace and product variant before editing. Distinguish at least:
   - `<ASR3601 工程路径>`
   - `<Crane SDK 工程路径>`
   - standard watch, sport watch, and phone/simulator targets
3. If the user asks “有没有/能不能做/先告诉我”, answer the existence and feasibility question before making edits.
4. Prefer `rg`, CodeGraph, and existing project symbols/resources over broad filesystem scanning or invented names.
5. Avoid changing unrelated variants. If the user says “不动运动版” or similar, explicitly preserve that boundary.

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
