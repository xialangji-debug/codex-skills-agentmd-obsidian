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

Choose skills from the current task and available-skill descriptions. Keep detailed procedures inside the owning skill instead of duplicating them in this global file.

In a direct Codex project conversation, the primary Codex agent implements a bounded fast fix directly when it is one project, one concrete issue, the current branch, local source only, expected to touch at most five files, and needs no branch switch, device action, release, Zentao write, or local model. This rule takes precedence over the local-worker allowlist. Do not start a nested Codex task, invoke the local worker, poll another task, or run a second closeout workflow for that fast fix.

For a direct fast fix: check repo/branch/commit/dirty once; preserve and work with unrelated user changes; read up to three relevant memory notes only when explicitly requested or when a regression/similar-issue lookup is required; run one focused code/history search pass; edit directly; inspect the target diff; run `git diff --check` and one narrow test or build; then report the result. When work leaves the fast-fix boundary, keep it in the current Codex task and route each operation to its owning global specialist Skill: Zentao triage/resolution, cross-branch work, local-model execution, build/flash, log capture, release, or closeout. Obtain explicit confirmation only for the risky action that requires it.

Route external bug-system listing, detail retrieval, status reconciliation, and remote writes to the owning skills. Keep product mappings, server details, target identity, and state-transition procedures in local project context or those skills, not in this global file. A local snapshot or memory update never authorizes an external-system write.

Use `local-coder-executor` only when the user explicitly requests the local coder/model and approves a bounded implementation plan, and only when the current repository or working directory is inside an enabled root in `%USERPROFILE%\.codex\local-coder-projects.json`. Outside that allowlist, the primary Codex agent implements directly and must not invoke the local worker. Do not bypass this boundary; change the allowlist only when the user explicitly changes the permitted project set.

- The primary Codex agent owns visual understanding, repository inspection, requirements, planning, product decisions, review, and verification.
- Delegate only a bounded, self-contained coding task to the configured local worker; run one worker at a time.
- Translate screenshots and other multimodal evidence into explicit text requirements before delegation. Do not ask the worker to interpret images.
- After the worker exits, independently inspect the changed files and diff, preserve pre-existing user changes, and run the narrowest relevant tests.
- Never include credentials, API keys, tokens, or unrelated private context in a worker task.

If a required skill is not exposed but exists locally, read:

`%USERPROFILE%\.codex\skills\<skill-name>\SKILL.md`

Use `%USERPROFILE%\.codex\skills-index\index.md` only when routing is unclear or the user asks to organize skills. The main index is a one-line catalog; read a domain index only when needed.

Prefer project-local context when present:

- `AGENTS.md`
- `.codex-project\index.md`
- Other files linked by the project index

Use `%USERPROFILE%\.codex\active-projects.json` as the explicit list for cross-project freshness audits. Do not treat every repository found under Desktop as active.

Run the read-only work architecture gate with `python -X utf8 %USERPROFILE%\.codex\scripts\architecture_audit.py all --skip-life-vault` unless the current request explicitly authorizes a private-life audit. Create a self-verifying control/work-Vault/project-context snapshot with `pwsh -File %USERPROFILE%\.codex\scripts\create_architecture_snapshot.ps1` and a `-SourceSpec` that excludes `LifeVault` after broad architecture changes.

Project context has two layers:

- Keep stable repository rules and navigation in `AGENTS.md` and `.codex-project\index.md`.
- Keep branch, commit, dirty state, product/version, protocol selection, build parameters, device identity, and external-system IDs only in `.codex-project\variant.md`.
- Refresh a stale variant before any operation that depends on dynamic target identity, unless the owning skill defines a narrower read-only freshness rule. Do not copy dynamic facts into global instructions or Skill bodies.

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
