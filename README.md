# Codex Skills + AGENTS.md + Obsidian Markdown Memory

作者：xiakezhen、Codex

这是一个可移植的 Codex 配置包，包含：

- 一组可直接安装到 Codex 的 `skills/`，当前同步 22 个本机自定义 skill
- 一行式主目录与按需领域目录 `skills-index/`
- 可选 MCP 元数据：Everything 文件搜索
- 通用版 `AGENTS.md`，用于约束 Codex 如何按需使用 Obsidian Markdown 记忆库
- 一个空的 Obsidian 记忆库模板，适合别人从零开始建立项目记忆
- Windows 一键安装脚本 `scripts/install.ps1`，会在未检测到 Obsidian 时先尝试安装 Obsidian，并复制仓库内公开 MCP 元数据

本仓库不包含私人 Obsidian 笔记、聊天记录、账号令牌、密钥或 MCP 本机私有配置。少量 skill 示例会保留可替换的本机路径写法，真正的密码、token 和私有配置不要提交。

## 目录结构

```text
.
├── AGENTS.md
├── LICENSE
├── README.md
├── obsidian/
│   └── Codex/
│       ├── AGENTS.md
│       ├── TODO.md
│       ├── agent/
│       │   └── open-loops.md
│       ├── fix-patterns/
│       ├── notes/
│       ├── people/
│       └── projects/
├── scripts/
│   ├── install.ps1
│   └── install.sh
├── skills-index/
│   ├── index.md
│   ├── firmware/
│   ├── zentao/
│   ├── protocol/
│   ├── logs/
│   ├── release/
│   └── memory/
├── mcp/
│   └── everything-search/
└── skills/
```

## 当前同步快照

- 更新时间：2026-07-17
- Skills：22 个本机自定义 skill，未包含 Codex 内置 `.system` skill
- MCP：`everything-search`（仅同步公开说明、许可证、`pyproject.toml` 和示例配置）
- 未发布的本机 MCP：`node_repl` 属于 Codex App 内置运行时，不作为仓库 MCP 分发

### 2026-07-17 更新

- 按当前本机状态收敛仓库 MCP，同步为仅保留 `everything-search` 的公开元数据；移除已不在这台机器上启用的 `aboot-download`、`catstudio-online-log`、`weflow-export`。
- Windows / macOS / Linux 安装说明同步更新：仓库不再自动向 Codex `config.toml` 追加这些旧 MCP 配置。
- 同步本机 `akq-firmware-release` 等 skill 的最新公开内容，并清理仓库里误带入的 Python `__pycache__` 缓存产物。

### 2026-07-14 更新

- 新增 `asr360x-feature-closure-auditor`，用于检查客户版功能裁剪是否真正闭环，而不只是隐藏菜单。
- 新增 `skill-usage-tracker`，用于统计 skill 使用情况、审计 active/disabled/plugin 注册状态和失效路由。
- 保留 `codex-clash-proxy` 和 `codex-ccswitch-mobile`，分别支持命令级 Clash 下载代理和 CC Switch 手机远程配置。
- 移除当前电脑已不再启用的 `code-review`、`grill-with-docs`、`to-prd`、`hatch-pet`、`playwright`。
- 扩展修复收尾和验证流程，加入验证债务汇总、变体指纹、LVGL 多语言/长文本预检。
- 更新项目接入、Bug 分流、跨分支移植、协议矩阵、固件构建发布和禅道抓取规则。
- 更新通用 `AGENTS.md`，补充简体中文、skill/project 路由、禅道 Bug 获取和记忆写入规则。

### 2026-07-15 更新

- 优化 `zentao-bug-triage`：快照会只读关联 `fix-patterns`，输出高/中/低/未命中和最多三条证据候选。
- 新增独立的修复资格判断：区分可直接修复候选、可移植候选、需先查代码、需先深抓、需日志验证、复测激活、平台问题和底层问题。
- 收紧自动修复门槛：同型号或同分支文本不能单独形成记忆命中；即使是高命中，也必须先核对当前代码、Git 历史和本地改动。
- 新增离线边界测试，覆盖同项目高命中、跨项目移植、未命中和复测激活禁止直接修复。

### 2026-07-16 更新

- 全局 `AGENTS.md` 去项目化：只保留语言、长期记忆、隐私和通用路由原则；360x/禅道步骤下沉到项目本地上下文和 owning skill。
- 新增 `asr360x-bug-delivery-orchestrator`，用本地断点状态编排深抓、修复、验证、逐 Bug 中文提交、记忆判断、禅道解决和显式发布。
- `skill-usage-tracker` 改为按文件字节游标增量扫描，报告默认不重扫，并默认只统计真实 skill 读取/工具调用。
- 跨分支 skill 新增 ordered cherry-pick Integration Mode；项目初始化新增 `--check`、`device.md` 和 `memory.md`。
- CC Switch 增加 HTTP/SOCKS/WS/OAuth 分层诊断；ASR/ESP32 刷机统一增加目标设备身份预检。
- 修复记忆新增“已验证/待复核”可信度更新，复测激活可降级旧模式而不删除历史。
- 安装脚本同时安装一行式主索引和按需领域索引。

