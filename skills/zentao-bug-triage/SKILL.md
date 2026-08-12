---
name: zentao-bug-triage
description: Fetch and deep-inspect current-project or assigned Zentao bugs, attachments, activation history, memory matches, repair eligibility, and exact-target status changes against the previous local baseline. Use for 当前bug, 当前分支bug, 禅道, 抓bug, bug IDs, downloading evidence, classification, or detecting active-to-resolved/closed and reactivated transitions. It may update local linked fix-pattern target evidence after deterministic status changes, but never writes Zentao; use zentao-bug-resolver for explicit remote resolution.
---

# Zentao Bug Triage

Use this skill to turn Zentao bugs into a branch-aware triage table before editing firmware code.

## Safety Rules

- Do not store the Zentao password in `SKILL.md`, Obsidian, GitHub, final answers, logs, or generated reports.
- Load credentials only from `%USERPROFILE%\.codex\secrets\zentao-bug-triage\zentao.credential.xml` or ask the user if that file is missing/rejected.
- Do not blindly fix a bug after fetching it. First report whether it exists in the current branch, likely module, difficulty, logs needed, and whether Codex can handle it.
- Treat fix-pattern memory as supporting evidence, never as proof that the current branch has the same root cause. Keep `记忆命中` separate from `修复资格`.
- Treat snapshot reconciliation as local evidence only. It never authorizes code edits, branch changes, commits, device actions, releases, or Zentao writes.
- Compare only the exact repository, branch, firmware version, and product/variant identity. Never combine snapshots from similar names or prefixes.
- Missing from the active list is not a transition. Deep-fetch the previously tracked Bug detail before deciding whether it is active, resolved, or closed.
- `已解决` means development resolved and QA is pending. Only `已关闭` or equivalent explicit QA evidence upgrades a linked target to `qa_verified`.
- An increased activation count on the same exact target and materially same symptom downgrades only that target. A changed symptom/variant leaves old verified memory unchanged and becomes a review candidate.
- `可直接修复候选` is only a triage label. Before editing, still deep-fetch the bug, inspect the current code path, check relevant Git history and local changes, and verify that the remembered fix applies to this variant.
- Never mark list-only, reactivated, platform/backend, low-level/hardware/driver, or log-dependent-without-evidence bugs as direct repair candidates.
- Do not directly handle low-level hardware/driver/power/modem/platform-server bugs. Give evidence, needed logs, and a suggested owner/debug path.
- Use current-project fetching by default in firmware workspaces: resolve the branch/version through the private local map at `%USERPROFILE%\.codex\zentao-bug-triage\project-map.local.md`, falling back to the bundled generic template only when the private map is absent. Fetch that Zentao project, and fall back to assigned bugs when no confirmed mapping exists, when project ID discovery fails, or when the project/list page returns zero rows.
- Fetch only bugs whose Zentao status is `active` by default. Do not fetch detail pages or attachments for `resolved` or `closed` bugs unless the user explicitly asks for all, resolved, closed, historical, or regression-review data.
- For current-branch bug fetching, trust only the current Git worktree and branch from `--repo`; do not infer the branch from browser state, an old snapshot, Obsidian memory, or another worktree. In multi-worktree folders, pass `--expect-repo-name` and `--expect-branch` so the script aborts before opening Zentao if the working directory is wrong.
- For a short list/fetch request such as “抓bug”, use the existence-first fast launcher. Do not refresh an existing project fingerprint before fetching merely because the commit or dirty state changed. The launcher fetches from live Git/`yl.h` evidence first, validates the snapshot afterward, and refreshes project context only when it is absent or the post-check finds it stale or inconsistent.
- By default, open the detail page for every fetched bug and download every attachment. Do not use the fast list mode unless the user explicitly asks for a fast/no-attachment listing.
- If a full detail/attachment fetch times out, retry with a longer timeout or higher detail concurrency, or split the same bug IDs into smaller deep-fetch batches and preserve all downloaded evidence. Never fall back to `--detail-limit 0` or `--no-download-attachments`, and never present a list-only snapshot as the completed result, unless the user explicitly requested a fast/no-attachment listing.
- Download attachments/logs automatically for selected bug IDs, log-needed bugs, or common log/video/image attachments, and keep them under the local snapshot folder.
- Always treat `triage.md` as the full snapshot, `work-items.md` as the temporary repair queue, and `ignored-items.md` as the temporary skip/waiting list.
- Always treat `chat-summary.md` as the user-facing conversation table. After fetching bugs, paste this compact table in the chat; do not make the user open Markdown files just to choose bug IDs.
- In every user-facing Markdown snapshot, table, section heading, list, and chat reply, identify a bug as `<数字ID> <单行完整标题>`, for example `3526 计算机界面向右滑动会有点卡顿`. Use exactly one ASCII space between the ID and title; do not add `#`, and do not emit a naked numeric ID.
- Use one combined table column named `Bug（ID + 标题）`; never split user-facing ID and title into separate columns. When a title genuinely cannot be fetched, use `<数字ID> 标题未获取` instead of a bare ID.
- Keep pure numeric IDs in machine-facing data and interfaces such as `bugs.json`, `state-events.json` fields, state keys, URLs, filenames, logs, `--ids`, and script-to-script parameters. The display-label rule must not change those contracts.
- Put bugs that Codex should inspect, fix, or present as user-selectable candidates into `work-items.md`. Put platform/backend, low-level/hardware/driver, log-needed-without-evidence, unclear-without-expectation/evidence, or already closed bugs into `ignored-items.md` with the reason.
- Later fix requests should read `work-items.md` first and use the bug's full description, result, expected behavior, and attachment paths instead of judging from titles only. If an item is list-only, deep-fetch that bug ID before editing code.
- For bugs that were solved and then reactivated by testing, treat the latest activation history note as the current source of truth. Put its version, result, expected behavior, screenshots, logs, and activation time before the original description in `work-items.md`.
- After all selected bugs are fixed and no longer need local evidence, clean only temporary `work-items.md`, `ignored-items.md`, and `attachments/` with the script cleanup command; keep `bugs.json` and `triage.md` unless the user asks to remove the whole snapshot.
- When the user asks to inspect selected bugs, do not stop at the fetched list or classification table. Open each bug detail, read the full steps/result/expected text, download every available attachment, inspect the owning code path, and compare the bug timestamp against relevant git commits before concluding.
- If a bug looks fixed by code but may still reproduce, or if code evidence cannot prove runtime behavior, explicitly ask for the exact missing evidence: CATStudio log, device log, video, repro time, firmware file name/version, or platform/backend packet trace.
- Preserve unrelated local source changes.

