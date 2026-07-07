---
name: codex-ccswitch-mobile
description: Use when configuring or troubleshooting Codex mobile remote control with desktop Codex requests routed through CC Switch sites such as icodeeasy, local OpenAI-compatible proxies, or third-party Responses API relays, especially when checking same-account login and localhost proxy ports.
---

# Codex CC Switch Mobile

## Core Model

Codex mobile remote control has two separate layers:

- Auth layer: mobile visibility and remote binding require the desktop Codex to be logged in with a ChatGPT account.
- Model layer: actual model calls are made by desktop Codex, so they can still route through desktop `config.toml` to CC Switch or another `/v1/responses` relay.

Do not expose CC Switch to the phone. The phone controls desktop Codex; desktop Codex calls `127.0.0.1`.

## Skill Summary

Use this skill to configure and troubleshoot Codex mobile remote control of desktop Codex while preserving the desktop model route through a CC Switch site such as icodeeasy, or another local Responses API proxy. This does not require a Codex Pro membership. The critical split is: both mobile and desktop must use the same ChatGPT account for remote control, while desktop `config.toml` keeps model calls pointed at `http://127.0.0.1:<proxy-port>/v1`.

## When To Use

Use this skill when:

- A user wants Codex mobile to control desktop Codex while model requests use CC Switch.
- A user wants CC Switch to forward Codex requests to custom sites such as icodeeasy.
- Desktop Codex says "logged in with API key" and mobile cannot see the machine.
- Mobile connects but requests do not appear in CC Switch logs.
- A user wants to adapt a third-party Responses API relay for Codex.

Do not use for unrelated OpenAI API application development.

## Activation Requirements

- Desktop Codex is installed and can run normally.
- Mobile Codex is updated to the latest available version and supports remote desktop sessions.
- Desktop Codex and mobile Codex are logged in with the same ChatGPT account.
- Desktop Codex login is ChatGPT auth, not API-key-only auth.
- A local proxy such as CC Switch is running on the desktop.
- The local proxy supports Codex's `wire_api = "responses"` traffic, ultimately forwarding `/v1/responses`.
- The desktop proxy port is known and verified; `15721` is a common CC Switch example, not a universal default.
- Codex Pro is not required for the routing pattern itself; account quota prompts belong to the Auth layer.

## Required State

Desktop `~/.codex/auth.json` should prefer ChatGPT auth:

```json
{
  "auth_mode": "chatgpt",
  "OPENAI_API_KEY": null
}
```

Desktop `~/.codex/config.toml` should keep the model provider on the local CC Switch endpoint:

```toml
model_provider = "custom"
model = "gpt-5.5"
preferred_auth_method = "chatgpt"

[model_providers.custom]
base_url = "http://127.0.0.1:<proxy-port>/v1"
name = "custom"
requires_openai_auth = true
wire_api = "responses"
```

For CC Switch, `<proxy-port>` is often `15721`, but always verify the actual listening port. Adjust `model` to the user's CC Switch provider model. Keep `wire_api = "responses"`; Codex uses `/v1/responses`, not `/v1/chat/completions`.

## Workflow

1. Check desktop login:
   - Run `codex login status`.
   - If it says API key, inspect `~/.codex/auth.json` and `preferred_auth_method`.
   - If changing files, back up `auth.json` and `config.toml` first.

2. Keep the model route local:
   - Confirm `base_url` is `http://127.0.0.1:<proxy-port>/v1` or the user's local proxy.
   - Confirm the proxy is listening, for example `lsof -nP -iTCP:<proxy-port> -sTCP:LISTEN`.
   - Do not replace the desktop local proxy with a phone-reachable URL.

3. Restart desktop Codex:
   - Quit and reopen Codex after auth/config edits.
   - The account menu should no longer show API-key login.

4. Test from phone:
   - Use the same ChatGPT account on mobile.
   - Send a short prompt from mobile.
   - Primary success signal: mobile can control desktop Codex.
   - Routing success signal: CC Switch logs show a new Codex request.

## Verification Commands

Use these commands, redacting secrets in any user-facing output:

```bash
codex login status
lsof -nP -iTCP:<proxy-port> -sTCP:LISTEN
tail -n 80 ~/.cc-switch/logs/cc-switch.log
```

For the common CC Switch port:

```bash
lsof -nP -iTCP:15721 -sTCP:LISTEN
```

Expected CC Switch log pattern:

```text
[Codex] >>> 请求 URL: https://.../v1/responses (model=...)
```

If mobile sends a message and no new CC Switch log appears, the active desktop process is not using the expected `~/.codex/config.toml` or the request is being blocked before the model layer.

## Troubleshooting

- Mobile cannot see desktop: fix Auth layer first. Use ChatGPT login, not API-key login.
- Mobile connects but no CC Switch log: check desktop `base_url`, process restart, and whether another Codex app-server/config is active.
- `127.0.0.1` works broadly for desktop-local proxies; the port does not. Replace `15721` with the actual local proxy port when using non-CC Switch tools or customized CC Switch settings.
- CC Switch gets 404/405: upstream relay likely does not support `/v1/responses`.
- Upgrade prompt appears in mobile: this is usually account/Auth quota, not proof that model calls bypass CC Switch. Check CC Switch logs before changing anything.
- Old sessions disappear after provider changes: this can happen because Codex session visibility is provider/account scoped.

## Safety

- Never print API keys or bearer tokens.
- Back up `~/.codex/auth.json` and `~/.codex/config.toml` before edits.
- Do not expose the local proxy port to the LAN or internet for mobile access.
- Prefer changing Auth layer only when model routing is already correct.
