# Corrective Zentao Operations

Load this reference only for accidental close/resolution or explicit reactivation.

## Accidentally closed fixed Bug

Use an approved plan with `--activate-closed --submit`. The script must activate
the closed Bug with a development-process note, submit the resolve form, reopen
the detail page, and require final status `已解决`.

```powershell
node "$env:USERPROFILE\.codex\skills\zentao-bug-resolver\scripts\zentao_bug_resolver.js" --repo . --plan ".codex\zentao-resolve-plan.md" --build-current-branch --activate-closed --submit
```

## Wrong-product Bug accidentally resolved

Preview `--reactivate-resolved` first because this is a corrective cross-product
write. Submit only after the correction is reviewed.

```powershell
node "$env:USERPROFILE\.codex\skills\zentao-bug-resolver\scripts\zentao_bug_resolver.js" --repo . --ids 3310,3304 --reactivate-resolved --allow-product-mismatch
node "$env:USERPROFILE\.codex\skills\zentao-bug-resolver\scripts\zentao_bug_resolver.js" --repo . --ids 3310,3304 --reactivate-resolved --allow-product-mismatch --submit
```

`--reactivate-resolved` accepts only source status `已解决` and restores it to
`激活`; it never runs a resolve form. `--allow-product-mismatch` is permitted only
for this explicit corrective path, never for an ordinary resolution.

Do not silently skip, close again, or continue with a second remote operation
after a corrective step fails.
