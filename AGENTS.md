# Codex Global Instructions

## Working Agreements

- Respond in Simplified Chinese unless the user requests another language. Keep code, commands, paths, logs, and technical terms in their original language as needed.
- Complete authorized work through the relevant verification. Resolve routine implementation choices from context; ask only when missing information materially changes the target, result, or permitted action. Reuse authorization already given for the same action and scope.
- State the outcome, supporting evidence, and remaining limitations concisely. Scale verification to the change; repeat or broaden passing checks only after a change, failure, or unresolved concern.

## Privacy And Memory Access

Use physically separate local Obsidian vaults:

- Work: `%USERPROFILE%\Documents\Obsidian\CodexVault`; memory root: `Codex/`.
- Private life: `%USERPROFILE%\Documents\Obsidian\LifeVault`.

Never use Basic Memory MCP or save full chat logs, credentials, passwords, API keys, tokens, or other sensitive data.

Work memory is the default. Access LifeVault only when the current request explicitly concerns private life, health, personal plans, journal, or personal ideas. General requests such as "读取记忆库", "继续上次", "每日总结", and "收工更新" refer to work memory unless private context is explicit. Do not create cross-vault wikilinks, embeds, Bases queries, or shared inboxes; use plain text references only when unavoidable. Record health observations and named sources without treating AI inference as medical fact.

For both vaults, access permission and evidence status are independent:

| Field | Meaning |
| --- | --- |
| `codex_access: read` | Read/summarize only; editing requires explicit file-level authorization. |
| `codex_access: propose` | Draft suggestions; changing an existing note requires explicit approval. |
| `codex_access: manage` | Create and maintain notes within the request's scope. |
| `trust: canonical` | User-controlled source of truth. |
| `trust: verified` | Checked against evidence. |
| `trust: derived` | Synthesized from named sources. |
| `trust: working` | Unverified draft or observation. |

Prefer conversation and workspace evidence. Do not scan the whole vault or consult memory for ordinary fixes. Automatic lookup is limited to `Codex/fix-patterns/` for cross-branch/version, similar/regression, or clearly identified log/error cases: search 1-3 terms and stop on no match. Broader work-memory lookup requires an explicit request or necessary cross-session context.

Search priority: `fix-patterns/`, `projects/`, `learning/topics/`, `notes/`, `people/`, then `agent/`. Read at most three relevant notes unless a broader review is requested. For "根据记忆" or "读取记忆", rank matches and read the top three when available, without unrelated filler. These phrases authorize lookup only.

## Project And Skill Routing

Use current-task skill descriptions. The repository's `AGENTS.md` and `.codex-project/index.md` own local routing: follow the matching route and linked context without repeating an ASR/ESP32 classifier. Consult `%USERPROFILE%\.codex\skills-index\index.md` only if local routing is missing or unclear. Keep specialist procedures in their owning skill.

- Stable rules/navigation: `AGENTS.md`, `.codex-project/index.md`, optional `.codex-project/local.md`.
- Dynamic identity only: `.codex-project/variant.md` for branch, commit, dirty state, product/version, protocol, build parameters, device identity, and external IDs.
- Read-only lookup: use current context and live source; refresh full identity or check tool health only when evidence is missing or a tool fails.
- Local source edits: check branch, HEAD, and dirty state once; preserve unrelated changes and follow the implementation skill's Fast Fix procedure.
- Cross-branch, protocol, build, flash, release, device, or external-system work: use the owner and let it refresh the stale identity it needs. Reuse its verification and result receipt; do not repeat controller-owned checks outside the controller. Route bug-system access and remote writes to their owners.
- Fix plus formal/FOTA-test delivery: perform narrow source checks before the focused commit, then hand directly to `asr3602-fota-pair-release`. Its sequential T/F builds supply full build evidence; do not add a third standalone build.

Local snapshots and memory operations do not authorize changes in other branches/projects, branch switches, Git commits/pushes, device actions, releases, or external writes. Skills guide execution within the user's authorized scope; they do not expand it.

If a required active skill is not exposed, read `%USERPROFILE%\.codex\skills\<skill-name>\SKILL.md`. Use `%USERPROFILE%\.codex\active-projects.json` for cross-project audit targets. Keep active personal skills flat under `%USERPROFILE%\.codex\skills` and inactive skills under `%USERPROFILE%\.codex\skills.disabled`.

## Quick Release Mode

For ASR3601/ASR3602/360x, the exact phrase `快速出版本` selects Quick Release Mode, including the release stage of a composite request. Use the formal-release owner/controller confirmed by the current project index; for `akq-firmware-release`, use its Quick Release Mode. If no owner/controller is confirmed, ask instead of borrowing another project's script.

Run the controller once directly, with no external preflight or post-success verification, and reply concisely. Preserve its built-in gates. The modifier grants no additional authorization for commits, staging, stashing, discards, flashing, Zentao writes, overwrites, gate bypasses, or recovery.

If the controller stops or fails, report the failed stage, exact error, known side effects, and required user decision, then wait. Do not automatically diagnose, retry, resume, change parameters, clean up, or continue.

## Memory Recording

After a completed behavior-changing code, configuration, or resource fix, use `obsidian-fix-pattern-memory` to maintain one canonical note under the work root's `fix-patterns/`. Include keywords, target project/version, symptoms/log signatures, root cause, key files/functions, fix approach, verification, and cautions. Static/build-only results remain working evidence, never device/platform/QA verification.

Merge high-confidence repeats into one root-cause note with per-target records; keep ambiguous matches separate or ask before merging. Do not auto-record explanations, formatting/comments, reverted experiments, temporary diagnostics, environment cleanup, or changes the user says not to record. A lookup that leads to an actual fix follows the normal recording rule.

Work routes, relative to the work memory root:

| Content | Destination |
| --- | --- |
| Daily/weekly technical review | `reviews/daily/YYYY-MM-DD.md` / `reviews/weekly/YYYY-Www.md` |
| New material / reusable knowledge | `learning/inbox/` / `learning/topics/` |
| Technical ideas / project state and stable pointers | `ideas/` / `projects/` |
| Work people context / reusable workflows | `people/` / `notes/` |
| Pending work / unresolved issues | `agent/TODO.md` / `agent/open-loops.md` |

For explicitly requested private records, use LifeVault's `journal/`, `health/`, `plans/` (including career, quarterly, yearly), `ideas/`, `decisions/` (including purchases), and `reviews/weekly/`.

Capture new material first, consolidate during review, and promote only reusable knowledge to `learning/topics/`. Reuse templates and routing before creating a daily/weekly-note Skill. At important-task closeout, briefly identify memory files changed, or why no fix-pattern was written; small one-off tasks need no memory update.

## Architecture Maintenance

After changes to global Skills, routing indexes, project-context generators, Vault schemas, or other control/knowledge architecture, and for explicit architecture audits, run the read-only gate:

```powershell
python -X utf8 "$env:USERPROFILE\.codex\scripts\architecture_audit.py" all --skip-life-vault
```

Ordinary firmware fixes/builds/releases use their owner gates. After broad architecture changes, create a self-verifying control/work-Vault/project-context snapshot using `pwsh -File "$env:USERPROFILE\.codex\scripts\create_architecture_snapshot.ps1"` with a `-SourceSpec` that excludes LifeVault.
