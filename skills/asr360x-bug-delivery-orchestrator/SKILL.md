---
name: asr360x-bug-delivery-orchestrator
description: Classify concrete ASR3601/ASR3602/360x/Crane/LVGL firmware bug evidence in a read-only intake mode, or coordinate explicit end-to-end bug delivery through deep fetch, diagnosis, narrow fixes, verification, one Chinese commit per bug, fix-pattern memory decisions, Zentao resolution, and an explicitly requested release. Use for reports with repro steps, actual/expected results, screenshots, videos, CATStudio logs, downloaded Zentao details, “有没有这个问题/存不存在/先判断再修”, or composite delivery wording such as “修复提交关禅道出版本” and ordered multi-bug processing. Use zentao-bug-triage directly for pure “抓 bug/当前 bug/禅道有哪些 bug” listing or a bare bug ID that still needs fetching.
---

# ASR360x Bug Intake and Delivery Orchestrator

Choose one mode before taking action. Coordinate specialist skills; do not duplicate their implementation.

## Mode Selection

| User intent | Mode | State/external writes |
|---|---|---|
| Provides concrete evidence; asks whether the bug exists, is already fixed, or needs a change | Read-only intake | Do not initialize delivery state, edit code, commit, change Zentao, or release |
| Asks for a narrow fix without commit/Zentao/release wording | Intake, then hand off to firmware triage | Edit only after the request clearly authorizes a fix; do not initialize delivery state |
| Explicitly combines fix with Chinese commit, Zentao resolution, release, or several selected bugs through ordered stages | Delivery | Initialize/resume delivery state and advance only with evidence |
| Asks to fetch/list current bugs or gives a bare bug ID without local detail | Not this skill | Enter `zentao-bug-triage` |

When intent is ambiguous, start in read-only intake. Do not let a terminal phrase such as “做完” silently authorize commits, Zentao writes, or a release.

## Shared Boundaries

- Treat development-side “关禅道” as mark `已解决`, not QA `关闭`, unless tester authority and closure are explicit.
- Release only when the user explicitly says `出版本`, `上传`, `fnOS`, or `release`.
- Preserve unrelated local changes and record the pre-existing dirty worktree.
- A successful build does not equal device, platform, or QA verification.
- Prefer `.codex-project/variant.md` as the canonical variant fingerprint. Refresh it through `asr3601-project-onboard` when missing or stale.
- Never infer protocol from customer/product wording alone.

## Specialist Routing

| Stage or evidence | Owner |
|---|---|
| Project fingerprint | `asr3601-project-onboard` |
| Zentao list/detail/history/attachments | `zentao-bug-triage` |
| CATStudio package or crash/protocol logs | `catstudio-log-extractor` |
| Current-branch diagnosis and narrow fix | `asr3601-lvgl-firmware-triage` |
| Cross-branch comparison or port | `asr3601-cross-branch-porting` |
| Verification, closeout, and validation debt | `asr3601-fix-closeout-reporter` |
| Canonical fix memory and exact target evidence | `obsidian-fix-pattern-memory` |
| Explicit Zentao resolution | `zentao-bug-resolver` |
| Explicit release | Project-local private release workflow from `.codex-project/local.md` |

## Read-Only Intake Mode

### Intake Snapshot

Collect or infer these fields before edits:

```text
来源：截图 / 复现步骤 / CATStudio / Zentao / 用户口述 / 历史问题
项目路径 / branch / commit / dirty：
yl_device_ver / CHIP_ID / TARGET_OS / PS_MODE：
协议 / 客户产品变体 / 构建命令 / 禅道映射：
用户目标：只判断 / 修复 / 移植 / 抓 bug / 提交 / 禅道 / 发布
步骤 / 实际 / 期望：
附件或日志：
初步模块：
历史记忆命中：
第一结论：
```

For Git workspaces, run non-destructive context checks early:

```powershell
git status --short
git branch --show-current
git rev-parse --short HEAD
```

### Evidence Gates

