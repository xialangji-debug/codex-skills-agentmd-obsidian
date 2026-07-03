# Release Rules

## Version Source

Use `gui/lv_watch/lv_apps/yl/yl.h` as the naming source.

Important defines:

```c
#define yl_device_name "LT52"
#define yl_device_ver "LT52_LZ_ASR3602_TW18_V1.1_RTOS_CN_20260626_1530_V1.0.1_Release_WX"
#define yl_hw_ver "TW18_LZ_3602"
#define yl_soft_ver "T001"
```

Unless the user gives extra requirements, only update the `YYYYMMDD_HHMM` segment in `yl_device_ver`.

## Upload Names

Do not upload the raw build output names directly. Copy and rename upload files to the `yl_device_ver` stem:

```text
<yl_device_ver>.zip
<yl_device_ver>.mdb.txt
readme.txt, only when user-provided
```

Example:

```text
LT52_LZ_ASR3602_TW18_V1.1_RTOS_CN_20260702_1400_V1.0.1_Release_WX.zip
LT52_LZ_ASR3602_TW18_V1.1_RTOS_CN_20260702_1400_V1.0.1_Release_WX.mdb.txt
readme.txt
```

## Local Artifacts

Common local output directory:

```text
out/product/craneg_modem_watch
```

Common generated files:

- `craneg_modem_watch_asr3602_8+8mb.zip` or another main firmware zip
- `craneg_modem_watch.mdb.txt`
- `craneg_modem_watch_asr3602_8+8mb_source.zip`

Normally upload the main firmware zip and `.mdb.txt`. Do not upload `*_source.zip` unless requested.

If more than one non-source zip exists, choose only after inspecting timestamps/sizes and asking the user if still ambiguous.

## Build Rule

For a release, update the `yl_device_ver` timestamp first, then run a clean rebuild before packaging. For make-based ASR3602 watch projects, use the confirmed branch-specific environment and run:

```powershell
make clean
make craneg_modem_watch
```

Use the same `PS_MODE`, `TARGET_OS`, and `CHIP_ID` for both commands. Do not package old artifacts from before the clean rebuild.

The one-command controller `scripts/akq_release.ps1` applies this rule by default. It can skip clean/build only when a local `.akq_release_state.json` checkpoint proves the same repo, branch, commit, source diff hash, release timestamp, device version, target, and build environment already completed that stage. Use `-ForceCleanBuild` to rebuild regardless of checkpoint state.

## Readme Rule

Upload `readme.txt` only when the user provides the readme file or exact text. If the user does not provide it, or asks Codex to summarize changes, do not upload a readme file. A Codex-generated summary may be shown to the user for review, but it is not part of the upload unless the user explicitly approves it as the readme content.

## Validation Checklist

Before upload:

- `yl_device_ver` contains the intended release timestamp.
- The release folder name equals the timestamp inside `yl_device_ver`.
- The upload zip name equals `<yl_device_ver>.zip`.
- The upload mdb name equals `<yl_device_ver>.mdb.txt`.
- `readme.txt` is present only if the user provided it.
- The source zip is not included unless explicitly requested.
- Missing remote team/domestic/product folders are not created automatically.
- A missing final timestamp folder named `YYYYMMDD_HHMM` may be created automatically under the confirmed product folder.
- The remote folder upload is automatic for a release request, but same-name remote files are not overwritten without confirmation.
- For interrupted upload resume, same-name remote files may be skipped only when their remote sizes match the local upload files exactly.
