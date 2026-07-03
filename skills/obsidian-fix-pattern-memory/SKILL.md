---
name: obsidian-fix-pattern-memory
description: Search, create, and update the user's local Obsidian Markdown fix-pattern memory at C:\Users\84365\Documents\Obsidian\CodexVault\Codex. Use when the user says "读取记忆库", "记一下", "收工更新", "fix-pattern", "类似问题", "回归", "跨分支", asks to preserve reusable project knowledge, or after a reusable ASR3601/Crane/LVGL firmware fix should be recorded with time, project path, branch, short commit, source/target branch, and validation status.
---

# Obsidian Fix Pattern Memory

Use the local Markdown vault directly. Do not use Basic Memory MCP for this workflow.

Vault root:

```text
C:\Users\84365\Documents\Obsidian\CodexVault\Codex
```

## Lookup

For code fixes, cross-branch ports, similar issues, regressions, or log keywords:

1. Identify project, branch/version, module, key error words, and key filenames.
2. Search only `fix-patterns/` for 1-3 likely notes with `rg`.
3. Read only directly relevant matches.
4. If no match is found, stop lookup instead of broad-scanning the vault.

For non-code memory requests, search narrowly in `projects/`, `people/`, or `notes/` by user-provided keywords.

## Write Rules

Write long-term memory only when it is reusable. Prefer these destinations:

- `fix-patterns/` for reusable cross-branch or recurring bug fixes.
- `projects/` for project state and decisions.
- `people/` for stable people context.
- `TODO.md` for follow-ups.
- `agent/open-loops.md` for unresolved or unverified findings.
- `notes/` for general reusable experience.

Always include:

```text
记录时间：YYYY-MM-DD HH:mm
项目路径：
当前分支：
当前提交：
来源分支：
目标分支：
验证状态：已验证 / 未验证 / 仅推测
```

If the current directory is not a Git repository, write `不可用` for branch and commit.

## Fix Pattern Shape

Use this structure for `fix-patterns/*.md`:

```markdown
# 问题标题

## 元信息

- 记录时间：
- 项目路径：
- 当前分支：
- 当前提交：
- 来源分支：
- 目标分支：
- 验证状态：

## 关键词

-

## 适用范围

-

## 症状

-

## 根因

-

## 关键文件和函数

-

## 修复思路

-

## 验证方法

-

## 注意事项

-
```

## Helper Script

Use the template generator when creating a new fix-pattern note:

```powershell
python C:\Users\84365\.codex\skills\obsidian-fix-pattern-memory\scripts\new_fix_pattern.py `
  --title "ASR3601 alarm class mode silent" `
  --slug "asr3601-alarm-class-mode-silent" `
  --validation "已验证"
```

It fills current time, cwd, Git branch, and short commit. Edit the generated Markdown with the actual symptom, root cause, files, fix, validation, and caveats.

## Final Report

When memory is updated, report only the note path and what was recorded. If no update was made, say why: one-off issue, unverified guess, no reusable value, or user asked not to record.
