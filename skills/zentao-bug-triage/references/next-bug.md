# Next Bug In The Current Session

Use the current session's list snapshot, candidate receipts, and outcomes. Keep
only a small in-task table: ID/title, 未检查 / 正在处理 / 本会话已完成 / 本轮跳过,
reason, and relevant current-target receipt. Do not create a persistent repair
state for a read-only navigation request or share a cursor between chats.

## Select One Candidate

1. Bind progress to repository path, branch, firmware/product identity, list
   snapshot, and expected HEAD. Reuse the task's current identity. A known commit
   from this task updates expected HEAD; an unexpected HEAD, branch/product
   change, or reactivation invalidates affected old conclusions. Preserve prior
   evidence as history and refresh only what is now stale.
2. Follow the user's requested order/filter. Otherwise preserve snapshot order.
   Never infer priority solely from a similar fix in memory. First resolve the
   current item's local navigation outcome: a completed query can be 本会话已完成
   with result 存在/当前已修/未确认; this does not imply a code fix or remote closure.
   An explicit “skip” records the reason and leaves the Zentao Bug unchanged.
3. Select the next eligible 未检查 item, excluding this round's completed/skipped
   items. If a genuinely unfinished authorized fix is active, retain its evidence
   and state the remaining stage; a navigation request does not complete it or
   authorize finishing it. Explicitly changing the selected ID makes that ID active.
4. Reuse current detail/attachments or fetch only this selected ID through the
   normal Selected path. Inspect its latest status/reactivation before diagnosing.
   Apply the existing repair-candidate assessment, then return one diagnosis.
5. For `下一个没修复的`, skip 已修 only when current-target source or an unchanged,
   exact-target receipt establishes it. A historical fix note, source-branch commit,
   or candidate match alone is insufficient. If the checked candidate is already
   fixed, record the evidence and continue selecting until an unresolved candidate
   is found or the list is exhausted; keep the skipped evidence compact.
6. Fetch a fresh list only when no usable list exists, the identity is stale,
   the user requests refresh, or the list is exhausted. At exhaustion refresh once;
   reconcile IDs and carry over still-valid same-session outcomes, so the same
   active-but-locally-processed Bugs do not form an endless loop. If no new eligible
   item remains, report this round complete and identify skipped/uncertain items.
   A requested retry, new reactivation, or changed source reopens the affected item.

Do not silently discard an unresolved item because the current list omits it;
list omission is not a remote status change. An unfamiliar/restarted session with
no reliable receipt starts from the current list instead of guessing an old cursor.

## Scope Of The User's Words

| Request | Authorized next action |
|---|---|
| 查下一个 / 下一个没修复的 | Query and diagnose the next eligible Bug |
| 跳过，查下一个 | Mark local skip, then query the next Bug |
| 修复并提交，然后查下一个 | Finish requested stages for the current Bug, then query the next |
| 一直修复并提交，然后查下一个 | Ordered repair/commit loop through the applicable multi-Bug owner |

Reuse previous explicit continuous-work authorization unless the user narrows or
ends it; “next” alone does not add such authorization. Existing ordered deliveries
reuse their owner's state/receipts and expected HEAD. Do not invent a commit to
satisfy a read-only cursor or advance the delivery's stage from navigation alone.

## Reply

Identify the selected Bug as `<ID> <完整标题>`, give its diagnosis and repair
candidate result, then one short progress line with completed/skipped/remaining
counts and skip reasons where useful. Counts describe the current snapshot and
session, not total historical fixes. A locally completed query remains distinct
from a verified fix, 已解决, and QA 已关闭.
