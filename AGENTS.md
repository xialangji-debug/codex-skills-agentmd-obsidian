# Codex Global Instructions

## Working Agreements

- Respond in Simplified Chinese unless the user requests another language. Keep code, commands, paths, logs, and technical terms in their original language as needed.
- Complete authorized work through the relevant verification. Resolve routine implementation choices from context; ask only when missing information materially changes the target, result, or permitted action. Reuse authorization already given for the same action and scope.
- State the outcome, key changes, actual verification, and material limitations concisely. Keep internal IDs, full hashes, and exhaustive checklists in existing receipts; show them when needed for the user's next action or requested.
- Scale verification to the change; repeat or broaden passing checks only after a change, failure, or unresolved concern. When multiple agents collaborate, one owner runs the relevant suite on the merged version; other agents reuse that version and result and reproduce only specific review concerns.
- For document edits, batch a coherent round before rendering. Small revisions need affected-page and downstream pagination review; new documents, global styles, table structure, or major reflow need full-page visual review. This user-approved working agreement overrides a plugin's blanket render-after-every-edit/full-page requirement for small revisions.

## Privacy And Memory Access

Use physically separate local Obsidian vaults:

- Work: `%USERPROFILE%\Documents\Obsidian\CodexVault`; memory root: `Codex/`.
- Private life: `%USERPROFILE%\Documents\Obsidian\LifeVault`.

Never use Basic Memory MCP or save full chat logs, credentials, passwords, API keys, tokens, or other sensitive data.

Work memory is the default. Access LifeVault only when the current request explicitly concerns private life, health, personal plans, journal, or personal ideas. General requests such as "读取记忆库", "继续上次", "每日总结", and "收工更新" refer to work memory unless private context is explicit. Do not create cross-vault wikilinks, embeds, Bases queries, or shared inboxes; use plain text references only when unavoidable. Record health observations and named sources without treating AI inference as medical fact.

Access and evidence are independent: `codex_access: read` permits reading only (editing needs file-level authorization); `propose` permits suggestions (editing needs approval); `manage` permits maintenance within scope. `trust: canonical` is user-controlled truth, `verified` has checked evidence, `derived` is synthesis, and `working` is unverified. Never infer write permission from trust.

Prefer conversation and workspace evidence. Do not scan the whole vault or consult memory for ordinary fixes. Automatic lookup is limited to `Codex/fix-patterns/` for cross-branch/version, similar/regression, or clearly identified log/error cases: search 1-3 terms and stop on no match. Broader work-memory lookup requires an explicit request or necessary cross-session context.

Search priority: `fix-patterns/`, `projects/`, `learning/topics/`, `notes/`, `people/`, then `agent/`. Read at most three relevant notes unless a broader review is requested. For "根据记忆" or "读取记忆", rank matches and read the top three when available, without unrelated filler. These phrases authorize lookup only.

## Project And Skill Routing

Use current-task skill descriptions. For ASR360x, project `AGENTS.md` records special routes; branch profiles and live source provide configuration and identity. Other projects may keep their own `.codex-project/index.md` routing. Follow the matching route without repeating a domain classifier. Consult `%USERPROFILE%\.codex\skills-index\index.md` only if local routing is missing or unclear. Keep specialist procedures in their owning skill.

- ASR stable rules/navigation: minimal `AGENTS.md` and optional project-owned `.codex-project/local.md`. Preserve specialized documents containing project-specific content.
- ASR identity: live Git and source; build parameters: confirmed branch profile; external mappings: existing private project map. `.codex-project/variant.md` is a generated view. After a branch switch, prepare the recorded configuration once; build/release controllers do this internally.
- Read-only lookup: use current context and live source; refresh full identity or check tool health only when evidence is missing or a tool fails.
- Local source edits: check branch, HEAD, and dirty state once; preserve unrelated changes and follow the implementation skill's Fast Fix procedure.
- Cross-branch, protocol, build, flash, release, device, or external-system work: use the owner and let it refresh the stale identity it needs. Reuse its verification and result receipt; do not repeat controller-owned checks outside the controller. Route bug-system access and remote writes to their owners.
- Fix plus formal/FOTA-test delivery: perform narrow source checks before the focused commit, then hand directly to `asr3602-fota-pair-release`. Its sequential T/F builds supply full build evidence; do not add a third standalone build.

Local snapshots and memory operations do not authorize changes in other branches/projects, branch switches, Git commits/pushes, device actions, releases, or external writes. Skills guide execution within the user's authorized scope; they do not expand it.

If a required active skill is not exposed, read `%USERPROFILE%\.codex\skills\<skill-name>\SKILL.md`. Use `%USERPROFILE%\.codex\active-projects.json` for cross-project audit targets. Keep active personal skills flat under `%USERPROFILE%\.codex\skills` and inactive skills under `%USERPROFILE%\.codex\skills.disabled`.

