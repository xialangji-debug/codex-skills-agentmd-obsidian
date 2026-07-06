# Zentao Resolve Plan Format

Use a plan when resolving multiple bugs or when any bug is not a plain code fix.

## Markdown Format

```markdown
# Zentao Resolve Plan

## Bug #1234 Bug title
resolution: fixed
resolvedBuild: trunk
assignTo: self
comment:

## Bug #1235 Another bug title
resolution: external
resolvedBuild:
assignTo: self
comment:
平台返回数据与协议字段不一致，设备端日志显示已经按协议上报，需平台侧修复解析。
```

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
      "resolvedBuild": "trunk",
      "assignTo": "self",
      "comment": ""
    }
  ]
}
```

## Required Remarks

- `fixed`: comment may be empty.
- `external`: comment is required and must explain the platform/external evidence.
- Other non-fixed solutions: add a remark unless the user explicitly says no remark.