- Inspect screenshots/videos before code search; record visible page, text, icons, state, and trigger path.
- Run `catstudio-log-extractor --fast-evidence` first for CATStudio/log packages. Expand only when compact evidence is insufficient.
- Use already-fetched Zentao detail text locally; re-enter `zentao-bug-triage` only when more history or attachments are required.
- For similar issues, regressions, cross-branch work, or clear error keywords, search only `Codex/fix-patterns/` with 1-3 terms and read only direct matches.
- For existence questions, inspect likely code entry points and history before proposing a patch.
- For protocol ambiguity, identify APP, mini-app, vendor, modem/platform, or backend ownership before firmware edits.

Choose one first-decision label and cite decisive evidence:

```text
存在，需要修：
当前 checkout 已修：
上游/其他分支已修，当前缺失：
可能已修，但需要设备/日志证明：
未确认，需要补日志/视频/复现时间：
平台/后端/硬件/驱动侧，不建议直接改固件：
需求/产品变体差异，不属于缺陷：
```

Return before edits:

```text
第一结论：
当前分支/提交：
证据来源：
历史命中：
疑似模块：
下一步：
需要转入的 skill：
```

## Delivery Mode

Use the existing state schema and commands unchanged. Existing schema-version-1 state files under `~/.codex/asr360x-delivery/states/` remain valid; do not migrate or recreate them.

1. Initialize state before editing, adding `--release-requested` only when release was explicit:

```powershell
python "$env:USERPROFILE\.codex\skills\asr360x-bug-delivery-orchestrator\scripts\delivery_state.py" init --repo . --bugs 2935,2931,2868,2867
```

2. Process bugs in the requested order:

```text
pending -> deep_fetched -> diagnosed -> fixed -> verified -> committed -> memory_decided -> zentao_resolved
```

`memory_decided` is retained for schema-version-1 compatibility, but its meaning is
now “canonical memory recorded”. Every behavior-changing delivered fix must reach
this stage with a real note, `fix_id`, and target ID. Do not complete it with a
skip reason.

3. Advance only after the owning skill produced evidence:

```powershell
python "$env:USERPROFILE\.codex\skills\asr360x-bug-delivery-orchestrator\scripts\delivery_state.py" advance `
  --repo . --bug 2935 --stage verified --evidence "diff checks + target build passed"
```

For `committed`, also pass `--commit <short-sha>`. For `memory_decided`, pass:

```powershell
python "$env:USERPROFILE\.codex\skills\asr360x-bug-delivery-orchestrator\scripts\delivery_state.py" advance `
  --repo . --bug 2935 --stage memory_decided --evidence "canonical target recorded" `
  --fix-id FP-YYYYMMDD-XXXXXXXX --memory-note <fix-pattern.md> --target-id <target-id>
```

4. Before each commit, confirm branch, `HEAD`, and dirty files; stage only the current bug; run both `git diff --check` and `git diff --cached --check`; run targeted verification; use a focused Chinese subject; record the SHA.

5. Before Zentao resolution, require the Bug to have a canonical memory target,
   then print and verify `bug ID -> detail-page product -> canonical project`.
   Require exact product equality. Zero exact matches means zero bugs. Never resolve
   prefix/substring matches from assigned-to-me results.

6. Release only after all selected bugs reach `zentao_resolved` and the state records an explicit release request:

```powershell
python "$env:USERPROFILE\.codex\skills\asr360x-bug-delivery-orchestrator\scripts\delivery_state.py" release `
  --repo . --status released --evidence "uploaded release folder and verified artifacts"
```

7. Resume without repeating completed external actions:

```powershell
python "$env:USERPROFILE\.codex\skills\asr360x-bug-delivery-orchestrator\scripts\delivery_state.py" status --repo .
```

If a wrong-product resolution occurred, stop release progression, reactivate it through `zentao-bug-resolver --reactivate-resolved`, verify `激活`, and record the correction.

## Final Delivery Report

Return one row per bug:

```text
ID | 当前阶段 | 修改 | 验证 | 提交 | 记忆 | 禅道
```

Then state release status, remaining blockers, and the local state file path.
