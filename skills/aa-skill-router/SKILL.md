---
name: aa-skill-router
description: Route short local Codex workflow requests to the right skill, local skill index, or project context. Use for ambiguous or high-frequency requests such as 抓 bug, 当前 bug, 禅道, 修 bug, 有没有这个问题, 协议, 符合协议吗, CATStudio, 日志, 出固件, 编译固件, 本地编译刷机, 刷固件, 出 dump 固件, 抓 dump 日志, 收工更新, 怎么验证, 解决说明, 出版本, 初始化当前 360x 项目上下文, skill 整理, or when a target skill is not visible in available skills but exists under C:\Users\84365\.codex\skills.
---

# Skill Router

Use this skill as the first lightweight router before doing work. Do not solve the task here if a specialist skill exists.

## Routing

Prefer the current project `AGENTS.md` and `.codex-project\index.md` when they exist.

| User wording | First destination |
|---|---|
| 抓 bug / 当前 bug / 禅道 / 当前分支 bug | `zentao-bug-triage` |
| 修 bug / 有没有这个问题 / 存不存在 / 先判断再修 | `asr3601-bug-intake-orchestrator` |
| 协议 / 符合协议吗 / APP协议 / 小程序协议 / 平台侧 | `asr3601-protocol-branch-matrix` |
| 出固件 / 编译固件 / 编译一个包 / 本地编译刷机 / 刷固件 / 刷到串口机器 | `asr3602-local-build-flash` + 当前项目 `.codex-project\build.md` |
| 出能抓 dump 的固件 / dump 固件 / 删看门狗出固件 / 3602 dump 固件 / 刷 dump 固件 | `asr3602-dump-firmware` |
| 抓日志 / 保存日志 / 暂停日志 / CATStudio日志 / 崩溃日志 / 设备日志 | `catstudio-log-extractor` + `catstudio-capture` MCP log-only workflow |
| 抓 dump / 抓 dump 日志 / 接收 dump / YModemDump / YModem dump / dump 文件 / CATStudio dump | `catstudio-log-extractor` + `catstudio-capture` MCP dump workflow |
| CATStudio / 日志 | `catstudio-log-extractor` |
| 收工更新 / 怎么验证 / 解决说明 / 禅道标记解决 | `asr3601-fix-closeout-reporter` |
| 出版本 / 上传固件 / fnOS / release | `akq-firmware-release` |
| 初始化当前 360x 项目上下文 / 生成项目 AGENTS | `asr3601-project-onboard` |
| skill 整理 / skill 太多 / 归档 skill / 触发不到 | read `C:\Users\84365\.codex\skills-index\index.md` |

## Fallback

If the destination skill is not listed in current available skills, read the local file directly:

```text
C:\Users\84365\.codex\skills\<skill-name>\SKILL.md
```

For global routing details, read only the needed index:

```text
C:\Users\84365\.codex\skills-index\index.md
C:\Users\84365\.codex\skills-index\zentao\index.md
C:\Users\84365\.codex\skills-index\firmware\index.md
C:\Users\84365\.codex\skills-index\protocol\index.md
C:\Users\84365\.codex\skills-index\logs\index.md
C:\Users\84365\.codex\skills-index\release\index.md
```

Do not read every index by default.

## Guardrails

- For "抓 bug/当前 bug/禅道", prefer the Zentao script workflow. Do not use browser, Chrome, or Computer Use unless the script fails, login is missing, or the user explicitly asks to inspect the web page.
- For "出固件/编译固件/刷固件/刷到串口机器", use `asr3602-local-build-flash` and treat it as local build/flash only. Do not update `yl.h`, create release folders/readme files, upload fnOS, or use `akq-firmware-release` unless the user also says "出版本", "上传", "fnOS", or "release".
- For 360x firmware projects, identify branch, short commit, `yl.h`, product/protocol variant, and Zentao mapping before deep code work.
- For project-specific behavior, use the current repo's `AGENTS.md` and `.codex-project\*.md` before falling back to global assumptions.
