---
name: aa-skill-router
description: Route ambiguous, cross-project, or Codex control-plane engineering requests only when the active project's AGENTS.md and .codex-project/index.md do not already provide the route. Use for missing project context, conflicting multi-project scope, project onboarding, skill registry cleanup, trigger failures, or index synchronization. If the project index covers the request, follow it and stop; do not classify ASR versus ESP32 again.
---

# Skill Router

Use this skill only as a fallback. It selects an owner; it does not perform the specialist workflow.

## Project-First Gate

1. Read the current repository `AGENTS.md` and `.codex-project/index.md` when present.
2. If the local index covers the request, use that route and stop routing. Do not inspect `variant.md` merely to decide whether the project is ASR or ESP32.
3. Read `.codex-project/variant.md` only when the selected operation depends on dynamic target identity.
4. If the request spans repositories or the local evidence conflicts, resolve the exact target before any edit, branch action, device action, release, or external write.

## Fallback Routing

Use the smallest applicable fallback:

| Situation | Destination |
|---|---|
| Project context is missing or stale | Project-specific onboarding; for ASR360x use `asr3601-project-onboard` |
| Skill routing is still unclear | Read only the matching domain entry from `%USERPROFILE%\.codex\skills-index\index.md` |
| Cross-project or cross-branch change | The owning porting/integration skill; for ASR360x use `asr3601-cross-branch-porting` |
| Skill cleanup, trigger failure, or index synchronization | `skill-usage-tracker` and its read-only `registry-audit` first |
| Explicit local-model implementation | `local-coder-executor`, only after its authorization and allowlist gates |
| Ordinary explanation outside a specialist workflow | Normal assistant behavior in the active project |

## Boundaries

- Generic words such as `bug`, `日志`, `编译`, or `发布` do not override the active project's local route.
- Code explanations and commit-grouping plans remain read-only unless the user authorizes changes.
- Do not turn a local build into flashing, a flash into log capture, or a package into release publication without explicit scope.
- Do not treat development-side Zentao resolution as QA closure.
- Keep specialist details in the specialist skill instead of copying them here.
