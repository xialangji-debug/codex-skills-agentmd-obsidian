# Contributing

## 提交原则

一个提交只表达一个可独立审查和回滚的目的。如果提交说明需要两个“以及”，或者各部分需要不同验证，就拆成多个提交。

推荐格式：

```text
type(scope): outcome
```

示例：

```text
docs(workflow): explain validation boundaries
test(privacy): scan staged repository content
fix(memory): preserve target verification state
```

行为代码、直接相关测试和完成该行为所必需的文档可以放在同一提交。无关格式化、生成物、README 美化和另一项行为变化必须拆开。

## 本地流程

```powershell
git status --short
git add <明确路径>
git diff --cached --stat
git diff --cached
python -X utf8 .\scripts\privacy_scan.py --root . --staged
python -X utf8 .\scripts\run_public_checks.py
git commit -m "type(scope): outcome"
```

多主题脏工作区不要使用 `git add .`。先明确每个提交的文件集合，再逐组暂存和验证。

公开 Skills/MCP 的同步必须通过 `public-sync-manifest.json` 和 `scripts/sync_public_snapshot.py`，不得临时遍历整个 `%USERPROFILE%\.codex` 后直接复制。完整流程见 [公开快照同步](docs/public-sync.md)。自动化只能创建独立分支和 PR，不能直接更新或自动合并 `main`。

## 隐私与样例

- 只使用 `example.invalid`、`zentao.example`、`SAMPLE_*`、`DEMO-*` 等明显的合成标识。
- 不提交本机绝对路径；文档使用 `%USERPROFILE%`、`$HOME` 或仓库相对路径。
- 不上传固件、构建目录、数据库、日志、截图或设备导出文件。
- 不在测试夹具中复制真实客户名、Bug 编号、版本号或服务地址。

## 验证声明

请分别报告静态检查、构建、真机、平台和 QA 状态。不能用构建通过替代真机回归，也不能用“已解决”替代 QA 关闭。
