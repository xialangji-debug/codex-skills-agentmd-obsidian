---
name: zentao-bug-triage
description: Login to YueLan Zentao, fetch assigned or project bugs by current firmware branch/version, open each selected bug detail, parse history records and latest reactivation notes, download attachments/logs, inspect current-branch code one bug at a time, compare bug creation/update/reactivation time with relevant git commits to judge whether it was already fixed, save local bug/requirement snapshots, classify each issue as UI, app/protocol, low-level, platform, or unclear, estimate difficulty, and produce a cautious action table before any code changes. Use when working in ASR3601/ASR3602/360x Crane/LVGL firmware projects and the user says 当前bug, 看看当前bug, 当前分支bug, 有哪些bug, 禅道, Zentao, 抓bug, 版本bug, 需求差异, 下载日志, Bug分类, 一个个查代码, 判断修复过没有, 激活后还有问题, or asks whether assigned bugs can be handled.
---

# Zentao Bug Triage

Use this skill to turn Zentao bugs into a branch-aware triage table before editing firmware code.

## Safety Rules

- Do not store the Zentao password in `SKILL.md`, Obsidian, GitHub, final answers, logs, or generated reports.
- Load credentials only from `%USERPROFILE%\.codex\secrets\zentao-bug-triage\zentao.credential.xml` or ask the user if that file is missing/rejected.
- Do not blindly fix a bug after fetching it. First report whether it exists in the current branch, likely module, difficulty, logs needed, and whether Codex can handle it.
- Do not directly handle low-level hardware/driver/power/modem/platform-server bugs. Give evidence, needed logs, and a suggested owner/debug path.
- Use current-project fetching by default in firmware workspaces: resolve the branch/version through `references/project-map.md`, fetch that Zentao project, and fall back to assigned bugs when no confirmed mapping exists, when project ID discovery fails, or when the project/list page returns zero rows.
- Download attachments/logs automatically for selected bug IDs, log-needed bugs, or common log/video/image attachments, and keep them under the local snapshot folder.
- Always treat `triage.md` as the full snapshot, `work-items.md` as the temporary repair queue, and `ignored-items.md` as the temporary skip/waiting list.
- Always treat `chat-summary.md` as the user-facing conversation table. After fetching bugs, paste this compact table in the chat; do not make the user open Markdown files just to choose bug IDs.
- Put bugs that Codex should inspect, fix, or present as user-selectable candidates into `work-items.md`. Put platform/backend, low-level/hardware/driver, log-needed-without-evidence, unclear-without-expectation/evidence, or already closed bugs into `ignored-items.md` with the reason.
- Later fix requests should read `work-items.md` first and use the bug's full description, result, expected behavior, and attachment paths instead of judging from titles only. If an item is list-only, deep-fetch that bug ID before editing code.
- For bugs that were solved and then reactivated by testing, treat the latest activation history note as the current source of truth. Put its version, result, expected behavior, screenshots, logs, and activation time before the original description in `work-items.md`.
- After all selected bugs are fixed and no longer need local evidence, clean only temporary `work-items.md`, `ignored-items.md`, and `attachments/` with the script cleanup command; keep `bugs.json` and `triage.md` unless the user asks to remove the whole snapshot.
- When the user asks to inspect selected bugs, do not stop at the fetched list or classification table. Open each bug detail, read the full steps/result/expected text, download every available attachment, inspect the owning code path, and compare the bug timestamp against relevant git commits before concluding.
- If a bug looks fixed by code but may still reproduce, or if code evidence cannot prove runtime behavior, explicitly ask for the exact missing evidence: CATStudio log, device log, video, repro time, firmware file name/version, or platform/backend packet trace.
- Preserve unrelated local source changes.

## Trigger and Scope Rule

- Treat short requests such as “看看当前bug”, “当前bug”, “这个分支有哪些bug”, and “看禅道bug” as this workflow when the current workspace or version tokens indicate an ASR3601/ASR3602/360x Crane/LVGL firmware project.
- Recognize these workspace/version clues: `gui/lv_watch`, `product/craneg_modem`, `yl.h`, `yl_device_ver`, `yl_hw_ver`, `ASR3601`, `ASR3602`, `3601`, `3602`, `360x`, `crane`, `TW10`, `TW18`, `C10`, `LT52`, `JC2`, `JC8`.
- If the same short request appears outside this firmware family, ask one short confirmation before logging in to Zentao.
- When both `asr3601-lvgl-firmware-triage` and this skill apply, use firmware triage for code reasoning and this skill for Zentao fetching, bug detail snapshots, attachments, classification, and time-vs-commit judgment.

