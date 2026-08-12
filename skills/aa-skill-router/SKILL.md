---
name: aa-skill-router
description: Route short local engineering requests only after identifying the active project/domain. Primary Codex owns ASR360x investigation, memory lookup, planning, code changes, review, and coordination through global specialist skills. ESP32, Codex/Obsidian control-plane work, and general repositories retain their own routes. Use for ambiguous or high-frequency wording such as 抓 bug, 当前 bug, 禅道, 修 bug, 根据记忆修改, 看一下日志, 当前代码怎么实现, 分批提交方案, 修复提交关禅道出版本, cherry-pick, 协议, CATStudio, 编译刷机, dump 固件, 收工更新, 验证债务, 功能裁剪, 根据视频做新 UI, 初始化项目上下文, skill 整理, skill 触发不到, and 索引同步.
---

# Skill Router

Use this skill as a lightweight router for short engineering requests. Do not solve the task here if a specialist skill exists.

## Scope Gate

Before matching wording, identify the active domain from the current workspace, repo `AGENTS.md`, `.codex-project/index.md`, `.codex-project/variant.md`, named model/path, and attached artifacts.

- Route ASR360x code investigation and fixes to the global `asr3601-lvgl-firmware-triage` Skill. Keep primary Codex as the writer and reviewer.
- Route ASR360x branch, device, build, log, release, and remote-write operations directly to their owning global specialist Skills while primary Codex keeps the conversation and review context.
- Route ESP32 or another repository to its project-local instructions and tools. Do not send generic `bug` or `日志` wording to Zentao or CATStudio without ASR/CATStudio evidence.
- Route Skill, Codex, Obsidian work-memory, index, and architecture requests to the control-plane workflow.
- Leave ordinary explanations, personal topics, and requests outside these domains to the normal assistant or their own explicit Skill.
- If domain evidence conflicts, stop before any write, flash, release, or external-system action and resolve the active target.

## Routing

Prefer the current project `AGENTS.md` and `.codex-project\index.md` when they exist.

Fast Fix Mode has routing precedence for a direct Codex request that is one project, one concrete current-branch issue, local source only, expected to touch no more than five files, and has no branch switch, device action, release, Zentao write, batch operation, or requested local model. A repository being present in `local-coder-projects.json` does not override this precedence.

