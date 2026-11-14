# Current Request Scope

Use the newest request together with still-applicable prior authorization. Keep
one compact scope statement in the task: selected target/Bugs, local changes,
commit/push, release/upload stages, and single-step versus continuous work. This
is a handoff aid, not a new state store or a natural-language parsing engine.

Before the next irreversible or external stage, ensure its owner receives the
current scope. Do not ask again for actions already clearly authorized. A changed
request removes unperformed steps; it cannot undo already performed actions.

| Request sequence | Current action scope |
|---|---|
| 提交出版本 → 仅提交然后同步 | Commit/push the selected changes; withdraw pending release and resolution if excluded by 仅提交 |
| 不同步，只提交，然后出版本 | Local commit, then the release owner's explicit no-sync mode; do not reintroduce push |
| 不提交，出版本 | The formal owner's documented no-commit route and gates; do not force a delivery-state commit |
| 修复并提交，然后查下一个 | Complete this Bug's requested stages; investigate the next one |
| 一直修复并提交，然后查下一个 | Continue the ordered authorized loop until exhausted or narrowed |
| FOTA 仅本地 | Pass the FOTA owner's local-only settings, including GitMode None and no external upload |
| FOTA 只上传差分 | Use the recorded pair/service route and differential-only owner path; no new build, version, fnOS upload, or Git action |

For ordinary new single-Bug composites, the calling agent sequences the relevant
owners directly; no delivery state is required. Existing delivery states remain
usable as evidence, including legacy single-Bug states. After a scope change,
use [delivery-state narrowing](delivery-state.md) for persisted pending release,
resolution, or whole-plan continuation. Explicit scope changes are recorded in the
same file, preserving original stage evidence and completed actions.

If the current request drops per-Bug commits or changes which Bugs may be worked
on, stop that recorded plan's continuation and use the retained receipts for the
new narrower task. Do not fabricate commits, verification, memory notes, or remote
resolution merely to satisfy the old stage chain. A later explicit continuation
request can resume the retained scope, but it does not revive withdrawn actions.

Git mode and upload are independent in the FOTA owner. Omitting an upload flag
alone does not disable Git sync. Resolve parameters through the existing owner;
do not add a second release preflight or post-success verification. Quick Release
retains its one-controller call and stop-on-failure behavior.

FOTA upload resume preserves the original manifest's Git mode and completed
actions. If the newer scope is incompatible with that entrypoint, use the existing
server-only/differential-only path that expresses the actual request, or report
the specific unsupported remainder. Do not alter the old manifest to invent a
different authorization history or execute its withdrawn stages.