## Trigger and Scope Rule

- Treat short requests such as “看看当前bug”, “当前bug”, “这个分支有哪些bug”, and “看禅道bug” as this workflow when the current workspace or version tokens indicate an ASR3601/ASR3602/360x Crane/LVGL firmware project.
- Treat requests to open bug IDs, download attachments, refresh snapshots, or inspect `work-items.md` as this workflow.
- If the user already pasted full bug steps/result/expected text or provided a local attachment path and does not need Zentao fetching, use `asr3601-lvgl-firmware-triage`; re-enter this skill only if additional Zentao history or attachments are needed.
- Recognize these workspace/version clues: `gui/lv_watch`, the modem product tree, the project version header, `ASR3601`, `ASR3602`, `3601`, `3602`, `360x`, and `crane`. Read concrete product/device tokens only from the private local map or `.codex-project/variant.md`.
- If the same short request appears outside this firmware family, ask one short confirmation before logging in to Zentao.
- When both `asr3601-lvgl-firmware-triage` and this skill apply, use firmware triage for code reasoning and this skill for Zentao fetching, bug detail snapshots, attachments, classification, and time-vs-commit judgment.

## Standard Workflow

1. Use the fast initialization gate for the default current-project fetch:
   - Treat the checkout as initialized only when `AGENTS.md` and the generated `.codex-project/{index,zentao,build,protocol,variant,device,memory}.md` files exist.
   - When those files exist, fetch immediately. Do not pre-read or refresh `variant.md`, and do not run separate Git/`yl.h` checks before launching the fetch.
   - When any required file is absent, run `asr3601-project-onboard` first, then fetch.
   - After fetching, validate the snapshot repo, branch, commit, `yl_device_ver`, exact mapped product, active status, detail coverage, and attachment files against live repository evidence. Refresh the project context after a successful fetch when its stable mapping/fingerprint fields are stale. If the snapshot itself is inconsistent, refresh and refetch once.
   - Dirty-worktree differences alone do not make initialization stale for list-only fetching. They remain relevant before code inspection or edits.

2. Fetch bugs:
   - For a normal “抓bug / 当前bug” request, prefer `scripts/zentao_bug_fast_fetch.py`. It performs the initialization gate, live fetch, post-check, and per-Bug attachment retries in one command:

