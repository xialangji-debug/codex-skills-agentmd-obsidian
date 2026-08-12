# Release Skill Index

| Request | Skill |
|---|---|
| 出版本 / 重新出版本 / 上传 | Project-local release workflow from `.codex-project/local.md`, after approval |
| Build/package release artifacts | Project-local release workflow |
| Fix closeout before resolving release bugs | `asr3601-fix-closeout-reporter` |
| 发布门禁、产物记录和发布前验收 | Project-local release workflow + `asr3601-fix-closeout-reporter` |

Plain "出固件", "编译一个包", or "刷到串口机器" is not a release request; route it to `asr3602-local-build-flash`.
For project-specific compile command, read `.codex-project\build.md` first when present.
