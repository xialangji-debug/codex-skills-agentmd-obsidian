# Archived Skills

Archived skills live under:

```text
%USERPROFILE%\.codex\skills.disabled
```

They are not deleted. Restore by moving a folder back to:

```text
%USERPROFILE%\.codex\skills
```

Current reason for archiving: keep high-priority firmware/Zentao skills visible in `available skills`.

## 2026-07-23 architecture consolidation

The canonical retirement manifest is `%USERPROFILE%\.codex\retired-skills.yaml`.
These folders remain recoverable until the review on 2026-08-22:

- `asr3601-bug-intake-orchestrator` -> `asr360x-bug-delivery-orchestrator` intake mode
- `asr3601-fix-verifier` -> `asr3601-fix-closeout-reporter`
- `esp32-c5-eim-jtag-flash` -> `esp32_c5\.codex-project\tools\flash_esp32c5.ps1`
- `asr3602-dump-firmware` -> project-local `.codex-project\tools\build_dump_firmware.ps1`

Do not delete these folders automatically. Restore only after re-running route and registry audits.
