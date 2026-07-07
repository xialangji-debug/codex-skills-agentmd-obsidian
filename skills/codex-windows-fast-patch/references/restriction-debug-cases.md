# Restriction Debug Cases

Use this reference only when the main `SKILL.md` workflow does not explain the current Codex Desktop restriction, plugin gate, Computer Use failure, browser_use failure, or Fast Mode failure. Keep the investigation evidence-based: prefer package status, config, plugin list output, Desktop logs, sandbox logs, and captured network requests over assumptions.

## Fast Mode Is Visible But Not Actually Fast

Symptoms:

- The UI exposes Fast Mode, but requests do not receive priority behavior.
- A local smoke test returns an answer such as `FAST_CHECK_OK`.

Checks:

- Capture the actual `/v1/responses` request made by Codex Desktop and verify `service_tier=priority` on the wire.
- If the upstream is CPA or another proxy, inspect the proxy-side override rules. Local capture only proves Codex sent the parameter; the proxy can still drop, rewrite, or ignore it.
- In newer Codex builds, inspect `webview\assets\read-service-tier-for-request-*.js`. A shape like `return authMethod===\`chatgpt\` ? featureRequirements?.fast_mode !== false : false` means API-key/local requests are still forced out of Fast Mode.

Action:

- For CPA, add an override rule for the Codex-facing model names and force `service_tier` as a string value of `priority`.
- Patch the Fast Mode gate by removing the `chatgpt`-only branch while preserving the feature-requirement lookup, then rerun wire capture.
- Treat proxy configuration as part of Fast Mode validation, not as optional documentation.

## UI Gate Is Still Blocking A Feature

Symptoms:

- Plugins, Goal commands, Computer Use, or "Any App" / "任意应用" appear disabled even after config changes.
- A Store upgrade moved or renamed webview asset chunks.

Checks:

- Search extracted ASAR webview assets by stable code behavior instead of fixed filenames.
- For Computer Use, relevant patterns include `featureName:\`computer_use\``, Statsig gate `1506311413`, `installPlugin:async`, and `openPluginInstall`.
- If old plugin gate markers such as `533078438` or `pluginDeepLinkAuthBlocked` are gone, inspect `webview\assets\plugins-page-*.js` for `openPluginInstall`, `authMethod:`, and an auth-blocked assignment shaped like `{authMethod:x}=..., y=authBlocked(x),`.

Action:

- Patch the extracted ASAR through the MSIX repack workflow.
- Do not edit `C:\Program Files\WindowsApps` in place.
- Update script search logic when asset filenames drift between Codex Desktop versions.
- For the newer plugin page auth shape, force only the local auth-blocked variable to `false`; do not require the old sidebar, skills-page, and detail-page chunks to exist.

## Browser Use Or Chrome Still Shows Unavailable

Symptoms:

- Chrome or browser use appears installed but Codex Desktop says it is unavailable.
- The plugin list shows `chrome@openai-bundled` as installed/enabled, but browser actions do not appear or do not run.
- Desktop logs contain `browser_use_availability_resolved` with `available=false`, commonly with a reason such as `statsig-disabled`.

Checks:

- Confirm the patch script logged `browser-use gate patch result` as `patched` or `already-patched`.
- Inspect the newest Desktop log under `%LOCALAPPDATA%\Packages\OpenAI.Codex_2p2nqsd0c76g0\LocalCache\Local\Codex\Logs\<year>\<month>\<day>`.
- If the log says `reason=local-patched`, the Desktop availability gate is open; continue by checking the Chrome extension, native host manifest, and plugin cache.
- If the log still says `statsig-disabled`, re-extract the ASAR and inspect targets for `featureName:\`browser_use_external\``, `featureName:\`browser_use\``, `browser-sidebar-availability-*.js`, `browser_use_availability_resolved`, and `.vite\build\main-*.js`.
- Check the native messaging host manifest at `%LOCALAPPDATA%\OpenAI\extension\com.openai.codexextension.json` and the registry key `HKCU\Software\Google\Chrome\NativeMessagingHosts\com.openai.codexextension`.
- Check that `codex plugin list` reports `chrome@openai-bundled` as `installed, enabled`, and that the cached plugin path under `%USERPROFILE%\.codex\plugins\cache\openai-bundled\chrome` exists.

Action:

- Reapply the MSIX patch when `browser_use_availability_resolved` is still `statsig-disabled`.
- Reinstall or repair the Chrome plugin/native host when the log is `local-patched` but the browser smoke test cannot reach Chrome.
- Validate with a real browser smoke test, not just plugin-list output. A good minimal test opens a controlled tab such as `https://example.com/`, asks the extension backend for the active tab, confirms the title `Example Domain`, and then closes the temporary tab.
- Keep the distinction explicit: `local-patched` proves the Desktop gate is open; it does not prove Chrome native messaging or the extension backend is healthy.

## Computer Use Settings Says Plugin Unavailable

Symptoms:

- Computer Control settings shows `Computer Use 插件不可用`.
- Desktop logs contain `computer-use native pipe startup failed` and `missing-helper-path`.
- `codex plugin list` may show bundled plugins missing, disabled, or marketplace load errors.
- The failure comes back after fully quitting Codex Desktop and reopening it.

Checks:

