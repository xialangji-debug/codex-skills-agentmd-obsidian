---
name: zentao-bug-resolver
description: Resolve explicitly selected Zentao Bugs after firmware fixes or triage decisions are complete. Use for 标记已解决, 关禅道, 外部原因, resolve-plan review, or corrective reactivation of an accidentally resolved/closed Bug. Directly submit ordinary fixed Bugs when the current request already authorizes the exact IDs and current exact-product fix receipts exist; otherwise preview once.
---

# Zentao Bug Resolver

This Skill owns development-side Zentao resolution only. `已解决` remains QA
pending; never close a Bug for QA/test.

## Choose One Path

| Current request/evidence | Path |
|---|---|
| Exact IDs explicitly authorized, every item is ordinary `fixed`, and each has a current exact-product fix receipt | Direct minimal submit |
| User asks for a plan, authorization is absent, fields differ, any item is external/other, or evidence is incomplete | Preview once, then submit after approval |
| Accidental close, wrong-product resolution, or reactivation | Read [corrective operations](references/corrective-operations.md) |

Do not run preview and submit as two automatic rounds after the current request
already satisfies the direct-submit row.

## Direct Minimal Submit

1. Reuse the current fix receipt and task snapshot. Let the resolver check the live checkout and mapping required for submission.
2. Confirm the exact Bug IDs and current fix receipts.
3. Call the resolver once:

```powershell
node "$env:USERPROFILE\.codex\skills\zentao-bug-resolver\scripts\zentao_bug_resolver.js" --repo . --ids 2799,2917 --minimal --submit
```

`--minimal` selects `fixed`, preserves the assignee, leaves the comment empty,
and defaults the resolved build to `trunk`. Use `--build-current-branch` only when
the requested resolved build is the current branch. The script still verifies product, current status, resolved build,
form values, submission, and the final `已解决` detail page.

## Preview Path

Create a plan only when the selected Bugs require different values or a non-fixed
decision. Read [resolve plan format](references/resolve-plan-format.md), then run:

```powershell
node "$env:USERPROFILE\.codex\skills\zentao-bug-resolver\scripts\zentao_bug_resolver.js" --repo . --plan ".codex\zentao-resolve-plan.md"
```

After the user approves that preview, rerun the same plan with `--submit`. Do not
ask for a second approval already supplied in the current request.

Use `fixed` only for a current code-side fix or evidence that the issue is already
fixed in the named build. Use `external` only when concrete evidence assigns the
failure to platform/backend/data/account/network/applet/test environment; include
a concise required remark. Do not infer either choice from a title.

## Hard Boundaries

- Resolve only explicitly selected IDs or IDs in an approved plan; never resolve
  the full fetched list.
- Require detail-page `所属产品` to exactly match the confirmed `禅道产品` in
  `.codex-project/variant.md`. Missing, ambiguous, unconfirmed, or branch-mismatched
  mappings stop before browser access. Legacy `zentao.md` mappings are supported
  only when variant.md is absent. An explicit product cannot override a conflicting
  current mapping; prefix similarity is not enough.
- `--allow-product-mismatch` is only for explicitly authorized corrective
  reactivation with `--reactivate-resolved`, never ordinary resolution.
- Preserve the current assignee unless the user explicitly changes it.
- Do not resolve `ignored-items.md` entries unless the user moves them into scope.
- Use the latest activation note for a reactivated Bug.
- Preserve unrelated local changes.
- Load credentials only from the existing private Zentao credential source. Never
  print or store passwords, service URLs, or tokens in reports or memory.

After a successful fixed submit, accept the script's exact-target
`zentao_resolved` memory event; it must not upgrade QA verification. Report IDs
actually submitted, final statuses, failures, resolved-build fallback, and memory
event count. An unmatched memory event stays unmatched; never link by title.

## Resource

`scripts/zentao_bug_resolver.js` performs all product/status/build/form/final-page
checks and writes the operation report. Do not duplicate those checks outside the
script.
