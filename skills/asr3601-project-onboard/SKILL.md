---
name: asr3601-project-onboard
description: Create, refresh, or check ASR360x project context and its canonical variant fingerprint. Use for project onboarding, 生成项目 AGENTS, 记录编译命令, 生成变体指纹, or a task owner that needs missing/stale identity. Ordinary source questions and direct release calls do not require a separate onboarding pass.
---

# ASR3601 Project Onboard

Keep shared procedures in global Skills and project identity in one generated variant.md. Preserve project-owned extensions.

## Load Only What The Task Needs

- Ordinary read-only source question: use live source and the established route.
- Explicit context check or missing exact identity: run --check once. Reuse its snapshot_id within the same logical task.
- Initialization or stale required identity: inspect the relevant live facts and generate with --write.
- Stable template maintenance: review generated changes before --write --force; preserve project-specific additions.
- A direct build/release/Zentao controller owns its required checks. Do not put an extra onboarding call before it.

Invalidate a task snapshot after a switch, unexpected HEAD/worktree drift, or changed yl_device_name/yl_device_ver/yl_hw_ver. An owner's own commit may update its expected HEAD without regenerating all project files. A snapshot is an in-task receipt, not a new persistent cache.

## Generation Contract

1. Read branch, HEAD, dirty state, and yl.h from the selected repo. Match the private project map's branch and version constraints.
2. Use unique confirmed mappings only. A candidate token match, version mismatch, ambiguous product, or explicit unconfirmed status stays needs-confirmation. Legacy entries with a recorded verification and unique identity remain supported.
3. Keep branch/commit/dirty, yl identity, chip/OS/protocol/build values, external IDs, device parameters, and memory IDs/aliases only in .codex-project/variant.md.
4. Generate AGENTS.md and .codex-project/{index,zentao,build,protocol,variant,device,memory}.md. Stable files contain rules and navigation, not copied dynamic facts.
5. Add generated context to Git's local exclude unless --no-exclude is requested. Preserve .codex-project/local.md byte-for-byte; never create or overwrite it.
6. Treat protocol classification from identity tokens as a search hint. Confirm the active protocol in code/documents before a protocol-sensitive action. A generated build candidate also needs a project-confirmed command/profile before execution.
7. Report changed paths, snapshot status, and unresolved identity. Link mapped source documents when they are relevant to the task.

Repository and variant hashes are privacy-safe identifiers. Target IDs retain branch/version case and match the canonical memory writer and Zentao reconciliation; do not rewrite historical memory targets during onboarding.

## Commands

The generator uses Python with PyYAML for structured project-map parsing.

```powershell
python "$env:USERPROFILE\.codex\skills\asr3601-project-onboard\scripts\project_onboard.py" --repo . --check
python "$env:USERPROFILE\.codex\skills\asr3601-project-onboard\scripts\project_onboard.py" --repo . --dry-run
python "$env:USERPROFILE\.codex\skills\asr3601-project-onboard\scripts\project_onboard.py" --repo . --write
```

--write updates variant.md and creates missing stable files. --force also replaces generated stable files; review their ownership first. A current --check prints snapshot_id; a stale result identifies the differences. Never store private customer mappings or service data in reusable templates.