- Inspect `%USERPROFILE%\.codex\.tmp\bundled-marketplaces\openai-bundled\.agents\plugins\marketplace.json`.
- Inspect `%USERPROFILE%\.codex\.tmp\bundled-marketplaces\openai-bundled\plugins\computer-use`.
- Inspect running `extension-host` processes whose paths are under `%USERPROFILE%\.codex\plugins\cache\openai-bundled`.
- Inspect `%USERPROFILE%\.codex\chrome-native-hosts.json`; remove stale entries whose `extensionHostPath` or `browserClientPath` points to a missing file.

Action:

- Stop only those bundled `extension-host` processes when they are locking the bundled marketplace mirror.
- Rerun `scripts\install-computer-use-local.ps1`.
- Restart Codex Desktop.
- Confirm the latest Desktop log ends with `computer-use native pipe startup ready`.
- If `-StrictVerifyOnly` fails because `plugins\cache\openai-bundled\computer-use\latest\.codex-plugin\plugin.json` is missing, run `-VerifyOnly` once to rebuild the cached plugin and `latest` link, then rerun `-StrictVerifyOnly`.

## Computer Use Task Fails Before App Interaction

Symptoms:

- A Computer Use task stops before touching any app or window.
- The visible result says `Computer Use native pipe is unavailable`.
- The plugin or Node REPL error mentions `Package subpath ... is not defined by "exports"`.
- The plugin or Node REPL error mentions `Module not found: @oai/sky`, missing `setupComputerUseRuntime`, or an internal `computer_use_client_base` import failure.
- The failure starts immediately after a Codex Desktop or bundled plugin update.

Checks:

- Inspect the installed package with `Get-AppxPackage -Name OpenAI.Codex | Select-Object Version,SignatureKind,InstallLocation`.
- Check both `app\resources\app.asar` and `app\resources\codex.exe` under the current `InstallLocation`. Do not assume `codex.exe` being a PE file means the ASAR route is gone.
- Inspect `%USERPROFILE%\.codex\plugins\cache\openai-bundled\computer-use\latest\scripts\computer-use-client.mjs`.
- Inspect `%LOCALAPPDATA%\OpenAI\Codex\runtimes\cua_node\*\bin\node_modules\@oai\sky\package.json`, especially the `exports` map. Newer runtime packages may export only `"."`, which breaks deep bare imports from plugin scripts.
- Inspect `%USERPROFILE%\.codex\config.toml` for stale `[mcp_servers.node_repl.env]` entries named `SKY_CUA_NATIVE_PIPE` or `SKY_CUA_NATIVE_PIPE_DIRECTORY`.

Action:

- Run `scripts\install-computer-use-local.ps1 -VerifyOnly` to rebuild the local bundled plugin mirror, stable cache links, CUA runtime overlay, Chrome native host paths, and config cleanup.
- Run `scripts\install-computer-use-local.ps1 -StrictVerifyOnly` immediately after. Treat `client import ok` and `helper transport ok` as the local repair success signal.
- If `-StrictVerifyOnly` fails because a cache link or plugin file is missing, rerun `-VerifyOnly` once, then rerun `-StrictVerifyOnly`.
- In 26.609-style caches, `browser\latest` or `chrome\latest` may be absent while the versioned cache directory still exists. Do not treat that as a Computer Use failure by itself; require the versioned browser/chrome plugin manifests and only validate a support-plugin `latest` junction when it exists.
- If verification succeeds but Desktop still reports native pipe unavailable, fully quit and relaunch Codex Desktop, then inspect the newest Desktop log for `computer-use native pipe startup ready`.
- Only consider a full MSIX repack when Desktop logs or UI evidence show a closed feature gate. Do not patch `resources\codex.exe` or the ASAR just because the immediate failure is an `@oai/sky` package export/import error.

## Sandbox Setup Refresh Fails With OS Error 740

Symptoms:

- Computer Use or node-based helpers fail with `windows sandbox failed: spawn setup refresh`.
- Sandbox logs show `codex-windows-sandbox-setup.exe` failed with OS error 740.

Checks:

- Inspect `%USERPROFILE%\.codex\.sandbox\sandbox.<date>.log`.
- Verify the configured sandbox mode in `%USERPROFILE%\.codex\config.toml`.

Action:

- Set `[windows] sandbox = "unelevated"`.
- Check `codex sandbox --help` before verification.
- If the help lists a `windows` command, verify with `codex sandbox windows "C:\Windows\System32\cmd.exe" /c echo OK`.
- Only builds whose help accepts a direct command form should use `codex sandbox "C:\Windows\System32\cmd.exe" /c echo OK`.

## Self-Update Fails

Symptoms:

- The skill self-update helper cannot reach GitHub, cannot download the archive, or cannot resolve remote HEAD.

Action:

- Do not block the repair.
- Continue with the currently installed local skill.
- Mention that self-update was skipped, then rely on local scripts and local evidence.

## Manual ASAR Extraction Leaves Temp Directory

Symptoms:

- A manual `asar extract` verification succeeds, but deleting the extracted temp tree fails.
- PowerShell reports a missing nested file such as `InfoPlist.strings` while deleting extracted `node_modules`.

Action:

- First verify the target directory is under the intended temp root and has the expected `codex-*` prefix.
- If normal `Remove-Item -Recurse -Force` fails, use .NET deletion with a Windows long-path prefix: `[System.IO.Directory]::Delete("\\?\C:\path\to\temp-dir", $true)`.
- Do not use this cleanup pattern on an unverified or computed path.