## Standard Workflow

1. Identify local context:
   - Run `git status --short`, `git branch --show-current`, and `git rev-parse --short HEAD`.
   - Read `gui/lv_watch/lv_apps/yl/yl.h` when present and extract `yl_device_ver`, `yl_device_name`, and product tokens.
   - Match the branch/product with `references/project-map.md`. If ambiguous, ask before choosing a Zentao project.

2. Fetch bugs:
   - Prefer `scripts/zentao_bug_snapshot.js`.
   - For current branch/project bugs, use the default current-project mode:

```powershell
$env:NODE_PATH="$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules"
node "$env:USERPROFILE\.codex\skills\zentao-bug-triage\scripts\zentao_bug_snapshot.js" --repo . --limit 80
```

   - The script reads `references/project-map.md`, matches `git branch --show-current` plus `yl_device_ver`, loads/saves a local project-id cache, discovers the Zentao project ID from `project-browse.html`/`program-browse.html`, fetches `project-bug-<id>.html`, records the selected project in the snapshot, and automatically falls back to assigned bugs when no confirmed mapping matches, project ID discovery fails, or the project/list page returns zero rows.
   - When this assigned fallback is used for a mapped current project, the script deep-fetches candidate assigned rows and keeps only bugs whose detail page product matches the mapped project. Do not treat the first empty project table as “no bugs” unless the fallback is also empty.
   - `--limit` controls how many list rows to capture. `--detail-limit` controls how many bugs to open fully; default is 20 so large projects do not time out. Rows beyond that are kept as list summaries and can be deep-fetched later with `--ids`.
   - Use `--bug-status unresolved` to fetch the project’s unresolved/active bug tab first when the user asks what still needs fixing.
   - For a fast current-unresolved list without detail pages:

```powershell
$env:NODE_PATH="$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules"
node "$env:USERPROFILE\.codex\skills\zentao-bug-triage\scripts\zentao_bug_snapshot.js" --repo . --bug-status unresolved --detail-limit 0 --no-download-attachments
```

   - For selected bugs that the user wants fixed next, deep-fetch IDs and generate the temporary detailed work order:

```powershell
$env:NODE_PATH="$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules"
node "$env:USERPROFILE\.codex\skills\zentao-bug-triage\scripts\zentao_bug_snapshot.js" --repo . --ids 2957,2937 --download-attachments
```

   - Each snapshot writes:
     - `triage.md`: all fetched bugs and first-pass handling decision.
     - `chat-summary.md`: compact chat table with ID, title, category, handling suggestion, attachment type, and whether Codex can inspect/fix first. Paste this table into the final answer after every fetch.
     - `work-items.md`: bugs Codex should inspect/fix next, plus candidate bugs that have a clear expected result or attachment evidence and should be shown to the user for selection.
     - `ignored-items.md`: bugs to skip this round, wait for logs/confirmation, or send to platform/driver/hardware owners.
   - The deep-fetch command fills `work-items.md` with full detail, history records, latest activation note, and attachment paths. Before later fixing “这些bug”, read the latest or user-specified `work-items.md` first and base the fix on its detail fields and attachments.
   - For bugs assigned to the user regardless of project:

```powershell
$env:NODE_PATH="$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules"
node "$env:USERPROFILE\.codex\skills\zentao-bug-triage\scripts\zentao_bug_snapshot.js" --repo . --assigned --limit 80
```

   - For a specific Zentao product/project, pass `--project-id`, `--project-name`, or `--project-key` after confirming the mapping.
   - Attachment mode defaults to `auto`; pass `--download-attachments` to force all detail attachments, or `--no-download-attachments` to skip downloads.
   - Pass `--no-work-md` only when no temporary repair/ignored queue files are needed.
   - Pass `--write-obsidian` only when the user wants the triage summary saved to the Obsidian vault; otherwise keep snapshots under `.codex` only.