```powershell
python -X utf8 "$env:USERPROFILE\.codex\skills\zentao-bug-triage\scripts\zentao_bug_fast_fetch.py" --repo .
```

   - The fast fetch also runs exact-target reconciliation. On the first fetch it
     creates a baseline. Later it reopens only previously tracked active/resolved
     Bug IDs missing from the current active list, writes `state-events.json`,
     appends the transition table to `chat-summary.md`, and sends deterministic
     events to `obsidian-fix-pattern-memory`.
   - State is compact and local under
     `%USERPROFILE%\.codex\zentao-bug-triage\state\<target-id>.json`.
     Raw snapshots remain under `snapshots/`; neither location is repository data.

   - Do not duplicate the launcher's initialization, Git, variant, mapping, or attachment checks outside this command. Read the generated `chat-summary.md` and work queues after it succeeds.
   - Use `scripts/zentao_bug_snapshot.js` directly only for special modes such as selected IDs, assigned-only, current-mine, non-active status, explicit project selection, or an explicitly requested fast/no-attachment list.

   - The script reads the private local project map first, matches `git branch --show-current` plus `yl_device_ver`, loads/saves a local project-id cache, discovers the Zentao project ID from `project-browse.html`/`program-browse.html`, fetches the active tab of `project-bug-<id>.html`, records the selected project in the snapshot, and automatically falls back to active assigned bugs when no confirmed mapping matches, project ID discovery fails, or the project/list page returns zero rows.
- When this assigned fallback is used for a mapped current project, the script deep-fetches candidate assigned rows and keeps only bugs whose detail page product matches the mapped project. Do not treat the first empty project table as “no bugs” unless the fallback is also empty.
- Assigned fallback product matching is exact after whitespace normalization. Similar synthetic prefixes such as `Example MiniApp` and `Example MiniApp Asset Edition` are different products. If no exact detail product matches, return zero current-project bugs; never widen the result to prefix/substring matches.
   - `--limit` controls how many active list rows to capture. By default every captured active row opens its detail page and downloads attachments. `--detail-limit` may lower that count only for an explicitly requested fast list. `--detail-concurrency` defaults to 4 and opens detail pages in parallel with independent pages sharing the authenticated session.
   - The script defaults to `--bug-status active`. Use `--bug-status all`, `resolved`, or `closed` only when the user explicitly requests those statuses.
   - Only when the user explicitly asks for a fast current-active list without detail pages:

```powershell
$env:NODE_PATH="$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules;$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules\.pnpm\node_modules"
$repoRoot = git rev-parse --show-toplevel
$repoName = Split-Path -Leaf $repoRoot
$branch = git branch --show-current
node "$env:USERPROFILE\.codex\skills\zentao-bug-triage\scripts\zentao_bug_snapshot.js" --repo . --expect-repo-name "$repoName" --expect-branch "$branch" --bug-status active --detail-limit 0 --no-download-attachments
```

   - When the user wants only the current branch/product bugs that are assigned to the current Zentao account and still active, use:

```powershell
$env:NODE_PATH="$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules;$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules\.pnpm\node_modules"
$repoRoot = git rev-parse --show-toplevel
$repoName = Split-Path -Leaf $repoRoot
$branch = git branch --show-current
node "$env:USERPROFILE\.codex\skills\zentao-bug-triage\scripts\zentao_bug_snapshot.js" --repo . --expect-repo-name "$repoName" --expect-branch "$branch" --current-mine-active --limit 80
```

   - For selected bugs that the user wants fixed next, deep-fetch IDs and generate the temporary detailed work order:

```powershell
$env:NODE_PATH="$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules;$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules\.pnpm\node_modules"
$repoRoot = git rev-parse --show-toplevel
$repoName = Split-Path -Leaf $repoRoot
$branch = git branch --show-current
node "$env:USERPROFILE\.codex\skills\zentao-bug-triage\scripts\zentao_bug_snapshot.js" --repo . --expect-repo-name "$repoName" --expect-branch "$branch" --ids 2957,2937 --download-attachments
```

   - Each snapshot writes:
     - `triage.md`: all fetched bugs, first-pass handling decision, memory match level, and repair eligibility.
     - `chat-summary.md`: compact chat table whose first column is `Bug（ID + 标题）`, followed by category, memory match, repair eligibility, handling suggestion, and attachment type. Paste this table into the final answer after every fetch.
     - `work-items.md`: bugs Codex should inspect/fix next, candidate fix-pattern paths/evidence, mandatory pre-edit checks, and candidate bugs that have a clear expected result or attachment evidence.
     - `ignored-items.md`: bugs to skip this round, wait for logs/confirmation, or send to platform/driver/hardware owners.
   - Memory linkage is read-only and enabled by default. It indexes Markdown under `%USERPROFILE%\Documents\Obsidian\CodexVault\Codex\fix-patterns`, keeps at most three candidates per bug, and emits `高` / `中` / `低` / `未命中`. Use `--fix-patterns <path>` to override the folder or `--no-memory-link` for an isolated run.
   - Treat `product`, branch, repo, device name, and version only as context filters. Never mix model/version tokens, `小程序`, `物卡`, `公版`, branch fragments, placeholder detail, or Chinese sliding-window fragments into symptom evidence.
   - A high match requires an already verified note plus multiple evidence dimensions and a same-project or code-symbol signal. Same device/branch text alone must not produce a match.
   - The deep-fetch command fills `work-items.md` with full detail, history records, latest activation note, and attachment paths. Before later fixing “这些bug”, read the latest or user-specified `work-items.md` first and base the fix on its detail fields and attachments.
   - For bugs assigned to the user regardless of project:

