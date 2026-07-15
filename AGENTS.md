# Codex Global Instructions

## Language

Always respond in Simplified Chinese unless the user explicitly requests another language. Code, commands, paths, logs, and technical terms may remain in English.

## Durable Memory

Use local Markdown in the user's Obsidian vault:

- Vault: `<your Obsidian vault>`
- Memory: `<your Obsidian vault>\Codex`

Never use Basic Memory MCP. Do not save full chat logs, credentials, passwords, API keys, tokens, or other sensitive data.

Default behavior:

- Prefer the current conversation and workspace files.
- Do not scan the whole vault or consult memory for ordinary code fixes.
- When memory is needed, search narrowly and read at most 1-3 relevant notes unless the user asks for a broader review.
- Search priority: `fix-patterns/`, `projects/`, `people/`, `notes/`, then `agent/`.

Automatically search only `Codex/fix-patterns/` for cross-branch/version work, similar or regression issues, or logs/errors with clear keywords. Use 1-3 terms and stop if no match is found.

Use broader memory when the user says "读取记忆库", "继续上次", "记一下", or "收工更新", or when reliable completion requires cross-session project context.

## Skill And Project Routing

Use `aa-skill-router` first for short workflow requests such as "抓 bug", "当前 bug", "禅道", "修 bug", "协议", "日志", "收工更新", "出版本", "初始化当前 360x 项目上下文", or "skill 整理".

If a required skill is not exposed but exists locally, read:

`<CODEX_HOME>\skills\<skill-name>\SKILL.md`

Use `<CODEX_HOME>\skills-index\index.md` only when routing is unclear or the user asks to organize skills.

Prefer project-local context when present:

- `AGENTS.md`
- `.codex-project\index.md`
- `.codex-project\zentao.md`
- `.codex-project\build.md`
- `.codex-project\protocol.md`

Keep active skills flat under `<CODEX_HOME>\skills`; archive inactive skills under `<CODEX_HOME>\skills.disabled`.

## Zentao Bug Intake

In ASR3601/ASR3602/360x/Crane/LVGL firmware workspaces, treat "抓 bug", "当前 bug", "当前分支 bug", "这个分支有哪些 bug", and "看禅道 bug" as Zentao fetch-and-triage requests.

Workflow:

1. Use `zentao-bug-triage`; if unavailable, read its local `SKILL.md` directly.
2. Identify the current repo, branch, short commit, product/version mapping, then run the snapshot workflow. Do not ask for reproduction steps first.
3. Return the compact table: `ID | 标题 | 类型 | 处理建议 | 附件 | 我能否先修`.
4. Use `asr3601-bug-intake-orchestrator` only after a concrete bug ID, detail, screenshot, log, or attachment needs code-level judgment or fixing.

## Writing Memory

After a reusable fix that may recur across branches, versions, or similar projects, create or update a note under:

`<your Obsidian vault>\Codex\fix-patterns`

Skip only when the user says "不要记录" or "不要更新记忆库". Include keywords, applicable project/version, symptoms/log signatures, root cause, key files/functions, fix approach, verification, and cautions.

Write other durable information only when valuable:

- Project state: `projects/`
- People context: `people/`
- Reusable workflows: `notes/`
- Pending work: `agent/TODO.md`
- Unresolved issues: `agent/open-loops.md`

At the end of important tasks, briefly state which memory files changed. If no fix-pattern was written, briefly state why. Small one-off tasks do not need memory updates.
