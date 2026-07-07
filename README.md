# Codex Skills + AGENTS.md + Obsidian Markdown Memory

作者：xiakezhen、Codex

这是一个可移植的 Codex 配置包，包含：

- 一组可直接安装到 Codex 的 `skills/`，当前同步 49 个本机自定义 skill
- 可选 MCP 工具：CATStudio 日志/设备辅助、AbootDownload 安全烧录辅助、WeFlow 聊天导出辅助
- 通用版 `AGENTS.md`，用于约束 Codex 如何按需使用 Obsidian Markdown 记忆库
- 一个空的 Obsidian 记忆库模板，适合别人从零开始建立项目记忆
- Windows 一键安装脚本 `scripts/install.ps1`，会在未检测到 Obsidian 时先尝试安装 Obsidian，并把 MCP 配置追加到 Codex `config.toml`

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
├── mcp/
│   ├── aboot-download/
│   ├── catstudio-device/
│   └── weflow-export/
└── skills/
```

## 当前同步快照

- 更新时间：2026-07-07
- Skills：49 个本机自定义 skill，未包含 Codex 内置 `.system` skill
- MCP：`aboot-download`、`catstudio-device`、`weflow-export`
- 未发布的本机 MCP：`node_repl` 属于 Codex App 内置运行时，不作为仓库 MCP 分发

<details>
<summary>已同步 skills</summary>

`akq-firmware-release`, `asr3601-bug-intake-orchestrator`, `asr3601-cross-branch-porting`, `asr3601-fix-verifier`, `asr3601-lvgl-firmware-triage`, `catstudio-log-extractor`, `code-review`, `codebase-design`, `codex-ccswitch-mobile`, `codex-clash-proxy`, `codex-windows-fast-patch`, `diagnosing-bugs`, `domain-modeling`, `find-skills`, `grill-with-docs`, `implement`, `improve-codebase-architecture`, `karpathy-guidelines`, `mermaid-visualizer`, `model-release-radar`, `obsidian-fix-pattern-memory`, `pdf`, `playwright`, `playwright-interactive`, `prototype`, `research`, `resolving-merge-conflicts`, `screenshot`, `skill-usage-tracker`, `speech`, `tdd`, `to-issues`, `to-prd`, `transcribe`, `triage`, `ui-ux-pro-max`, `understand`, `understand-chat`, `understand-dashboard`, `understand-diff`, `understand-domain`, `understand-explain`, `understand-knowledge`, `understand-onboard`, `wechat-chat-export`, `weflow-chat-export-analysis`, `yeet`, `zentao-bug-resolver`, `zentao-bug-triage`

</details>

## 快速安装（Windows）

在 PowerShell 中运行：

```powershell
git clone https://github.com/xialangji-debug/codex-skills-agentmd-obsidian.git
cd codex-skills-agentmd-obsidian
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
```

脚本会先检测本机是否安装 Obsidian；如果没有，会尝试通过 `winget install Obsidian.Obsidian` 安装。没有 `winget` 时，脚本会提示手动安装地址。

Windows 脚本默认还会复制 `mcp/` 到 `%USERPROFILE%\.codex\mcp`，并在 `%USERPROFILE%\.codex\config.toml` 里追加：

- `catstudio_device`：查找、复制、导出 CATStudio 日志，辅助查看 ADB/串口设备
- `aboot_download`：查找 release 包、检查 AbootDownload/adownload、生成烧录命令，只有显式确认才会执行烧录
- `weflow-export`：诊断 WeFlow 本机 HTTP API，并导出微信聊天为 JSONL、Markdown 或 CSV

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

macOS / Linux 脚本默认不安装 MCP，因为当前 MCP 主要服务 Windows 上的 CATStudio、AbootDownload 和 WeFlow。如果只想复制 MCP 文件，可设置 `INSTALL_MCP=1` 后手动配置 Codex。

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
