# Ordered Commit Integration

Use for an explicit ordered integration, with a clean worktree, confirmed start point, new branch name, and commit order. Reuse authorization already supplied for the exact branch creation/switch and commits.

1. When the start point, branch creation/switch, and commit order are already authorized, run --apply directly; it validates the same inputs. Run without --apply when the user wants a plan or the scope still needs a concrete preview.
2. The helper makes a timestamped backup branch from original HEAD, creates the integration branch, and cherry-picks in the supplied order.
3. The helper returns at a conflict with completed commits, failed commit, paths, and a Git-directory codex-integration-state.json. The agent may resolve clear mechanical conflicts within the authorized port. Pause for functional choices, ambiguous target behavior, or an explicit user instruction such as 冲突就停. Do not silently skip, reorder, or abort commits.
4. To continue a mechanical resolution, confirm the current branch and CHERRY_PICK_HEAD match the saved new_branch and failed_commit. Stage only the resolved paths, run git cherry-pick --continue, then apply only the commits after failed_commit in the saved order. Record each completed step in the same state receipt; stop at any new unresolved issue. Do not rerun --apply, which creates a new branch. A failed command without an active cherry-pick requires diagnosing its actual error before choosing recovery.
5. Compare the integrated range and perform target verification. Return the same compact port receipt as semantic porting.

```powershell
python "$env:USERPROFILE\.codex\skills\asr3601-cross-branch-porting\scripts\ordered_cherry_pick.py" `
  --repo . --start-point <start> --new-branch <branch> --commits <ordered-shas>
```

Add --apply only for the authorized mutation. A dry run is the helper's concrete plan, not a demand for duplicate approval. Do not fetch or synchronize a remote when the request excludes synchronization.
