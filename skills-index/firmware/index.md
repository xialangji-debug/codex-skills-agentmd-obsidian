# Firmware Skill Index

| Request | Skill |
|---|---|
| Raw firmware bug report, screenshots, repro steps, existence check | `asr3601-bug-intake-orchestrator` |
| Current-branch code triage and narrow fix | `asr3601-lvgl-firmware-triage` |
| Cross-branch or sibling-project port | `asr3601-cross-branch-porting` |
| Ordered cherry-pick integration with conflict-stop | `asr3601-cross-branch-porting` Integration Mode |
| Fix + verify + Chinese commit + Zentao resolution + optional release | `asr360x-bug-delivery-orchestrator` |
| Local build, compile one package, flash to connected device | `asr3602-local-build-flash` |
| Dump-capable firmware build/flash, watchdog config removed temporarily | `asr3602-dump-firmware` |
| Verify fix before final report | `asr3601-fix-verifier` |
| Closeout report, verification summary, Zentao solution note | `asr3601-fix-closeout-reporter` |
| Initialize project-local context | `asr3601-project-onboard` |

Before firmware edits, record branch, short commit, product/protocol variant, and dirty worktree status.
For plain "出固件/刷固件", do not use release upload skills unless the user also asks for "出版本", "上传", "fnOS", or "release".
When multiple embedded devices are connected, require project/artifact/chip/USB identity agreement before flashing.
