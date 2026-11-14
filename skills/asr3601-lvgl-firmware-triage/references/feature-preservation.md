# Feature Preservation After Ports And Reductions

Apply to authorized ports, feature cuts, storage reductions, and single-Flash
conversions. Reuse the current target identity and fix receipt. Limit this check
to changed features and their dependencies; ordinary one-Bug edits do not trigger
a project-wide feature audit.

## Before Editing

From the user's current requirements and live target code, identify the behavior
to preserve/change/remove. A single-feature port can use a short paragraph. For
multi-feature reductions or single-Flash conversions, use a compact table such as:

| Feature / behavior | Current target | Intended result | Required paths |
|---|---|---|---|
| Camera capture | Current source evidence | Preserve | Entry, init, capture callback |
| Cloud photo upload | Current source evidence | Preserve | Capture result, protocol, upload |
| Local photo persistence | Current source evidence | Remove if requested | Storage writes, local album |

These rows are examples, not a default product requirement. Use preserve/change/
remove for the actual task. Group related source fixes by user-visible behavior.
Derive clear scope from existing instructions; ask only when an unresolved choice
would materially change behavior. Removing local storage does not imply disabling
the camera, cloud upload, or every use of the same filesystem.

## Evidence And Comparison

1. Record relevant source and target behavior before editing, with branch/commit
   and related dirty changes. Reuse already-read evidence. For a broad feature
   reduction, use `scripts/audit_feature_closure.py` with narrow feature aliases
   and guards before and after, using the same arguments. The invocation is in
   [feature closure](advanced-modes.md). Store reports, if needed, under
   `.codex-project/validation/<task>/`; do not add validation files to firmware commits.
2. Inspect the touched macro/build selection, menu/UI entry, initialization/task,
   protocol/sender, resource registration, and storage paths. Inspect only relevant
   surfaces; omit unrelated categories. For storage changes,
   trace callers through success, failure, cleanup, and reboot behavior where relevant.
3. Reuse the scanner's hits as navigation. It does not evaluate the preprocessor,
   resolve all aliases, or prove runtime reachability. `#define FEATURE 0`, an
   inactive variant, a stub, or a same-named function cannot establish retention.
   Check the actual target guard values, call path, and build inputs. The scanner's
   surfaces do not cover every resource/storage dependency; inspect those directly.
4. Compare each requirement to the final diff. Use 完整覆盖, 部分覆盖, 有意排除,
   or 证据不足, with a concrete path/call/guard and the remaining gap. 有意排除
   requires a user-approved exclusion or a demonstrated target incompatibility
   already handled within the agreed scope; never relabel a missed requirement.
5. Keep coverage separate from verification: 完整覆盖 may mean source paths are
   accounted for, with build/device acceptance still pending. Reuse the owning
   build/release receipt; immediate FOTA pairs supply both full builds.

If a required preserved feature disappeared, correct it within the authorized
change or report it as incomplete. Do not claim the port is complete merely
because all source commits were applied.

## Completion Receipt

Carry the relevant behavior differences, decisive evidence, and missing validation
in the existing fix/port receipt and canonical exact-target record. Use prose for
a small single-feature change and a compact table for multi-feature reductions or
single-Flash conversions; do not start a second closeout workflow.
If the change has already been made without a baseline report, reconstruct the
baseline from known diffs/source receipts and label any unavailable evidence.
