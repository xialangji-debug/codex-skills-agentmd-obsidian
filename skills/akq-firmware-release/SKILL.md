---
name: akq-firmware-release
description: Prepare and automatically publish Akq domestic TW10/TW18 ASR3602 watch firmware releases. Use when the user asks to "出版本", upload firmware to fnOS/yuelaniot, update `yl.h` `yl_device_ver`, run `make clean` and rebuild, package `craneg_modem_watch` outputs, rename firmware zip/mdb files for Akq domestic folders, or manage TW10/TW18 release folders/readme files under 阿科奇-国内.
---

# Akq Firmware Release

Use this skill to prepare an Akq domestic firmware release end to end: update the release timestamp, clean rebuild with the correct project configuration, find the generated firmware artifacts, rename copies to the `yl_device_ver` stem, and automatically upload to the correct fnOS team folder.

## Safety Rules

- Do not guess the build configuration. Derive it from the current repo, previous successful terminal output, build scripts, project notes, or ask the user.
- Treat a user request to "出版本" as permission to upload to the confirmed product folder and to create only the final timestamp release folder named `YYYYMMDD_HHMM` when it is missing.
- If the remote team, domestic, or product folder does not exist, stop and ask the user to confirm the mapping. Do not create those larger folders automatically.
- Do not overwrite, delete, or replace existing remote files without an explicit confirmation at that action point.
- Do not store or print the fnOS password in SKILL.md, Obsidian, final answers, logs, or readme files.
- If login fails once with saved credentials, stop and ask the user to confirm the password before trying again.
- If the product folder or build artifact is ambiguous, list the candidates and ask the user to choose.
- Preserve unrelated local source changes.
- Do not create a git commit for a plain "出版本" or "重新出版本" request. Only commit release timestamp or code changes when the user explicitly asks to "提交", "commit", or otherwise requests a git commit.
- Before any clean build, check `git status --short`. If there are untracked source-like files such as new `.c/.h/CMakeLists.txt` entries, stop and commit/stage them first when the user asked to submit; otherwise ask before using `-AllowUntrackedSource`. Clean release flows must not silently omit or delete new ported files.
- When the user asks “依次提交” plus “出版本”, use this order by default: fix commits one by one, then the `yl.h` release-version commit, then clean build/package/upload. This keeps the release checkpoint commit equal to final `HEAD`.
- For this user's Akq releases, always create and upload `readme.txt` in the release folder by default. Do not commit repo `README.md` unless the user explicitly says to submit/readme/commit it.

## Credentials

The fnOS credential is stored outside the skill as a Windows user-encrypted PowerShell credential:

`%USERPROFILE%\.codex\secrets\akq-firmware-release\fnos.credential.xml`

Load it only when logging in:

```powershell
$cred = Import-Clixml -LiteralPath "$env:USERPROFILE\.codex\secrets\akq-firmware-release\fnos.credential.xml"
$username = $cred.UserName
$password = $cred.GetNetworkCredential().Password
```

Use the username/password to fill the login form, but never echo `$password`. If this file is missing, unreadable, or rejected by the website, ask the user for updated credentials and save the replacement using the same encrypted format.

## Workflow

Preferred fast path: use `scripts/akq_release.ps1` for normal releases. It performs remote preflight first, updates `yl.h`, protects against untracked source before clean builds, runs clean/build only when the current release state has not already completed those steps, prepares renamed upload files, generates or copies release `readme.txt`, uploads, and writes a local `.akq_release_state.json` checkpoint under the release upload directory for safe resume.

1. Identify the release context:
   - Run `git status --short`, `git branch --show-current`, and `git rev-parse --short HEAD`.
   - Treat `??` files under source/config paths as a release blocker before clean builds. Commit them when the user requested commits; otherwise confirm before bypassing with `-AllowUntrackedSource`.
   - Find `gui/lv_watch/lv_apps/yl/yl.h` or search with `rg -n "yl_device_ver"`.
   - Extract `yl_device_ver`, `yl_device_name`, `yl_hw_ver`, and `yl_soft_ver`.
   - Determine the release time in `YYYYMMDD_HHMM` format. If the user did not provide it, ask or use the intended build time only after confirmation.

