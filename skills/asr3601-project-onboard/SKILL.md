---
name: asr3601-project-onboard
description: Initialize, refresh, or check local project context and a canonical variant fingerprint for ASR3601/ASR3602/360x/Crane/LVGL firmware repositories. Use for 初始化当前 360x 项目上下文, 生成项目 AGENTS, 新项目接入 Codex, 记录编译命令, 生成变体指纹, 检查上下文是否过期, project onboarding, or when a checkout needs project-level index/build/zentao/protocol/variant/device/memory files and local git exclude entries.
---

# ASR3601 Project Onboard

Use this skill to create lightweight project-local context for one firmware checkout. It keeps global skills shared while isolating per-project rules and one canonical live fingerprint.

`.codex-project\variant.md` is the only generated source for dynamic checkout facts. Branch, commit, dirty state, product/version identity, protocol choice, build command/parameters, device target parameters, memory aliases, and Zentao names/IDs/status must not be copied into `AGENTS.md`, `index.md`, `zentao.md`, `build.md`, `protocol.md`, `device.md`, or `memory.md`.

## Workflow

1. Inspect the target repo:

```powershell
git status --short
git branch --show-current
git rev-parse --short HEAD
```

2. Read `gui\lv_watch\lv_apps\yl\yl.h` when present and extract `yl_device_name`, `yl_device_ver`, and `yl_hw_ver`.
3. Match the branch and version against:

```text
%USERPROFILE%\.codex\zentao-bug-triage\project-map.local.md
```

4. Generate or refresh:

```text
AGENTS.md
.codex-project\index.md
.codex-project\zentao.md
.codex-project\build.md
.codex-project\protocol.md
.codex-project\variant.md
.codex-project\device.md
.codex-project\memory.md
```

5. Add these local context files to `.git\info\exclude` so they do not pollute source commits.
6. Treat `.codex-project\variant.md` as the canonical preflight fingerprint for every ASR bug, port, verification, build, release, protocol, and Zentao workflow. It must include repo, privacy-safe `repo_id`/`variant_id`/`target_id`, branch, commit, dirty state, `yl_*` identity, chip, OS, protocol, customer/product variant, build command and parameters, device target parameters, fix-pattern search aliases, and the complete current Zentao mapping.
7. Keep only stable device-selection rules in `.codex-project\device.md`; never persist a COM number as identity. Keep only stable memory lookup policy in `.codex-project\memory.md`. Both files must point to `variant.md` for current values.
8. If `.codex-project\local.md` exists, preserve it byte-for-byte. It is a project-owned extension for local tools and constraints; this generator must never create, overwrite, or include it in the generated-file set.
9. In the completion response, provide clickable absolute Markdown links for `AGENTS.md` and every generated `.codex-project` file. When a protocol document is mapped, also provide clickable links to its original and searchable extracted file.

The three IDs are one-way hashes used by local fix memory and Zentao snapshot
reconciliation. Do not copy the raw repository path, remote URL, customer mapping,
or service address into fix-pattern managed state or reusable Skill repositories.

## Script

Use the bundled script for deterministic generation:

```powershell
python "$env:USERPROFILE\.codex\skills\asr3601-project-onboard\scripts\project_onboard.py" --repo . --write
```

Useful options:

```powershell
python "$env:USERPROFILE\.codex\skills\asr3601-project-onboard\scripts\project_onboard.py" --repo C:\path\to\firmware-repo --dry-run
python "$env:USERPROFILE\.codex\skills\asr3601-project-onboard\scripts\project_onboard.py" --repo . --write --force
python "$env:USERPROFILE\.codex\skills\asr3601-project-onboard\scripts\project_onboard.py" --repo . --write --no-exclude
python "$env:USERPROFILE\.codex\skills\asr3601-project-onboard\scripts\project_onboard.py" --repo . --check
```

## Defaults

- Confirmed entries from the private local project map can be used automatically. Never put real customer, branch, version, device, external-system ID, or service data in the bundled template.
- Unmatched or unconfirmed project mappings must be marked as needing user confirmation; do not guess a Zentao project ID.
- Protocol categories are only `电信乐智协议`, `小程序协议`, and `APP协议`: branches or version tokens containing 乐智/电信/LZ use 电信乐智协议; explicit APP uses APP协议; otherwise default to 小程序协议. Treat 物卡/公版/客户名 as product variants, not separate protocol categories.
- Build commands may be generated from confirmed project notes or local repository evidence. If uncertain, write the safest known candidate and its caveat into `variant.md`; never duplicate it in `build.md`.
- Do not copy global skills into the project. Project files should point back to the global skill path.
- Regeneration may change `variant.md` whenever the checkout changes. The other generated files are stable policy/index files and should only change when the project-context contract changes.
