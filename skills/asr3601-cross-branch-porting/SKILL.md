---
name: asr3601-cross-branch-porting
description: Port ASR3601/Crane SDK LVGL children-watch firmware fixes across branches, versions, or sibling projects. Use when the user asks to migrate changes from another branch/version/project, mentions “移植/别的版本/当前分支/另一个工程/JC2/同类问题/回归”, or needs reusable Obsidian fix-pattern guidance for ASR3601, Crane SDK, LVGL v7, watch firmware, cloud album, scheduled power, alarms, contacts, SIM, boot animation, UI resources, or protocol behavior.
---

# ASR3601 Cross-Branch Porting

Use this skill only for cross-branch or cross-version firmware work. For ordinary “当前分支有没有这个问题/为什么/怎么修” triage, use `asr3601-lvgl-firmware-triage` first and enter this workflow only after the task is identified as a port, regression, or reusable similar fix.

## Role Boundary

- `asr3601-lvgl-firmware-triage` is the main intake: classify the bug, identify module/variant/evidence, and decide whether this porting workflow is needed.
- `asr3601-cross-branch-porting` is the specialist workflow: compare source and target, port the minimal patch, verify, and update `fix-patterns` when the result is reusable.
- Do not let both skills independently choose different fixes. If both trigger, let triage provide the problem frame and let this skill own the migration plan.

## Required Inputs

Infer these from the user, workspace, git state, attached files, or memory before asking:

```text
源版本/源分支/参考工程：
目标版本/目标分支/当前工程：
功能或缺陷：
涉及模块/文件：
排除边界：
验证方式：
```

Ask only when the source or target cannot be inferred safely. Common roots include `<ASR3601 工程路径>`, `<Crane SDK 工程路径>`, and temporary desktop/export folders.

## Memory Lookup

Use the user's Obsidian Markdown memory rules, not Basic Memory MCP.

For cross-branch, similar issue, regression, or clear log keyword cases:

1. Identify project name, branch/version, module, key error words, and key filenames.
2. Search only `<你的 Obsidian vault>\Codex\fix-patterns` for 1-3 relevant patterns.
3. Read only matching pattern files.
4. If nothing matches, do not broaden to the whole vault.

After a reusable fix, update or create one concise `fix-patterns` note unless the user explicitly says not to record it.

## Porting Workflow

1. Establish the baseline:
   - run `git status --short`
   - identify current branch with `git branch --show-current`
   - locate source artifacts: branch, commit, exported folder, copied files, patch notes, screenshots, logs, or Markdown summary
   - note uncommitted user changes and avoid reverting them
2. Compare source and target:
   - use `git diff`, `git show`, `rg`, or directory comparison
   - list changed files and classify them as code, resource, config/build, language/text, or documentation
   - trace related target-side functions before copying code
3. Decide the migration shape:
   - direct copy only for identical local files/resources
   - adapt when target branch has different macros, variants, resource IDs, language tables, screen sizes, or app registration paths
   - skip source changes that are unrelated, variant-specific, debug-only, or already present in target
4. Apply the smallest target-native patch:
   - preserve LVGL v7 conventions and local helper wrappers
   - preserve watch/phone/sport variant boundaries
   - reuse existing resource naming, text IDs, image registration, and build macros
   - avoid broad refactors while porting
5. Verify:
   - prefer the target's documented build or simulator command
   - if full build is unavailable, run focused syntax/search checks and explain the gap
   - verify both functional behavior and excluded variants when relevant

## Diff Review Checklist

Before editing, produce or internally confirm:

```text
源改动文件：
目标对应文件：
需要直接移植：
需要适配：
不移植：
风险点：
验证命令：
```

For UI/resources, check image/resource indexes, language text tables, page registration, refresh paths, and screen resolution. For timers/power/alarm/contact/protocol behavior, check storage, parse, event dispatch, UI confirmation, timeout callbacks, and reboot/resume paths.

## Reporting Shape

Use concise Chinese status, especially before large edits:

```text
结论：
源分支/目标分支：
需要移植：
需要适配：
不建议搬：
影响范围：
验证方式：
```

After the fix:

```text
已移植：
适配点：
影响范围：
验证：
记忆库：
风险：
```

## Fix-Pattern Note Shape

When writing `fix-patterns`, include only reusable information:

```markdown
# 问题标题

关键词：
适用项目/分支/版本：
症状和日志特征：
根因：
关键文件和函数：
修复步骤或补丁思路：
验证方法：
不适用场景和注意事项：
```

Do not save full chat logs, secrets, tokens, private account data, or large pasted logs.
