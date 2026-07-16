# Zentao Skill Index

| Request | Skill |
|---|---|
| 抓 bug / 当前 bug / 当前分支 bug / 看禅道 bug | `zentao-bug-triage` |
| Deep-fetch selected bug IDs, download attachments, create work-items | `zentao-bug-triage` |
| 禅道标记解决 / 已解决 / 外部原因 / reopen then resolve | `zentao-bug-resolver` |
| 修复、中文提交、关禅道、可选出版本的连续流程 | `asr360x-bug-delivery-orchestrator` |

Prefer script workflow:

```powershell
$env:NODE_PATH="$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules;$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules\.pnpm\node_modules"
node "$env:USERPROFILE\.codex\skills\zentao-bug-triage\scripts\zentao_bug_snapshot.js" --repo . --limit 80
```

Do not use browser/Computer Use first unless the script fails, login state is missing, or the user explicitly asks for page inspection.
