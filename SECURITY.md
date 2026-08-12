# Security Policy

## 公开内容边界

本仓库不接受包含以下内容的提交、Issue、Discussion 或附件：

- 密码、Token、Cookie、私钥和设备密钥。
- 客户源码、真实项目映射、内部服务地址和外部系统数据。
- 未脱敏的日志、固件、数据库、截图、视频或聊天记录。

## 报告安全问题

不要在公开 Issue 中粘贴敏感内容。优先通过 GitHub 的 [Private Vulnerability Reporting](https://github.com/xialangji-debug/codex-skills-agentmd-obsidian/security/advisories/new) 提交最小复现；报告中仍应删除不必要的凭据和私人信息。

如果真实凭据已经公开，先在对应服务中撤销或轮换凭据，再处理 Git 历史。仅删除当前文件不能让旧提交、fork 或缓存中的内容失效。

## 提交前检查

```powershell
python -X utf8 .\scripts\privacy_scan.py --root . --staged
python -X utf8 .\scripts\run_public_checks.py
```

本机专用的 denylist 必须保存在 `.privacy-denylist.local.txt` 或用户私有配置目录，不能提交到仓库。
