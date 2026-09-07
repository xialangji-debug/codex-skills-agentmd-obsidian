# Ordered Commit Integration

Use for an explicit ordered integration, with a clean worktree, confirmed start point, new branch name, and commit order. Reuse authorization already supplied for the exact branch creation/switch and commits.

1. Run the helper without --apply to validate the commit list and show the concrete plan.
2. Within the authorized scope, run --apply. It makes a timestamped backup branch from original HEAD, creates the integration branch from the start point, and cherry-picks in the supplied order.
3. Stop at the first conflict. Report completed commits, failed commit, and conflicted paths. Do not resolve, skip, abort, reorder, or continue until the user chooses that recovery.
4. Compare the integrated range and perform target verification. Return the same compact port receipt as semantic porting.

```powershell
python "$env:USERPROFILE\.codex\skills\asr3601-cross-branch-porting\scripts\ordered_cherry_pick.py" `
  --repo . --start-point <start> --new-branch <branch> --commits <ordered-shas>
```

Add --apply only for the authorized mutation. A dry run is the helper's concrete plan, not a demand for duplicate approval. Do not fetch or synchronize a remote when the request excludes synchronization.
