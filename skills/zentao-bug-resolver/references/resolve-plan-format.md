# Zentao Resolve Plan Format

Use a plan when resolving multiple bugs or when any bug is not a plain code fix.

## Markdown Format

```markdown
# Zentao Resolve Plan

## Bug #1234 Bug title
resolution: fixed
resolvedBuild: trunk

## Bug #1235 Another bug title
resolution: external
resolvedBuild:
comment:
平台返回数据与协议字段不一致，设备端日志显示已经按协议上报，需平台侧修复解析。
```

`comment` supports both `comment: 单行备注` and the multiline form shown above. When a non-empty comment cannot be written into the Zentao form, the resolver must fail instead of submitting an empty remark.

For current branch firmware fixes, use the alias instead of copying the branch name by hand:

```markdown
resolvedBuild: current-branch
```

The resolver expands `current-branch`, `branch`, `当前分支`, or `当前版本` to `git branch --show-current`.

Supported key names:

- `resolution`, `解决方案`
- `resolvedBuild`, `build`, `解决版本`
- `assignTo`, `assignedTo`, `指派给`
- `comment`, `备注`

Supported resolution values:

- `fixed` or `已解决`
- `external` or `外部原因`
- `bydesign` or `设计如此`
- `duplicate` or `重复Bug`
- `notrepro` or `无法重现`
- `postponed` or `延期处理`
- `willnotfix` or `不予解决`

## JSON Format

```json
{
  "bugs": [
    {
      "id": "2957",
      "title": "录音过程中收到的微聊消息不会弹出未读弹窗",
      "resolution": "fixed",
      "resolvedBuild": "trunk"
    }
  ]
}
```

## Required Remarks

- `fixed`: comment may be empty.
- `assignTo` is optional. When omitted, the current assignee is preserved.
- `external`: comment is required and must explain the platform/external evidence.
- Other non-fixed solutions: add a remark unless the user explicitly says no remark.

## Development Closeout Rules

- Development-side workflow ends at `已解决`.
- Do not click `关闭`; QA/test closes after verification.
- If a fixed bug is already `已关闭` because it was closed by mistake, run the resolver with `--activate-closed --submit` so it activates the bug first, then resolves it as `已解决`.
- After submit, the expected final status is `已解决`; treat any other status as a failed operation that needs manual inspection.
