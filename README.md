# Codex Skills + AGENTS.md + Obsidian Markdown Memory

作者：xiakezhen、Codex

这是一个可移植的 Codex 配置包，包含：

- 一组可直接安装到 Codex 的 `skills/`
- 通用版 `AGENTS.md`，用于约束 Codex 如何按需使用 Obsidian Markdown 记忆库
- 一个空的 Obsidian 记忆库模板，适合别人从零开始建立项目记忆
- Windows 一键安装脚本 `scripts/install.ps1`，会在未检测到 Obsidian 时先尝试安装 Obsidian

本仓库不包含私人 Obsidian 笔记、聊天记录、账号令牌、密钥或本机绝对路径。发布前已将个人路径改为占位符。

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
└── skills/
```

## 快速安装（Windows）

在 PowerShell 中运行：

```powershell
git clone https://github.com/xialangji-debug/codex-skills-agentmd-obsidian.git
cd codex-skills-agentmd-obsidian
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
```

脚本会先检测本机是否安装 Obsidian；如果没有，会尝试通过 `winget install Obsidian.Obsidian` 安装。没有 `winget` 时，脚本会提示手动安装地址。

默认会安装到：

```text
%USERPROFILE%\.codex\skills
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
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1 -SkipAgents -SkipObsidian
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

也可以指定路径：

```bash
CODEX_HOME="$HOME/.codex" OBSIDIAN_VAULT="$HOME/Documents/Obsidian/CodexVault" bash scripts/install.sh
```

## 安装后怎么用

1. 重新打开 Codex，让它重新加载 skills。
2. 如果你使用 Obsidian，打开安装后的 vault。
3. 根据自己的项目，把长期可复用信息写到：
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

安装后你自己产生的 Obsidian 笔记不会自动上传到这个仓库。请不要把真实项目机密、账号、token、客户信息或私人聊天原文提交到 Git。

## 更新

如果仓库有更新，可以重新拉取并安装：

```powershell
git pull
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
```

安装脚本默认不会删除你的已有 Obsidian 笔记，只会补齐模板文件。重复安装 skills 会覆盖同名 skill。

## 开源协议

本项目使用 MIT License。详见 `LICENSE`。