3. Classify and report:
   - Read `references/classification-rules.md` before judging a fetched table.
   - Produce a compact chat table with: ID, title, category, handling suggestion, attachment type, and whether Codex can inspect/fix first. Keep this table in the response even when snapshot paths are also provided.
   - Keep detailed metadata in `triage.md`; do not paste the full wide triage table into chat unless the user asks for all details.
   - For each bug, state whether it enters `work-items.md`, needs deep-fetch first, waits for logs/confirmation, defers to platform/backend, or defers to hardware/driver owner.

4. Deep code investigation for selected bugs:
   - Trigger this when the user provides bug IDs, says “一个个查代码”, “判断修复过没有”, “看这些需要修改的”, or asks for current-branch existence.
   - If a snapshot `work-items.md` already exists for the selected bugs, read it before code inspection and treat it as the source of truth for description, actual result, expected result, and attachments.
   - Do not use `ignored-items.md` as a repair queue unless the user explicitly moves an item back into scope or provides the missing logs/confirmation.
   - For every selected bug, perform the same loop before reporting the final judgment:
     1. Open the full Zentao detail and record status, created/opened time, last edited/resolved time, activation count, latest activation time/note, steps, actual result, expected result, and attachments.
     2. Download attachments with `--download-attachments`; inspect videos/logs when they are present.
     3. Search the narrow owning code path first by title keywords, UI text, enum/function names, protocol fields, timers, and affected modules.
     4. Trace entry event -> state write/read -> UI/status refresh -> timer/alarm/network side effect. Cite concrete functions/files.
     5. Run targeted git history for the owning files using the bug time window. For reactivated bugs, use the latest activation time as the key lower bound, for example `git log --all --since=<before-activation-date> -- <files>`. For new bugs, use the bug creation time.
     6. Compare bug created/updated/resolved time with commit time:
        - Commit before bug creation and status still active: treat as not fixed or regression unless code proves the report is stale.
        - Commit before the latest activation and the activation note says the issue still reproduces: treat the previous fix as failed or incomplete.
        - Commit after the latest activation and directly touches the owning path: mark as possibly fixed only if the diff covers the activation note's current symptom.
        - Commit after bug creation and touches the owning path: mark as likely fixed only if the diff directly covers the symptom.
        - Current checkout behind the fixing commit: say the current build does not include the fix.
        - Zentao solved but current checkout lacks the fixing commit: say solved upstream but not present here.
     7. Decide one of: exists, already fixed in current checkout, fixed upstream but missing here, likely fixed but needs runtime proof, not enough evidence/log needed, or not Codex-owned.
   - Do not edit code during this step unless the user explicitly says to fix after reading the investigation.

5. Save local memory:
   - Keep machine-readable snapshots under `%USERPROFILE%\.codex\zentao-bug-triage\snapshots\`.
   - Keep temporary repair and skip/waiting files as `work-items.md` and `ignored-items.md` in the snapshot folder only. These files are for short-term fixing and should not be copied to Obsidian by default.
   - After all bugs in a snapshot are fixed, clean temporary evidence with:

```powershell
$env:NODE_PATH="$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules"
node "$env:USERPROFILE\.codex\skills\zentao-bug-triage\scripts\zentao_bug_snapshot.js" --cleanup "<snapshot-dir>"
```

   - Write a compact Markdown summary under `C:\Users\84365\Documents\Obsidian\CodexVault\Codex\projects\zentao\` only when the user explicitly asks to save/update memory or the script is run with `--write-obsidian`.
   - Save only reusable branch/version context, bug summary, classification, and local paths to downloaded attachments. Do not save passwords or full private chat.

6. Code investigation gate:
   - Only inspect or edit code after the user chooses one or more bug IDs or asks “看这些需要修改的”.
   - For selected UI/app/protocol bugs, check whether the issue exists in the current checkout before proposing changes.
   - For low-level bugs, report required device evidence instead of editing.
   - When reporting after code inspection, include: Zentao evidence, code evidence, commit/time evidence, conclusion, needed logs/videos, and whether Codex should fix it now.

## Resources

- `scripts/zentao_bug_snapshot.js`: login, resolve current branch to a Zentao project, fetch project/assigned/selected bugs, classify, auto-download relevant attachments, save JSON/Markdown snapshots, generate temporary `work-items.md`/`ignored-items.md`, and clean temporary work orders/attachments.
- `references/classification-rules.md`: category, difficulty, and “can Codex handle” rules.
- `references/project-map.md`: current branch/version tokens to Zentao project/product names.
- `references/local-storage.md`: snapshot and Obsidian storage conventions.
