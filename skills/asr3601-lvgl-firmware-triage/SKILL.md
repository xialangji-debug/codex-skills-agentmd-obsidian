---
name: asr3601-lvgl-firmware-triage
description: Perform code-level triage, explanation, primary-Codex fast fixes, reference-driven LVGL UI planning, and read-only feature-closure audits for ASR3601/ASR3602/Crane SDK children-watch firmware. Use for a direct current-branch request involving one concrete local issue, UI screenshots/videos/effect drawings, encoder/key interaction, resources, protocol, power, SIM, location, watch/phone/sport variants, or requests such as 根据记忆修改, 功能裁剪完整吗, 客户版去掉XX, 只保留XX, 公版派生, and 菜单隐藏但还上报. Route batch, local-model, branch, device, release, or remote-write work to the owning global specialist Skill. Answer existence before edits when asked and finish with 存在/原因/修改/影响/验证/风险.
---

# ASR3601 LVGL Firmware Triage

Use this skill for code-level investigation and narrow firmware fixes after the bug has a concrete frame. If the task is mixed intake or needs branch, device, release, or remote-write operations, let primary Codex route those steps to their owning global specialist Skills.

## Start Here

1. Read local project instructions first: `AGENTS.md`, build notes, and any user-attached screenshots, videos, logs, PDFs, or protocol notes.
2. Read `.codex-project/variant.md` when present. In Fast Fix Mode confirm repo, branch, commit, dirty state, target variant, and the narrow build command once; refresh only a required missing or stale fact. For controlled delivery, protocol, device, release, or Zentao work, confirm the complete dynamic fingerprint and refresh it through `asr3601-project-onboard` when needed.
3. Identify the active workspace and product variant before editing. Distinguish at least:
   - `D:\XM\360x_202403r1`
   - `D:\XM\crane-2024.03_r4`
   - standard watch, sport watch, and phone/simulator targets
4. If the user asks “有没有/能不能做/先告诉我”, answer the existence and feasibility question before making edits.
5. Prefer `rg`, CodeGraph, and existing project symbols/resources over broad filesystem scanning or invented names.
6. Avoid changing unrelated variants. If the user says “不动运动版” or similar, explicitly preserve that boundary.

## Fast Fix Mode

Use this mode when all of these are true:

- the request is in a direct Codex project conversation;
- it is one concrete issue in one repository on the current branch;
- the change is local source only and is expected to touch no more than five files;
- it needs no branch switch, device action, release, Zentao write, batch operation,
  or user-selected local model.

Keep the path short:

1. Read project instructions and check repo, branch, short commit, and dirty state
   once. Preserve unrelated user changes; inspect and work with relevant existing
   edits instead of reverting them.
2. If the user explicitly says “根据记忆/读取记忆”, or the issue is clearly a
   regression/similar issue, search `fix-patterns/` with one to three precise terms.
   Read the top three relevant notes when three exist; otherwise read only genuine
   matches. Do not scan the vault. Lookup alone is read-only.
3. Run one focused search pass across the target code and, when useful, one Git
   history query for the known fix. Do not browse Zentao, start an
   inner Codex plan, invoke a worker, or poll another task.
4. Let primary Codex edit the smallest correct change directly. Keep the edit on
   the current branch and inside the identified files.
5. Inspect the target diff, run `git diff --check`, and run one narrow documented
   test or build. Do not expand to a full release or device workflow.
6. Return the result in the normal triage report. Keep interim updates to at most
   three unless a long-running build genuinely needs another status update.

Do not invoke `local-coder-executor`, a second Codex review, or
`asr3601-fix-closeout-reporter` in Fast Fix Mode. After an actual behavior-changing
fix and its narrow verification, call `obsidian-fix-pattern-memory` once: update an
exact high-confidence root-cause note or create a complete working note, then add
the current target row. Static/build evidence remains working, never device/QA
verified. If scope grows beyond five files, primary Codex may continue after
explaining the new scope; route an excluded branch, device, release, or remote-write
boundary to its owning global specialist Skill.

## Mandatory Evidence Gate

Before editing, obey these gates:

- If the user asks “有没有/还存在吗/先告诉我/能不能做”, answer that status from evidence first.
- If a screenshot, video, log zip, CATStudio folder, protocol PDF, or named artifact is attached, inspect that artifact before broad code theory.
- If a CATStudio zip/folder/.icl is attached, use `catstudio-log-extractor`; for broad triage prefer `--evidence-pack`.
- If the task is similar issue, regression, or cross-branch, perform the narrow `fix-patterns/` lookup through `obsidian-fix-pattern-memory`.
- After a Fast Fix, verify inline as defined above. Use `asr3601-fix-closeout-reporter` only for explicit closeout/validation-debt requests or the full controlled-delivery path.