<details>
<summary>已同步 skills</summary>

`aa-skill-router`, `akq-firmware-release`, `asr3601-bug-intake-orchestrator`, `asr3601-cross-branch-porting`, `asr3601-fix-closeout-reporter`, `asr3601-fix-verifier`, `asr3601-lvgl-firmware-triage`, `asr3601-project-onboard`, `asr3601-protocol-branch-matrix`, `asr3602-dump-firmware`, `asr3602-local-build-flash`, `asr360x-bug-delivery-orchestrator`, `asr360x-feature-closure-auditor`, `catstudio-log-extractor`, `catstudio-online-log`, `codex-ccswitch-mobile`, `codex-clash-proxy`, `esp32-c5-eim-jtag-flash`, `obsidian-fix-pattern-memory`, `skill-usage-tracker`, `zentao-bug-resolver`, `zentao-bug-triage`

</details>

## 快速安装（Windows）

在 PowerShell 中运行：

```powershell
git clone https://github.com/xialangji-debug/codex-skills-agentmd-obsidian.git
cd codex-skills-agentmd-obsidian
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
```

脚本会先检测本机是否安装 Obsidian；如果没有，会尝试通过 `winget install Obsidian.Obsidian` 安装。没有 `winget` 时，脚本会提示手动安装地址。

Windows 脚本在未指定 `-SkipMcp` 时会把 `mcp/` 复制到 `%USERPROFILE%\.codex\mcp`。当前仓库只保留 `everything-search` 的公开元数据，不会自动向 Codex `config.toml` 追加 MCP server 配置。

需要时请按 `mcp/everything-search/everything_search_config.example.json` 手动配置 `everything-search`。

如不需要 MCP：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1 -SkipMcp
```

默认会安装到：

```text
%USERPROFILE%\.codex\skills
%USERPROFILE%\.codex\mcp
%USERPROFILE%\.codex\AGENTS.md
%USERPROFILE%\Documents\Obsidian\CodexVault\Codex
```

如果你的 Codex 或 Obsidian 路径不同，可以指定参数：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1 `
  -CodexHome "D:\Tools\codex" `
  -VaultPath "D:\Obsidian\CodexVault"
```

只安装 skills：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1 -SkipAgents -SkipObsidian -SkipMcp
```

如果你已经自己安装 Obsidian，或者只想复制模板、不希望脚本安装 Obsidian：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1 -SkipObsidianInstall
```

## 快速安装（macOS / Linux）

```bash
git clone https://github.com/xialangji-debug/codex-skills-agentmd-obsidian.git
cd codex-skills-agentmd-obsidian
bash scripts/install.sh
```

macOS / Linux 脚本不会自动安装 Obsidian。需要 Obsidian 的话，请先从官网安装：<https://obsidian.md/download>。

macOS / Linux 脚本默认不安装 MCP。如果只想复制 `everything-search` 的公开元数据，可设置 `INSTALL_MCP=1` 后再按示例手动配置 Codex。

也可以指定路径：

```bash
CODEX_HOME="$HOME/.codex" OBSIDIAN_VAULT="$HOME/Documents/Obsidian/CodexVault" bash scripts/install.sh
```

## 安装后怎么用

1. 重新打开 Codex，让它重新加载 skills。
2. 如果你使用 Obsidian，打开安装后的 vault。
3. 如果启用 MCP，重启 Codex 后查看工具是否出现；如本机工具路径不同，把对应 `*.example.json` 复制为 `*_config.json` 后修改路径，或使用环境变量覆盖路径。
4. 根据自己的项目，把长期可复用信息写到：
   - `Codex/projects/`
   - `Codex/people/`
   - `Codex/notes/`
   - `Codex/fix-patterns/`
   - `Codex/TODO.md`
   - `Codex/agent/open-loops.md`

## AGENTS.md 的核心规则

这个模板的目标是让 Codex 使用 Obsidian 作为长期项目记忆，但避免浪费 token：

- 不保存完整聊天记录
- 默认不读取整个记忆库
- 只有跨分支移植、类似问题、回归问题、明确日志关键词或用户明确要求时才查记忆
- 先窄范围搜索，再读取 1-3 篇最相关笔记
- 可复用修复模式写入 `Codex/fix-patterns/`
- 密码、密钥、令牌、身份证、银行卡等敏感信息不要写入记忆库

## 关于隐私

这个仓库只提供可复用配置、技能和空模板。

安装后你自己产生的 Obsidian 笔记、MCP 本机配置和抓取日志不会自动上传到这个仓库。请不要把真实项目机密、账号、密码、token、客户信息、私有附件或私人聊天原文提交到 Git。

## 更新

如果仓库有更新，可以重新拉取并安装：

```powershell
git pull
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
```

安装脚本默认不会删除你的已有 Obsidian 笔记，只会补齐模板文件。重复安装 skills 会覆盖同名 skill。

## 开源协议

本项目使用 MIT License。详见 `LICENSE`。