2. Update `yl.h` conservatively:
   - Default behavior: replace only the `YYYYMMDD_HHMM` segment inside `yl_device_ver`.
   - Do not change `V1.0.x`, model prefix, `TW10/TW18`, `CN`, `Release_WX`, `yl_hw_ver`, or `yl_soft_ver` unless the user explicitly requests it.
   - Leave this timestamp change as a working-tree change for a normal release; do not commit it unless the user explicitly requests a commit.
   - If the user requested commits, commit code fixes first, then commit the `yl.h` timestamp update, then build/upload. Do not build/upload first and commit the version later.

3. Clean rebuild:
   - Confirm the correct build command/configuration for this repo and branch before compiling.
   - Run the clean command for the same build configuration before building. For make-based ASR3602 watch projects, this is normally `make clean` followed by the target build using the same `PS_MODE`, `TARGET_OS`, and `CHIP_ID`.
   - For ASR3602 watch projects, the common output target is usually under `out/product/craneg_modem_watch`, but do not assume that if the repo differs.
   - After build, inspect artifact timestamps and sizes. Use only artifacts generated by the clean rebuild, not older manual zip files left in the output directory.

4. Prepare upload artifacts:
   - Use `scripts/prepare_release_package.py` with `--dry-run` first.
   - Main upload files are normally:
     - firmware zip, renamed to `<yl_device_ver>.zip`
     - mdb text file, renamed to `<yl_device_ver>.mdb.txt`
     - `readme.txt`, generated from the repo `README.md` latest section and recent commits by `akq_release.ps1`, unless `-NoReadme` is passed
   - Do not upload source packages such as `*_source.zip` unless the user explicitly asks.
   - Prefer copying renamed files into `out/product/<target>/release_upload/<YYYYMMDD_HHMM>/` instead of renaming build outputs in place.

5. Handle `readme.txt`:
   - Default release behavior for this user: keep repo `README.md` updated as a local changelog when useful, generate/copy `release_upload/<YYYYMMDD_HHMM>/readme.txt`, and upload it with the release.
   - Do not commit repo `README.md` unless the user explicitly asks to submit/readme/commit it.
   - If the user provides a specific readme path, pass it with `-Readme`; otherwise let `akq_release.ps1` generate `readme.txt`.
   - For readme-only补传 after zip/mdb already exist remotely, use `fnos_upload_release.js --include-readme --allow-existing-identical`; it skips identical zip/mdb and uploads only missing/different `readme.txt`.

6. Upload to fnOS:
   - Open `https://fnos.yuelaniot.com:5667`.
   - Navigate through 文件管理 to `团队文件 > 阿科奇 > 阿科奇-国内`.
   - Choose the correct product folder using `references/project-folder-map.md`: explicit CLI folder first, exact/current branch mapping second, `yl_device_ver` as confirmation, and local path only as a weak hint. Do not let a different local checkout path block a branch/version-confirmed mapping.
   - Enter the release folder named exactly `YYYYMMDD_HHMM`.
   - If the release folder named exactly `YYYYMMDD_HHMM` does not exist under the confirmed product folder, create that final timestamp folder automatically.
   - Upload the renamed zip, renamed `.mdb.txt`, and release `readme.txt` automatically unless `-NoReadme` was used.
   - Verify the remote folder contains exactly the intended release files. If any same-name remote file exists, stop and ask before overwriting.

7. Resume behavior:
   - If a previous `akq_release.ps1` run wrote a matching checkpoint for the same repo, branch, commit, source diff hash, release time, device version, target, and build environment, skip completed build/package steps.
   - If upload was interrupted after files reached fnOS, rerun the same command; upload uses `--allow-existing-identical` so same-name same-size files are treated as already complete.
   - If a local package/checkpoint uses the same release time but a different source diff hash, stop by default. Use a new release time for a new build, `-TrustExistingPackage` to verify/upload the existing package, or `-ForceCleanBuild` only when rebuilding the same timestamp is intentional.
   - If only the version commit/checkpoint is out of sync but the package files are known-good, use `-TrustExistingPackage`; the script skips collision-only preflight and verifies identical remote files in the upload step.
   - Use `-ForceCleanBuild` to intentionally ignore checkpoints and rebuild from clean.

## References

- Read `references/fnos-paths.md` when navigating fnOS or choosing a remote folder.
- Read `references/fnos-upload-api.md` when implementing or debugging automatic fnOS uploads.
- Read `references/release-rules.md` when validating naming, timestamps, and upload contents.
- Read `references/project-folder-map.md` when mapping a local repo/branch/product to an Akq domestic folder.

## Scripts

