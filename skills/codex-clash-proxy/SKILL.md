---
name: codex-clash-proxy
description: Start Clash Verge for Codex-only network operations and run download, git clone, dependency install, curl, npm, pip, cargo, go, or similar commands through the local Clash proxy without enabling system proxy or writing persistent user/global Git proxy settings. Use when Codex needs to download software, clone repositories, fetch dependencies, or troubleshoot slow/blocked network access on this Windows machine while the user's normal apps should stay on the direct network.
---

# Codex Clash Proxy

## Overview

Use this skill when a Codex-initiated network command should go through Clash Verge while the user's normal Windows session stays direct. The skill starts Clash Verge if needed, waits for `127.0.0.1:7897`, injects proxy environment variables only for the child command, and avoids persistent system or Git proxy changes.

## Defaults

- Clash Verge executable: `C:\software\Clash Verge\clash-verge.exe`
- Local mixed proxy: `http://127.0.0.1:7897`
- Optional Clash controller: `http://127.0.0.1:9097`
- System proxy must remain off.
- Do not set user-level `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, or global Git `http.proxy` / `https.proxy`.

## Standard Workflow

1. Prefer the wrapper script for downloads, dependency installs, and Git operations:

```powershell
& "C:\Users\84365\.codex\skills\codex-clash-proxy\scripts\run-with-clash-proxy.ps1" -CommandLine "<command> <args>"
```

2. Use `-PreferAutoGroup` when the task may need Clash to switch away from `DIRECT`. This attempts to select the first available automatic/url-test style group through the local controller, if the controller is available.

```powershell
& "C:\Users\84365\.codex\skills\codex-clash-proxy\scripts\run-with-clash-proxy.ps1" -PreferAutoGroup -CommandLine "git clone https://github.com/example/repo.git"
```

3. For Git, still use the wrapper. It injects per-process Git config through environment variables without modifying global Git config.

4. If the wrapper cannot reach `127.0.0.1:7897`, inspect whether Clash Verge failed to start or whether its mixed port changed. Do not fall back to persistent global proxy settings unless the user explicitly asks.

## Node Selection

Let Clash Verge handle node testing and selection. If `-PreferAutoGroup` succeeds, it changes selector groups that are currently on `DIRECT` to an available `url-test`, `fallback`, or `load-balance` group. If the controller is unavailable, continue with the current Clash selection and report that automatic group switching was skipped.

Avoid editing subscription files, node credentials, or remote profile URLs. Do not print secrets from Clash config.

## Examples

Clone through Clash only for this command:

```powershell
& "C:\Users\84365\.codex\skills\codex-clash-proxy\scripts\run-with-clash-proxy.ps1" -PreferAutoGroup -CommandLine "git clone https://github.com/owner/repo.git"
```

Download a file:

```powershell
& "C:\Users\84365\.codex\skills\codex-clash-proxy\scripts\run-with-clash-proxy.ps1" -CommandLine "curl.exe -L -o tool.zip https://example.com/tool.zip"
```

Install Python dependencies:

```powershell
& "C:\Users\84365\.codex\skills\codex-clash-proxy\scripts\run-with-clash-proxy.ps1" -CommandLine "python -m pip install -r requirements.txt"
```

Only start Clash and verify the local proxy port:

```powershell
& "C:\Users\84365\.codex\skills\codex-clash-proxy\scripts\run-with-clash-proxy.ps1"
```
