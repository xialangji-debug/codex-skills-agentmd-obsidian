# Codex Global Instructions

## Language

Always respond in Simplified Chinese unless the user explicitly requests another language. Code, commands, paths, logs, and technical terms may remain in English.

## Durable Memory And Privacy Boundary

Use two physically separate local Obsidian vaults:

- Work vault: `%USERPROFILE%\Documents\Obsidian\CodexVault`
- Work memory root: `%USERPROFILE%\Documents\Obsidian\CodexVault\Codex`
- Private life vault: `%USERPROFILE%\Documents\Obsidian\LifeVault`

Never use Basic Memory MCP. Do not save full chat logs, credentials, passwords, API keys, tokens, or other sensitive data.

The work vault is the default durable-memory surface. The life vault is opt-in only:

- Do not search, read, summarize, or write `LifeVault` unless the user's current request explicitly concerns private life, health, personal plans, journal, or personal ideas.
- A general request such as "读取记忆库", "继续上次", "每日总结", or "收工更新" refers to the work vault unless the user explicitly names life/private/health context.
- Do not create cross-vault wikilinks, embeds, Bases queries, or shared inboxes. Refer to another vault only as plain text when unavoidable.
- Health notes record user-provided observations or source material. Never promote AI inference into a medical fact.

For both vaults, `codex_access` and `trust` are independent axes:

- `codex_access: read`: read and summarize only; do not modify without explicit file-level authorization.
- `codex_access: propose`: draft a suggested change, but require explicit user approval before changing an existing note.
- `codex_access: manage`: create and maintain notes within the request's scope.
- `trust: canonical`: user-controlled source of truth.
- `trust: verified`: checked against evidence.
- `trust: derived`: synthesized from named sources.
- `trust: working`: unverified draft or observation.

Default work-memory behavior:

- Prefer the current conversation and workspace files.
- Do not scan the whole vault or consult memory for ordinary code fixes.
- When memory is needed, search narrowly and read at most three relevant notes unless the user asks for a broader review. When the user explicitly says "根据记忆" or "读取记忆", rank the narrow matches and read the top three when three relevant notes exist; do not pad the result with unrelated notes.
- Search priority: `fix-patterns/`, `projects/`, `learning/topics/`, `notes/`, `people/`, then `agent/`.
- Automatically search only `Codex/fix-patterns/` for cross-branch/version work, similar or regression issues, or logs/errors with clear keywords. Use 1-3 terms and stop if no match is found.
- Use broader work memory when the user explicitly asks to read memory or when reliable completion requires cross-session project context.

## Skill And Project Routing

Choose skills from the current task and available-skill descriptions. Keep each procedure in its owning skill.

When the current repository provides `AGENTS.md` and `.codex-project\index.md`, treat them as the routing authority. Follow the matching local route and read only its linked context; do not run another ASR/ESP32 classifier or load every global index. Use `%USERPROFILE%\.codex\skills-index\index.md` only when local routing is missing or unclear.

Keep stable repository rules and navigation in `AGENTS.md`, `.codex-project\index.md`, and optional `.codex-project\local.md`. Keep branch, commit, dirty state, product/version, protocol selection, build parameters, device identity, and external-system IDs only in `.codex-project\variant.md`.

Scale checks with the action:

- For read-only code lookup or explanation, use current project context and live source. Do not refresh the complete variant or run tool health checks unless the needed evidence is missing or the tool fails.
- Before a local source edit, check branch, HEAD, and dirty state once and preserve unrelated user changes. The owning implementation skill defines the Fast Fix procedure.
- For cross-branch, protocol, build, flash, release, device, or external-system work, use the owning specialist skill and refresh any stale dynamic identity it depends on.
- When one request combines a behavior fix with formal plus FOTA-test delivery,
  do only narrow source checks before the focused commit. Hand the release stage
  directly to `asr3602-fota-pair-release`; its sequential T/F builds supply the
  full build evidence, so do not run a third standalone firmware build first.

Route external bug-system access and remote writes to their owning skills. A local snapshot or memory update never authorizes a branch change, commit, push, device action, release, or external write.

