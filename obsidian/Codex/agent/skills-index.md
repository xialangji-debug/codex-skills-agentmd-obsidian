---
area: system
domains: []
scope:
  - vault/codex
kind: skill-index
codex_access: manage
trust: working
lifecycle: active
---

# Codex Skills Index

更新时间：2026-08-03（北京时间）

用途：当前可执行 skill 的一行式目录。这里只记录入口和职责，不保存项目流程；具体步骤读取对应 `SKILL.md`、领域索引或项目 `.codex-project/index.md`。

注册状态变化后运行：

```powershell
python -X utf8 "%USERPROFILE%\.codex\skills\skill-usage-tracker\scripts\skill_usage_tracker.py" registry-audit
```

## 领域索引

| 领域 | 按需读取 |
|---|---|
| 固件开发 | `%USERPROFILE%\.codex\skills-index\firmware\index.md` |
| 禅道 | `%USERPROFILE%\.codex\skills-index\zentao\index.md` |
| 协议 | `%USERPROFILE%\.codex\skills-index\protocol\index.md` |
| 日志 | `%USERPROFILE%\.codex\skills-index\logs\index.md` |
| 发布 | `%USERPROFILE%\.codex\skills-index\release\index.md` |
| 记忆 | `%USERPROFILE%\.codex\skills-index\memory\index.md` |

## 本地 Skill

| 用途 | Skill |
|---|---|
| 本地工作流轻量路由 | `aa-skill-router` |
| 跨分支修复移植与集成 | `asr3601-cross-branch-porting` |
| 固件修复验证、收尾和验证债务 | `asr3601-fix-closeout-reporter` |
| 当前分支 LVGL/固件排查与功能闭包审计 | `asr3601-lvgl-firmware-triage` |
| 360x 项目本地上下文初始化 | `asr3601-project-onboard` |
| 协议与分支矩阵 | `asr3601-protocol-branch-matrix` |
| ASR3602 本地构建刷机 | `asr3602-local-build-flash` |
| 多 Bug 修复、中文提交、记忆、禅道解决和显式发布编排 | `asr360x-bug-delivery-orchestrator` |
| CATStudio 离线日志提取 | `catstudio-log-extractor` |
| CC Switch 手机远程与网络诊断 | `codex-ccswitch-mobile` |
| Codex 命令级 Clash 代理 | `codex-clash-proxy` |
| Obsidian 根因记忆、目标矩阵和验证状态 | `obsidian-fix-pattern-memory` |
| Skill 使用统计与注册审计 | `skill-usage-tracker` |
| 禅道 Bug 标记已解决 | `zentao-bug-resolver` |
| 禅道 Bug 抓取、分拣和跨快照状态对账 | `zentao-bug-triage` |

## 系统 Skill

| 用途 | Skill |
|---|---|
| 位图生成与编辑 | `imagegen` |
| OpenAI 官方文档 | `openai-docs` |
| Codex Plugin 创建 | `plugin-creator` |
| 只读缺陷优先代码审查 | `review-agent` |
| Skill 创建与更新 | `skill-creator` |
| Skill 安装 | `skill-installer` |

## 常用插件入口

| 用途 | Skill |
|---|---|
| 浏览器控制 | `browser:control-in-app-browser` |
| Chrome 登录态控制 | `chrome:control-chrome` |
| Windows 桌面应用控制 | `computer-use:computer-use` |
| Word/DOCX | `documents:documents` |
| PDF | `pdf:pdf` |

ESP32-C5 与 ASR dump 的单工程工具从各工程 `.codex-project/index.md` / `local.md` 进入，不注册为全局 Skill。