| User wording | First destination |
|---|---|
| ASR 工程 + 抓 bug / 当前 bug / 禅道 / 当前分支 bug | `zentao-bug-triage`；抓取后由主 Codex 直接调查或讨论 |
| 直接对话 + 单个明确问题 + 修复/修改/根据记忆修改 | `asr3601-lvgl-firmware-triage` 的 Fast Fix Mode；主 Codex 直接修改 |
| 有没有这个问题 / 存不存在 / 先判断再修 | `asr3601-lvgl-firmware-triage`；先只读回答，用户授权后再修改 |
| 多个 Bug / 批量调查 | `zentao-bug-triage` 抓取上下文，主 Codex 分项并行调查；后续动作分别交给对应全局 Skill |
| 指定本地模型 | `local-coder-executor`；只执行已批准且边界明确的实现任务 |
| 切分支 / 跨项目 / 按顺序 cherry-pick / 创建整合分支 / 冲突就停 | `asr3601-cross-branch-porting` |
| 协议 / 符合协议吗 / APP协议 / 小程序协议 / 平台侧 | `asr3601-protocol-branch-matrix` |
| ASR 工程 + 自动刷包并抓日志 / 编译刷机抓日志 / 刷机后自动抓日志 | `asr3602-local-build-flash` 与 `catstudio-log-extractor`；按各自预检与授权顺序执行 |
| 出固件 / 编译固件 / 编译一个包 / 本地编译刷机 / 刷固件 / 刷到串口机器 | `asr3602-local-build-flash` + 当前项目 `.codex-project\build.md` |
| 两个设备都连接 / 不要刷错 / 确认目标设备 | 当前项目刷机 skill 的设备身份预检；任何芯片/VID-PID/产物不一致都停止 |
| 出能抓 dump 的固件 / dump 固件 / 删看门狗出固件 / 3602 dump 固件 / 刷 dump 固件 | 当前 ASR 工程的 `.codex-project/local.md`；无局部入口时停止，不套用全局默认 |
| ASR/CATStudio + 抓日志 / 保存日志 / 暂停日志 / `.icl` / Device0 / 崩溃日志 | `catstudio-log-extractor` + `catstudio-capture` MCP log-only workflow |
| ASR/CATStudio + 抓 dump / 接收 dump / YModemDump / dump 文件 | `catstudio-log-extractor` + `catstudio-capture` MCP dump workflow |
| ESP32/其他工程 + 看一下日志 / 为什么失败 / 崩溃 | 当前项目 `AGENTS.md` 和 `.codex-project`；使用项目日志工具或普通代码诊断 |
| 当前代码怎么实现 / 分多少层 / 调用链是什么 | 当前项目上下文 + 窄代码搜索，优先解释现状，不自动修改 |
| 检查改动 / 分批次提交怎么提交 / 出提交方案 | 当前项目规则 + `git status`/`git diff` 只读分析；先给分组方案，不自动提交 |
| 收工更新 / 怎么验证 / 解决说明 | `asr3601-fix-closeout-reporter` |
| 禅道标记解决 / 外部原因 | `zentao-bug-resolver`；预览并确认后写入 |
| 这个改了其他版本要不要改 / 哪些分支也需要改 | `obsidian-fix-pattern-memory` + active projects；只读列候选 |
| 把这些分支/工程一起改 / 同步其他版本 | `asr3601-cross-branch-porting`；明确目标后逐个更新目标记录 |
| 修复、中文提交、关禅道 / 修复提交关禅道出版本 / 多 Bug 按阶段处理 | `asr360x-bug-delivery-orchestrator` |
| 真机通过 / 平台通过 / 测试关闭 / 重新激活 | `asr3601-fix-closeout-reporter` 提交证据，由 `obsidian-fix-pattern-memory` 更新精确目标 |
| 还有哪些没验证 / 待真机 / 验证债务 / 待回归 / 发布前验收清单 | `asr3601-fix-closeout-reporter` 的 Validation Debt Mode |
| 功能裁剪完整吗 / 客户版去掉 / 只保留 / 公版派生 / 菜单隐藏但还上报 | `asr3601-lvgl-firmware-triage` 的 Feature Closure Mode |
| 出版本 / 上传固件 / release | 项目 `.codex-project/local.md` 指定的私有发布流程；按其预检、确认和产物规则执行 |
| 初始化当前 360x 项目上下文 / 生成项目 AGENTS | `asr3601-project-onboard` |
| 根据视频/效果图做新 UI / 替换旧表盘 / 编码器交互 | `asr3601-lvgl-firmware-triage`，先输出页面/资源/交互/验收清单再实现 |
| skill 整理 / skill 太多 / 归档 skill / 触发不到 / 索引同步 / 哪些 skill 失效 | `skill-usage-tracker` 的 `registry-audit`，再按需读取 `%USERPROFILE%\.codex\skills-index\index.md` |

## Fallback

Specialist ASR skills are global Codex skills. If one is not listed, read its active source directly:

```text
%USERPROFILE%\.codex\skills\<skill-name>\SKILL.md
```

All ASR routes above resolve to global Codex Skills; no board or plugin bridge is required.

For global routing details, read only the needed index:

```text
%USERPROFILE%\.codex\skills-index\index.md
%USERPROFILE%\.codex\skills-index\zentao\index.md
%USERPROFILE%\.codex\skills-index\firmware\index.md
%USERPROFILE%\.codex\skills-index\protocol\index.md
%USERPROFILE%\.codex\skills-index\logs\index.md
%USERPROFILE%\.codex\skills-index\release\index.md
```