```powershell
$env:NODE_PATH="$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules;$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules\.pnpm\node_modules"
node "$env:USERPROFILE\.codex\skills\zentao-bug-triage\scripts\zentao_bug_snapshot.js" --repo . --assigned --bug-status active --limit 80
```

   - For a specific Zentao product/project, pass `--project-id`, `--project-name`, or `--project-key` after confirming the mapping.
   - Attachment mode defaults to `all`; use `--no-download-attachments` only when the user explicitly requests no downloads.
   - Pass `--no-work-md` only when no temporary repair/ignored queue files are needed.
   - Pass `--write-obsidian` only when the user wants the triage summary saved to the Obsidian vault; otherwise keep snapshots under `.codex` only.

3. Classify and report:
   - Read `references/classification-rules.md` before judging a fetched table.
   - Produce a compact chat table with: `Bug（ID + 标题）`, category, memory match, repair eligibility, handling suggestion, and attachment type. Keep this table in the response even when snapshot paths are also provided.
   - Explain `高` / `中` / `低` matches using the top candidate's project/branch, keywords, code symbols, symptom overlap, and verification state. Do not expose the full note body in the snapshot.
   - Interpret repair eligibility conservatively: `可直接修复候选`, `可移植候选`, `需先查代码`, `需先深抓`, `需日志验证`, `复测激活-需重新定位`, `非固件问题`, or `需底层/硬件处理`.
   - Keep detailed metadata in `triage.md`; do not paste the full wide triage table into chat unless the user asks for all details.
   - Before any downstream Zentao resolution, compare every selected detail-page `产品/项目` value with the canonical mapped project and stop on empty or non-exact values.
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
   - Keep the compact cross-fetch target baseline under
     `%USERPROFILE%\.codex\zentao-bug-triage\state\`. Do not delete it during
     attachment cleanup; deleting it intentionally resets comparison history.
   - Keep temporary repair and skip/waiting files as `work-items.md` and `ignored-items.md` in the snapshot folder only. These files are for short-term fixing and should not be copied to Obsidian by default.
   - After all bugs in a snapshot are fixed, clean temporary evidence with:

```powershell
$env:NODE_PATH="$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules;$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules\.pnpm\node_modules"
node "$env:USERPROFILE\.codex\skills\zentao-bug-triage\scripts\zentao_bug_snapshot.js" --cleanup "<snapshot-dir>"
```

   - Write a compact Markdown summary under `%USERPROFILE%\Documents\Obsidian\CodexVault\Codex\projects\zentao\` only when the user explicitly asks to save/update memory or the script is run with `--write-obsidian`.
   - Save only reusable branch/version context, bug summary, classification, and local paths to downloaded attachments. Do not save passwords or full private chat.

6. Code investigation gate:
   - Only inspect or edit code after the user chooses one or more bug IDs or asks “看这些需要修改的”.
   - For selected UI/app/protocol bugs, check whether the issue exists in the current checkout before proposing changes.
   - For low-level bugs, report required device evidence instead of editing.
   - When reporting after code inspection, include: Zentao evidence, code evidence, commit/time evidence, conclusion, needed logs/videos, and whether Codex should fix it now.
   - Stop after the diagnosis and proposed behavior unless the user approves implementation. Primary Codex implements an approved bounded fix directly. Use `local-coder-executor` only when the user explicitly requests the local model and approves a bounded implementation plan; never invoke the worker from a list-only snapshot.

## Resources

- `scripts/zentao_bug_fast_fetch.py`: existence-first initialization gate, default current-project fetch, live post-fetch validation, attachment retry, and deferred project-context refresh.
- `scripts/zentao_snapshot_reconcile.py`: exact-target baseline, missing-status refresh plan, transition classification, chat report, and local fix-memory events.
- `scripts/zentao_bug_snapshot.js`: login, resolve current branch to a Zentao project, fetch project/assigned/selected bugs, classify, link fix-pattern memory, auto-download relevant attachments, save JSON/Markdown snapshots, generate temporary `work-items.md`/`ignored-items.md`, and clean temporary work orders/attachments.
- `scripts/memory_linkage.js`: read-only fix-pattern indexing, bug fingerprint scoring, high/medium/low/no-match classification, and conservative repair eligibility.
- `references/classification-rules.md`: category, difficulty, and “can Codex handle” rules.
- `%USERPROFILE%\.codex\zentao-bug-triage\project-map.local.md`: private current branch/version/customer mapping; never sync or commit it.
- `references/project-map.md`: generic schema/example only; it must not contain real customer, branch, device, version, ID, or service data.
- `references/local-storage.md`: snapshot and Obsidian storage conventions.