For Skill registration/routing maintenance or explicitly requested usage statistics, read `%USERPROFILE%\.codex\scripts\skill-maintenance\maintenance.md`. In PowerShell, the registry audit entry is `python -X utf8 "$env:USERPROFILE/.codex/scripts/skill-maintenance/skill_usage_tracker.py" registry-audit --strict --json`; registry maintenance does not require scanning chat logs or enabling telemetry.

## Quick Release Mode

For ASR3601/ASR3602/360x, the exact phrase `快速出版本` selects Quick Release Mode, including the release stage of a composite request. Use the formal-release owner/controller confirmed by project AGENTS or applicable project routing; for `akq-firmware-release`, use its Quick Release Mode. If no owner/controller is confirmed, ask instead of borrowing another project's script.

Run the controller once directly, with no external preflight or post-success verification, and reply concisely. Preserve its built-in gates. The modifier grants no additional authorization for commits, staging, stashing, discards, flashing, Zentao writes, overwrites, gate bypasses, or recovery.

If the controller stops or fails, report the failed stage, exact error, known side effects, and required user decision, then wait. Do not automatically diagnose, retry, resume, change parameters, clean up, or continue.

## Memory Recording

After a completed behavior-changing code, configuration, or resource fix, use `obsidian-fix-pattern-memory` to maintain one canonical note under the work root's `fix-patterns/`. Include keywords, target project/version, symptoms/log signatures, root cause, key files/functions, fix approach, verification, and cautions. Static/build-only results remain working evidence, never device/platform/QA verification.

Merge high-confidence repeats into one root-cause note with per-target records; keep ambiguous matches separate or ask before merging. Do not auto-record explanations, formatting/comments, reverted experiments, temporary diagnostics, environment cleanup, or changes the user says not to record. A lookup that leads to an actual fix follows the normal recording rule.

Work content routes and note properties are maintained in the work Vault's `Codex/agent/memory-policy.md` and `Codex/00-system/schema.md`; read them when categorizing or changing notes. Use `agent/open-loops.md` as the single pending-work entrance; detailed validation items are generated from canonical fix notes on demand, not duplicated after every record. For explicitly requested private records, use LifeVault's existing journal/health/plans/ideas/decisions/reviews routes.

Capture new material first, consolidate during review, and promote only reusable knowledge to `learning/topics/`. Reuse templates and routing before creating a daily/weekly-note Skill. At important-task closeout, briefly identify memory files changed, or why no fix-pattern was written; small one-off tasks need no memory update.

## Architecture Maintenance

After broad control/knowledge changes, audit engine/policy changes, project-context generator or Vault schema changes, or an explicit full audit, run:

```powershell
python -X utf8 "$env:USERPROFILE/.codex/scripts/architecture_audit.py" all --skip-life-vault
```

For bounded Skill/routing edits use `check --checks skills,routes --skip-life-vault`; project-local control edits may use `check --project <repo> --checks projects,constants,routes --skip-life-vault`; explicit or batch knowledge maintenance uses `check --checks vault --skip-life-vault`. A routine single fix/event record ends with the canonical writer result; small note/text edits do not trigger a full Vault audit or architecture snapshot. Ordinary firmware work uses its owner's gates. State the selected scope and keep unrelated findings separate. Missing/dynamic targets or failed parsers are incomplete coverage; required routes must resolve and conditional capabilities must be exposed before use.

Policy, dependent scopes, effective values and static-analysis limits: `%USERPROFILE%/.codex/scripts/architecture-audit.md`. Follow that reference for audit maintenance rather than duplicating its procedure. Do not change historical verification dates or evidence levels to satisfy freshness checks. After broad changes, create a self-verifying control/work-Vault/project-context snapshot with `%USERPROFILE%/.codex/scripts/create_architecture_snapshot.ps1` and an explicit `-SourceSpec` excluding LifeVault. Private audit access requires explicit user scope and `--include-life-vault`.

## Local Validation Scripts

Applies to all repositories, branches, and worktrees:

- Temporary Python tests, regression checks, and diagnostic scripts created for a task are local validation tools; do not stage or commit them unless the user explicitly requests those files.
- Create new temporary scripts, fixtures, generated C files, executables, and logs under `.codex-project/validation/<task-or-bug>/`. Do not add temporary validation scripts to `tools/lv_utils/`.
- Before committing, inspect the staged paths and exclude task-local validation artifacts. Do not use force-add to bypass ignore rules without an explicit request to commit those files.
- Preserve tracked production tests and tools. Do not delete, untrack, or discard them automatically; existing tracked temporary tests require explicit cleanup authorization.
