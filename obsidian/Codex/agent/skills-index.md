# Codex Skills Index

更新时间：2026-07-16（北京时间）

用途：当前可执行 skill 的一行式目录。这里只记录入口和职责，不保存项目流程；具体步骤读取对应 `SKILL.md`、领域索引或项目 `.codex-project/index.md`。

注册状态变化后运行：

```powershell
python <CODEX_HOME>\skills\skill-usage-tracker\scripts\skill_usage_tracker.py registry-audit
```

## 领域索引

| 领域 | 按需读取 |
|---|---|
| 固件开发 | `<CODEX_HOME>\skills-index\firmware\index.md` |
| 禅道 | `<CODEX_HOME>\skills-index\zentao\index.md` |
| 协议 | `<CODEX_HOME>\skills-index\protocol\index.md` |
| 日志 | `<CODEX_HOME>\skills-index\logs\index.md` |
| 发布 | `<CODEX_HOME>\skills-index\release\index.md` |
| 记忆 | `<CODEX_HOME>\skills-index\memory\index.md` |

## 本地 Skill

| 用途 | Skill |
|---|---|
| 本地工作流轻量路由 | `aa-skill-router` |
| 阿科奇固件发布 | `akq-firmware-release` |
| 具体固件 Bug 首轮编排 | `asr3601-bug-intake-orchestrator` |
| 跨分支修复移植与集成 | `asr3601-cross-branch-porting` |
| 修复收尾和验证债务 | `asr3601-fix-closeout-reporter` |
| 固件修复验证 | `asr3601-fix-verifier` |
| 当前分支 LVGL/固件排查 | `asr3601-lvgl-firmware-triage` |
| 360x 项目本地上下文初始化 | `asr3601-project-onboard` |
| 协议与分支矩阵 | `asr3601-protocol-branch-matrix` |
| ASR3602 dump 固件 | `asr3602-dump-firmware` |
| ASR3602 本地构建刷机 | `asr3602-local-build-flash` |
| 360x 功能裁剪闭包审计 | `asr360x-feature-closure-auditor` |
| Bug 修复到发布的连续交付 | `asr360x-bug-delivery-orchestrator` |
| CATStudio 离线日志提取 | `catstudio-log-extractor` |
| CATStudio 在线日志准备 | `catstudio-online-log` |
| CC Switch 手机远程与网络诊断 | `codex-ccswitch-mobile` |
| Codex 命令级 Clash 代理 | `codex-clash-proxy` |
| ESP32-C5 EIM/JTAG 构建刷机 | `esp32-c5-eim-jtag-flash` |
| Obsidian 修复模式记忆 | `obsidian-fix-pattern-memory` |
| Skill 使用统计与注册审计 | `skill-usage-tracker` |
| 禅道 Bug 标记已解决 | `zentao-bug-resolver` |
| 禅道 Bug 抓取与分拣 | `zentao-bug-triage` |

## 系统 Skill

| 用途 | Skill |
|---|---|
| 位图生成与编辑 | `imagegen` |
| OpenAI 官方文档 | `openai-docs` |
| Codex Plugin 创建 | `plugin-creator` |
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
| PPT | `presentations:Presentations` |
| 独立表格文件 | `spreadsheets:Spreadsheets` |
| 实时 Excel | `spreadsheets:excel-live-control` |

没有 disabled 目录记录时，不在此文件保留历史禁用名称。
