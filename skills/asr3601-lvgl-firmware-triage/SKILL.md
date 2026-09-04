---
name: asr3601-lvgl-firmware-triage
description: Perform code-level triage, explanation, primary-Codex fast fixes, reference-driven LVGL UI planning, and read-only feature-closure audits for the current ASR3601/ASR3602/Crane SDK project. Use after the project AGENTS.md or .codex-project/index.md routes one concrete current-branch issue here, including existence checks, UI screenshots/videos, encoder/key interaction, resources, power, SIM, location, customer feature removal, and menu-hidden-but-still-reported audits. Route branch, batch, local-model, device, release, or remote-write work to the owning specialist skill. Report 存在/原因/修改/影响/验证/风险.
---

# ASR3601 LVGL Firmware Triage

Investigate and fix one concrete issue in the current project. Project-local documentation identifies the project; do not classify ASR versus ESP32 again inside this skill.

## Entry

1. Read the current repository `AGENTS.md` and `.codex-project/index.md`, then only the task-specific local files they link.
2. For read-only code questions, use current source directly; do not require a complete `variant.md` refresh. Before editing, check branch, HEAD, and dirty state once. Read or refresh dynamic variant facts only when the conclusion or action depends on them.
3. Inspect user-provided screenshots, videos, logs, PDFs, protocol notes, or named artifacts before broad code theory.
4. If the user asks whether something exists or is feasible, answer that from evidence before editing.
5. Preserve unrelated user changes and any explicitly excluded product variant.

## Search

- For a known macro, function, filename, UI text, protocol field, event ID, or error string, use scoped `rg` first.
- For an unknown concept, behavior, or call relationship, use the current project's code index declared in `.codex-project/local.md`.
- Do not run index `status` or `doctor` for a normal question. Use them only when search fails, results are clearly stale, or scope is wrong.
- Treat index results as locators. Confirm every conclusion in live source, Git history, build configuration, or generated build evidence.
- Run one focused search pass, then trace `entry -> state/guard -> update -> resource/storage -> side effect`. For UI issues, inspect both create and refresh paths.
- Load `references/project-patterns.md` only when the issue matches a recurring pattern documented there.

## Fast Fix

Use Fast Fix when the request is one concrete current-branch issue in one repository, is expected to touch at most five local source files, and needs no branch switch, device action, release, Zentao write, batch operation, or user-selected local model.

1. Confirm the user authorized changes. Check branch, HEAD, and dirty state once; preserve unrelated changes.
2. Search `fix-patterns/` narrowly only when the user explicitly requests memory or the issue is a clear regression/similar issue. Read at most three genuine matches.
3. Use one focused code/index search and, when useful, one focused Git history query.
4. Make the smallest correct current-branch edit directly with primary Codex.
5. Inspect the target diff, run `git diff --check`, and run one narrow documented test or build. If the same authorized request immediately continues into formal/FOTA-test pair delivery, do not run a standalone full firmware build here; the pair controller's T/F builds provide that evidence.
6. Report using the triage shape below. Do not start an inner task or run a second closeout workflow.

After a qualifying behavior-changing fix, invoke `obsidian-fix-pattern-memory` once. Static or build evidence remains working evidence, never device or QA proof. If scope grows beyond five files, explain the new scope; route branch, device, release, or remote-write operations to their owning specialist.

## Evidence And Investigation

Use this frame:

```text
现象 -> 可能模块 -> 验证点 -> 修复路径 -> 影响范围 -> 验证方式
```

Extract trigger steps, actual result, expected result, affected page/module, and attached evidence from the user's material. Do not ask again for facts already supplied.

Before proposing a fix:

1. Locate stable clues in code or the project index.
2. Trace the controlling condition and all relevant create/update/callback paths.
3. State whether the behavior exists, does not exist, or remains unconfirmed, with exact code or build evidence.
4. Choose the smallest project-native fix and identify affected/excluded variants.

Use `catstudio-log-extractor` for CATStudio zip/folder/`.icl` evidence. Use `asr3601-cross-branch-porting` when source-target comparison or migration is required. Use the protocol, build/flash, release, Zentao, and closeout specialists only when the request enters those scopes.

## Reference UI

For screenshots, videos, effect drawings, or replacement UI requests, first establish:

- page/state inventory and old-UI removal boundary;
- encoder, key, touch, timer, and back behavior;
- resources, fonts, languages, resolution, animation, focus, timeout, and persistence;
- implementation order and a page-by-page acceptance matrix.

Then implement in small target-native steps. Verify registration, resource indexes, LVGL object lifetime, long-text behavior, and excluded variants. Visual evidence does not authorize guessing hidden states.

## Feature Closure

Keep closure audits read-only until changes are explicitly authorized.

1. Confirm the customer/protocol variant only when it affects the feature boundary.
2. Build narrow aliases from the feature name, macros, protocol enums, module names, and Chinese terms; avoid generic tokens alone.
3. Run the deterministic scanner:

```powershell
python "$env:USERPROFILE\.codex\skills\asr3601-lvgl-firmware-triage\scripts\audit_feature_closure.py" `
  --repo <repo> --feature <功能名> --expected removed `
  --keyword <别名1> --keyword <别名2> --guard <统一开关> `
  --output <报告.md>
```

4. Check build lists, menus/factory UI, initialization/tasks, protocol sender/capability paths, and ID/NV definitions. A hidden menu is not proof that runtime behavior is disabled.
5. Classify evidence as `present`, `guarded`, `removed`, `compat-retained`, or `needs-review`. Combine source hits with build lists and ELF/map evidence; static results are not build, device, platform, or QA proof.
6. Preserve protocol enums, Activity/Text/resource IDs, and NV sections unless compatibility evidence supports removal. After an authorized change, rerun the same scan.

Read `references/feature-closure-first-sample.md` only when the generic report shape is needed.

## Fix And Verification

- Reuse existing text/resources and LVGL v7 conventions.
- Keep multilingual layout stable with explicit width and correct long/scroll mode.
- Check state priority for low-power, SIM, location, timer, wakeup, and callback flows.
- Verify configured resolution, resource dimensions, and scaling/cropping before asset changes.
- Avoid broad refactors unless shared behavior requires them.

Run the narrowest validation documented by the project. In Fast Fix, run `git diff --check` plus one narrow test/build and do not invoke a separate closeout pass. For an immediate FOTA-pair handoff, a source-level targeted check is sufficient before the focused commit; promote to `build_passed` only after both pair builds succeed. If build or device validation is unavailable, state the exact gap.

## Report

Use this concise Chinese shape:

```text
存在/未确认：
原因：
修改/修复路径：
影响范围：
验证：
风险：
```

For an actual behavior fix, also state the fix-pattern note or why no qualifying memory record was written.