For every ASR3601/ASR3602/360x project, the exact phrase `快速出版本` activates
the shared Quick Release Mode. Route a standalone formal release to the owner
confirmed by the current project's index; when that owner is
`akq-firmware-release`, use its Quick Release Mode. If the project has no
confirmed release owner or controller, stop and ask instead of borrowing a
similar ASR360x project's script. For a composite request, preserve the same
mode when handing off the release stage. This modifier requests one direct
controller run, no controller-external preflight or post-success verification,
and a concise completion reply. It does not disable the controller's built-in
gates or authorize commits, staging, stashing, discards, flashing, Zentao
writes, overwrites, gate bypasses, or recovery actions that the rest of the
request did not explicitly authorize. If the controller stops or fails, do not
diagnose, retry, resume, change parameters, clean up, or continue automatically;
report the failed stage, exact error, known side effects, and the decision
needed from the user, then wait.

Use `local-coder-executor` only when the user explicitly requests the local model, approves a bounded implementation plan, and the project is allowlisted in `%USERPROFILE%\.codex\local-coder-projects.json`. Primary Codex retains requirements, visual interpretation, review, and verification; never send credentials or unrelated private context to the worker.

If a required active skill is not exposed, read `%USERPROFILE%\.codex\skills\<skill-name>\SKILL.md`. Use `%USERPROFILE%\.codex\active-projects.json` as the explicit list for cross-project audits.

Run the read-only work architecture gate with `python -X utf8 %USERPROFILE%\.codex\scripts\architecture_audit.py all --skip-life-vault` after changes to global Skills, routing indexes, project-context generators, Vault schemas, or other control/knowledge-plane architecture, and when the user explicitly requests an architecture audit. Ordinary firmware fixes, builds, and releases use their project/owner gates and do not run the global architecture audit. After broad architecture changes, create a self-verifying control/work-Vault/project-context snapshot with `pwsh -File %USERPROFILE%\.codex\scripts\create_architecture_snapshot.ps1` and a `-SourceSpec` that excludes `LifeVault`.

Keep active skills flat under `%USERPROFILE%\.codex\skills`; archive inactive skills under `%USERPROFILE%\.codex\skills.disabled`.

## Writing Memory

After every completed behavior-changing code, configuration, or resource fix, create or update one local canonical fix-pattern through `obsidian-fix-pattern-memory`. Record static/build-only results as working evidence; never promote them to device, platform, or QA verification. Merge high-confidence repeats into one root-cause note with per-target application records. Keep ambiguous matches separate or ask before merging. Do not auto-record explanation-only work, formatting/comments, reverted experiments, temporary diagnostics, environment cleanup, or changes the user explicitly says not to record.

The wording "根据记忆" or "读取记忆" alone authorizes lookup only. If that request leads to an actual behavior fix, the normal post-fix recording rule applies. Automatic local recording does not authorize edits in another branch/project, Git commits or pushes, device actions, releases, or external-system writes.

Write qualifying notes under:

`%USERPROFILE%\Documents\Obsidian\CodexVault\Codex\fix-patterns`

Include keywords, applicable project/version, symptoms/log signatures, root cause, key files/functions, fix approach, verification, and cautions.

Route other durable work information as follows:

- Daily technical review: `reviews/daily/YYYY-MM-DD.md`
- Weekly technical review: `reviews/weekly/YYYY-Www.md`
- Newly encountered material awaiting consolidation: `learning/inbox/`
- Reusable technical knowledge: `learning/topics/`
- Small technical ideas: `ideas/`
- Project state and stable pointers: `projects/`
- People context relevant to work: `people/`
- Reusable workflows: `notes/`
- Pending work: `agent/TODO.md`
- Unresolved issues: `agent/open-loops.md`

Route explicitly requested private information inside `LifeVault`:

- Daily life: `journal/`
- Health observations, records, and habits: `health/`
- Personal, career, quarterly, and yearly plans: `plans/`
- Personal ideas: `ideas/`
- Decisions and purchases: `decisions/`
- Private weekly reviews: `reviews/weekly/`

Do not create a new Skill for daily/weekly notes until templates and routing prove insufficient. Capture first, consolidate during review, and promote only reusable knowledge from `learning/inbox/` to `learning/topics/`.

At the end of important tasks, briefly state which memory files changed. If no fix-pattern was written, briefly state why. Small one-off tasks do not need memory updates.
