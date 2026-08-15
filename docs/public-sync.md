# Public Snapshot Sync

公开同步使用显式白名单，不从本机 Skills、插件或 MCP 目录推断“应该发布什么”。白名单位于根目录 `public-sync-manifest.json`；新增或移除公开组件必须先通过人工评审修改该文件。

## 安全边界

- 只读取清单列出的全局文件、Skill 目录和 MCP 文件。
- `.system`、插件缓存、虚拟环境、日志、数据库、固件和本机私有文件默认不进入候选树。
- 同步脚本先在临时目录构建候选树，再使用通用规则和本机私有 denylist 扫描；扫描通过后才允许修改仓库。
- 本机 denylist 必须放在 `%USERPROFILE%\.codex\secrets\repo-privacy\denylist.txt`，不得提交到仓库。
- 同步脚本只修改白名单管理的目标和 README 标记区块，不删除未列入清单的仓库目录。
- 仓库 `origin` 必须与清单中的公开仓库完全一致，否则脚本拒绝运行。
- 自动化只能推送独立分支并创建 PR，不得直接推送或自动合并 `main`。

## 本地演练

以下命令只比较，不修改仓库：

```powershell
python -X utf8 .\scripts\sync_public_snapshot.py
```

检查仓库是否已经与公开清单一致：

```powershell
python -X utf8 .\scripts\sync_public_snapshot.py --check
```

在干净工作区中应用候选内容：

```powershell
python -X utf8 .\scripts\sync_public_snapshot.py --apply
```

应用后必须检查并显式暂存：

```powershell
git status --short
git diff --check
git diff
git add AGENTS.md README.md public-sync-manifest.json skills mcp
python -X utf8 .\scripts\privacy_scan.py --root . --staged `
  --denylist "$env:USERPROFILE\.codex\secrets\repo-privacy\denylist.txt"
python -X utf8 .\scripts\run_public_checks.py
```

只有全部检查通过后，才能提交到 `automation/public-sync-YYYYMMDD-HHmm` 形式的独立分支并创建 PR。检查失败、来源缺失、工作区不干净、远端分叉或没有实际变化时都不发布。