Do not read every index by default.

## Guardrails

- For "抓 bug/当前 bug/禅道", use `zentao-bug-triage` and its fixed script workflow. Do not open a browser, Chrome, or Computer Use unless the script fails or login is missing.
- For a direct Fast Fix, do not create an inner Codex plan, invoke `local-coder-executor`, poll jobs, or invoke `asr3601-fix-closeout-reporter`. Check the fingerprint once, make one focused search pass, patch directly, run `git diff --check` plus one narrow test/build, and report. When the user explicitly asks to use memory, read up to three relevant notes and read all three when three genuine matches exist.
- After every completed behavior-changing fix, let `obsidian-fix-pattern-memory`
  record or update one canonical root-cause note and the exact current target.
  This local write is automatic; it does not authorize any other branch/project or
  external write.
- Apply the Zentao rule only after confirming an ASR project or explicit Zentao context. Generic `bug` in ESP32 or another repository stays in that project's local workflow.
- Apply CATStudio routing only when the request names CATStudio, `.icl`, Device0, YModemDump, or an ASR project/artifact. Generic `看一下日志` follows the active repository.
- For "出固件/编译固件/刷固件/刷到串口机器", use `asr3602-local-build-flash` and treat it as local build/flash only. Do not update version metadata, create release folders/readme files, or upload unless the user also says "出版本", "上传", or "release".
- Enter Normal Flash + Capture Mode only when the same request contains both flashing and log-capture intent. A plain log request never authorizes flashing, and a plain flash request does not imply CATStudio capture.
- Treat `刷包` as local flashing, not release publication. Treat `抓日志` as normal CATStudio ICL/ILD capture, not YModem dump. If the request explicitly says `dump`, `删看门狗`, or `YModemDump`, stop the normal composite flow and use the project-specific dump route.
- If the request explicitly includes `出版本`, `上传`, or `release`, route publication through the project-local private release workflow; do not silently mix it into the local composite flow.
- Dump firmware is project-specific. Read the current ASR checkout's `.codex-project/local.md`; if it has no dump entry, stop and ask for the owning project instead of invoking a global dump workflow.
- For composite delivery, keep primary Codex responsible for sequencing and review, and invoke only the owning global Skills for branch, build/flash, logs, release, artifacts, or confirmed remote writes. Development-side “关禅道” means resolve, not QA close.
- A normal “抓 bug” fast fetch may reconcile deterministic local target states.
  `resolved` remains QA pending; only `closed` upgrades QA evidence. A missing row
  must be detail-refreshed before any state change.
- For an explicit user request for the local model inside a root enabled by `local-coder-projects.json`, keep primary Codex responsible for evidence, plan, and verification; use `local-coder-executor` for one bounded Bug at a time. Never use the worker merely because a direct Fast Fix repo is allowlisted.
- When more than one embedded target is connected, never choose a port by COM number alone. Match project chip, artifact identity, USB VID/PID, and probe result before flashing.
- For a direct Fast Fix in a 360x firmware project, read `.codex-project\variant.md` once and confirm only repo, branch, short commit, dirty state, target variant, and the narrow build command needed by the change. Refresh it only when a required fact is missing or stale. Build/flash/release, protocol, and external-system work must confirm the complete dynamic fingerprint and refresh it through `asr3601-project-onboard` when needed.
- For project-specific behavior, use the current repo's `AGENTS.md` and `.codex-project\*.md` before falling back to global assumptions.
- For code explanations and commit-splitting plans, remain read-only unless the user separately authorizes edits or commits.
- For skill registry cleanup, run `python "%USERPROFILE%\.codex\skills\skill-usage-tracker\scripts\skill_usage_tracker.py" registry-audit` first. Keep it read-only until the user has reviewed the active/disabled/plugin and stale-route report.
