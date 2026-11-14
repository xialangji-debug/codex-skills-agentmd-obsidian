---
name: asr3601-project-onboard
description: Prepare recorded ASR360x branch configuration after a checkout, recover missing generated context, or register confirmed build parameters. Use for 切换后初始化, 调取版本配置, 生成项目 AGENTS, or a missing build profile. Ordinary source questions and direct build/release requests use their owners without an extra onboarding pass.
---

# ASR360x Project Configuration

Live Git and yl.h own current identity. The registered branch profile owns build parameters. The existing private project map owns external mappings. variant.md is a generated view.

## Prepare Configuration

After an authorized branch switch, run the generator with --prepare once. Build and release controllers restore their profiles internally; do not repeat initialization outside the owner.

Records live under the Git common directory's codex/build-profiles/. Worktrees share branch records but keep their own current profile. Version dates and ordinary commits do not require registering build parameters again. Hardware or selected configuration-value changes require verified updated settings. A root Makefile/CMakeLists.txt change alone requires owner review of the relevant definitions; follow [branch profile operations](references/branch-profiles.md) to refresh unchanged settings without asking the user to confirm them again.

A controller that already prepared and checked the profile can refresh generated
views with `--refresh-view --configuration-receipt <preflight.json>`. This reuses
its exact adapter and checks the configuration binding; it never prepares the
profile, changes Git excludes, or creates registry/cache entries. A changed HEAD
updates the view without re-registering unchanged build settings. Do not call this
as an extra post-success step outside the controller. A stale receipt preserves
the existing views and reports the mismatch.

## Generation Contract

1. Use live identity and unique confirmed mappings. Missing or ambiguous build records remain NEEDS_CONFIGURATION; ordinary source work can continue.
2. Default context consists of AGENTS.md, .codex-project/asr3602-build-profile.json, and .codex-project/variant.md. Write only changed generated files.
3. Preserve local.md, project-owned AGENTS content, specialized documents, resources, and validation material. --force does not erase project-owned instructions.
4. Protocol classification is only a search hint. Device selection and remote writes retain their owner's checks.
5. For first registration or a confirmed update, use [branch profile operations](references/branch-profiles.md). Reuse user-supplied parameters and exact-target evidence before asking for missing facts. Do not qualify a build from folder tokens or a copied support label.

Repository and variant hashes are privacy-safe identifiers. Target IDs retain branch/version case and match the canonical memory writer and Zentao reconciliation; do not rewrite historical memory targets during onboarding.

## Commands

The generator uses Python; private project-map parsing uses PyYAML.

```powershell
python "$env:USERPROFILE\.codex\skills\asr3601-project-onboard\scripts\project_onboard.py" --repo . --check
python "$env:USERPROFILE\.codex\skills\asr3601-project-onboard\scripts\project_onboard.py" --repo . --dry-run
python -X utf8 "$env:USERPROFILE\.codex\skills\asr3601-project-onboard\scripts\project_onboard.py" --repo . --prepare
```

--check is read-only; --dry-run previews. --write remains an alias for preparation and view generation. Add --json for structured context. A record does not replace current Git state or actual device verification. Never store private customer mappings or service data in reusable templates.