Use `scripts/akq_release.ps1` as the default one-command release controller:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.codex\skills\akq-firmware-release\scripts\akq_release.ps1" -Repo .
```

Useful options:

```powershell
# Dry-run: remote preflight plus planned yl.h timestamp update; no local writes, build, package, or upload.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.codex\skills\akq-firmware-release\scripts\akq_release.ps1" -Repo . -ReleaseTime 20260702_2359 -DryRun

# Resume or reproduce a known timestamp.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.codex\skills\akq-firmware-release\scripts\akq_release.ps1" -Repo . -ReleaseTime 20260702_1817

# Build/package only, without upload.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.codex\skills\akq-firmware-release\scripts\akq_release.ps1" -Repo . -NoUpload

# Reuse an existing local package/checkpoint and verify/upload missing readme or identical remote files.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.codex\skills\akq-firmware-release\scripts\akq_release.ps1" -Repo . -ReleaseTime 20260702_1817 -TrustExistingPackage

# Special fixed-version branches: keep yl.h/yl_device_ver unchanged, use ReleaseTime only for the remote folder.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.codex\skills\akq-firmware-release\scripts\akq_release.ps1" -Repo . -KeepYlVersion

# Explicitly skip release readme generation/upload.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.codex\skills\akq-firmware-release\scripts\akq_release.ps1" -Repo . -ReleaseTime 20260702_1817 -NoReadme
```

The controller defaults to `PS_MODE=LITE_LTEONLY`, `TARGET_OS=ALIOS`, `CHIP_ID=CRANEL`, and target `craneg_modem_watch`, matching the confirmed `D:\XM\c10lezhi` ASR3602 watch release build. Override these parameters only when the branch configuration is confirmed.

Use `scripts/prepare_release_package.py` for deterministic local packaging:

```powershell
python "$env:USERPROFILE\.codex\skills\akq-firmware-release\scripts\prepare_release_package.py" --repo . --release-time 20260702_1400 --dry-run
```

Then run without `--dry-run` after reviewing the plan. Pass `--firmware-zip`, `--mdb`, or `--product-dir` if auto-detection is ambiguous. Pass `--readme` when using an explicit readme file; the release controller can otherwise generate one.

Use `scripts/fnos_upload_release.js` for automatic fnOS upload after local packaging:

```powershell
$env:NODE_PATH="$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules"
node "$env:USERPROFILE\.codex\skills\akq-firmware-release\scripts\fnos_upload_release.js" --repo . --dry-run
node "$env:USERPROFILE\.codex\skills\akq-firmware-release\scripts\fnos_upload_release.js" --repo . --include-readme --allow-existing-identical
```

The upload script resolves the remote team/product/release folder by name and project mapping, creates only the final missing timestamp folder when needed, checks remote same-name collisions by listing the folder first, uploads zip/mdb/readme files from `release_upload/<YYYYMMDD_HHMM>`, and verifies remote filenames and sizes. It refuses to create missing team/domestic/product folders; ask the user to confirm if those are missing or ambiguous. Pass `--readme <path>` only when uploading a specific readme file outside the release directory.

Use `--resolve-only` to quickly verify release names and the mapped product folder without logging in or opening a browser:

```powershell
$env:NODE_PATH="$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules"
node "$env:USERPROFILE\.codex\skills\akq-firmware-release\scripts\fnos_upload_release.js" --repo . --release-time 20260703_2002 --resolve-only
```

For compile-before-upload checks, pass `--preflight` to `scripts/fnos_upload_release.js`. For idempotent resume after an interrupted upload, pass `--allow-existing-identical` so remote files with matching names and sizes are skipped instead of treated as overwrite attempts.

## MCP Fast Paths

- For readme-only補传, do not rerun clean/build or the full release controller. Generate/update `release_upload/<YYYYMMDD_HHMM>/readme.txt`, then run:

```powershell
$env:NODE_PATH="$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules"
node "$env:USERPROFILE\.codex\skills\akq-firmware-release\scripts\fnos_upload_release.js" --repo . --release-time 20260703_2002 --include-readme --allow-existing-identical
```

- For flashing a just-built package with the `aboot_download` MCP tools, first inspect the package, then list devices only if the port is unknown. When the previous successful device is still `ASR Modem Device (COM3)`, use COM3 directly with `auto_enable_usb=true`, `at_fallback=true`, `reboot_after=true`, `quit_after=true`, and `baudrate=115200`. Report the final MCP status such as `SUCCEEDED`; do not paste the full flashing log unless the user asks.