## Intake Routing

Before deeper investigation, classify the request:

```text
普通当前分支缺陷：
跨分支/跨版本移植：
类似问题/回归：
日志/截图/协议证据分析：
只问能不能做/有没有：
功能新增/裁剪闭包审计：
```

- If the task is ordinary current-branch triage, continue in this skill.
- If the task asks whether a customer feature is fully added, removed, retained, or still reported after its UI is hidden, use Feature Closure Mode below before proposing edits.
- If the task clearly says “移植/别的版本/当前分支/另一个工程/其他型号/同类问题/回归” or needs source-target comparison, use `asr3601-cross-branch-porting` as the specialist workflow after this classification.
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

## Reference UI Mode

When the input is a video, effect drawing, screenshot set, or “replace the old UI” request, first produce and confirm:

- page/state inventory and old-UI removal boundary;
- encoder, key, touch, timer, and back-behavior mapping;
- resource, font, language, and screen-resolution constraints;
- animation, scrolling-text, focus, timeout, and persistence behavior;
- implementation order and a page-by-page acceptance matrix.

Then implement in small target-native steps. Verify page registration, resource indexes, LVGL object lifetime, long-text behavior, and excluded variants. Video appearance is behavioral evidence, not permission to guess hidden states.

## Feature Closure Mode

Keep this mode read-only until the user explicitly asks for code changes.

1. Confirm the repository fingerprint and customer/protocol variant from `.codex-project/variant.md`.
2. Build narrow aliases from the concrete feature name, macros, protocol enums, module names, and Chinese terms. Do not use generic tokens such as `AI` or `AVD` alone.
3. Run the deterministic scanner:

```powershell
python "$env:USERPROFILE\.codex\skills\asr3601-lvgl-firmware-triage\scripts\audit_feature_closure.py" `
  --repo <repo> --feature <功能名> --expected removed `
  --keyword <别名1> --keyword <别名2> --guard <统一开关> `
  --output <报告.md>
```

4. Check build lists, menus/factory UI, initialization/tasks, protocol link/pro/sender/cap paths, and ID/NV definitions. Do not equate a hidden menu with a disabled runtime path.
5. Classify evidence as `present`, `guarded`, `removed`, `compat-retained`, or `needs-review`. Treat the report as static evidence, not as build, device, or platform verification.
6. Preserve protocol enums, Activity/Text/resource IDs, and NV sections by default unless compatibility evidence requires removal.
7. Combine source hits with build lists and ELF map evidence. An unguarded source hit does not prove runtime inclusion when its file is excluded from the build.
8. If the user asks for changes, propose the smallest closure fix, implement only after authorization, rerun the same scan, and pass verification to `asr3601-fix-closeout-reporter`.

Read `references/feature-closure-first-sample.md` only when checking the generic report shape.

## Fix Rules

- Reuse existing text resources; do not invent user-visible Chinese copy when the user asks to find matching text.
- Preserve existing LVGL v7 conventions and helper wrappers.
- Keep layout fixes stable across languages: constrain width, enable scroll/long mode, and account for Russian/Baltic/Bulgarian/Macedonian strings when relevant.
- For low-power, SIM, and location flows, check state priority carefully so a lower-priority reminder does not cover shutdown, low-battery, or power-save UI.
- For screen-size or wallpaper work, verify configured resolution, resource dimensions, and scaling/cropping paths before changing assets.
- For branch/feature porting, compare source and target branches first, then port only the needed files/functions and protect excluded variants.
- Avoid broad refactors unless required to fix shared behavior safely.

## Verification

Run the narrowest available validation from project instructions. In Fast Fix Mode run one narrow test/build after `git diff --check`; do not invoke a separate closeout pass. Prefer simulator/UI build targets when available, for example `make pc_simulator_watch`, `make pc_simulator_watch_sport`, or the target named by `AGENTS.md`. If a build is unavailable, run syntax/search checks and explain the gap.

After verification, record the fix through `fix_memory.py upsert --write`. New
notes must include symptom, root cause, fix, key files/functions, validation method,
and cautions. If the fix came from a fetched Bug, attach its Bug ID. Do not record
explanation-only work, temporary diagnostics, reverted experiments, formatting, or
a change the user explicitly excluded from memory.

For each fix, report:

- 问题是否存在
- 根因
- 修改了什么
- 影响范围，尤其是否影响运动版/手机版/其他语言
- 验证结果或未验证原因
- 记忆记录（note / fix_id / target evidence）
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

Read `references/project-patterns.md` when the task involves one of the recurring project-specific bug types or when you need reminders about preferred search terms and risk checks. Read `references/feature-closure-first-sample.md` only for the generic feature-closure report shape.
