# Zentao Bug Classification Rules

Use these rules for the first-pass triage table. They are intentionally conservative: do not promise a fix before checking the current branch.

## Categories

### UI Bug

Typical clues:

- 界面, 显示, 图标, 导航栏, 按钮, 页面, 弹窗, 文案, 字体, 布局, am/pm, 12小时制, 闹钟图标, 灰色, 截图
- User-visible LVGL behavior where no protocol/log evidence is required.
- Long text display issues such as 显示不全, 滚动, 字体/宽度/layout problems.
- Clear wording/layout requests such as `绑定向导` text replacements, `请绑定APP` -> `请绑定小程序`, `手表` -> `设备`, `3C认证信息/扰码` display format, lock-screen UI, and first-level menu order.

Default handling:

- Codex can usually inspect and propose/fix after confirming the current branch path.
- Logs usually not required unless the UI state is event-driven.

### App Or Protocol Layer

Typical clues:

- APP, 小程序, 协议, 指令, 上报, 下发, 短信, 微聊, 联系人, 白名单, SOS, 防欺凌, BULLYEVENT, 定位, 云相册, 消息, IMEI, 远程
- Behavior depends on local app state, watch protocol parsing, network message routing, or feature logic.
- Contact/whitelist count limits such as “最多显示16个”, “白名单25个”, or “亲情号至少5个” should be treated as app/protocol/storage/UI-boundary issues that Codex can inspect first.
- “重启后配置不生效” is app/protocol/NVM unless the detail includes crash, assert, reboot loop, power failure, or driver evidence.
- Factory/engineering-mode feature gaps such as 老化模式, 自动老化, LCD, 喇叭, 麦克, 马达/振动, 工模测试 can be inspected first when a video, screenshot, or explicit expected sequence is provided.
- Pedometer/factory step-test issues such as 计步, 步伐, 步伐无数据 should be inspected when a log or screenshot is attached.
- Class-mode/DND priority conflicts should be treated as app/protocol priority logic first unless backend request/response evidence proves it is platform-only.

Default handling:

- Codex can usually inspect and propose/fix after checking protocol files, local storage, and message status.
- Logs may be needed for protocol payload, server response, or timing issues.
- Logs are not always required for pure count-limit or obvious local storage boundary issues; mark those as `可以先查`.

### Low-Level / Hardware / Driver

Typical clues:

- 底电流, PMIC, LDO, SIM REMOVED, SDIO, modem, camera sensor, MCLK, 电源, 充电电流, 睡眠功耗, 死机, crash, assert, dump, 驱动, 平台芯片

Default handling:

- Do not directly fix. Give a debug plan, required logs, schematic/hardware evidence, and likely owner.
- Ask for CATStudio logs, power measurement, crash dump, hardware revision, or schematic when needed.

### Platform / Backend

Typical clues:

- 后台, 平台, 服务器, 接口, 云端, 管理端, 账号, 登录, 权限, 数据同步, API返回, 数据库

Default handling:

- Do not directly fix firmware unless there is evidence the device request is wrong.
- Ask for backend API logs, request/response payload, account/project configuration, or platform owner confirmation.

### Unclear / Needs Repro

Typical clues:

- Title is too short, no clear steps, missing device state, or cannot tell whether bug belongs to product/branch.

Default handling:

- Ask for repro steps, screenshots, logs, branch/product confirmation, and expected behavior.

## Difficulty

- `低`: local UI text/layout/state guard, clear repro, likely one module.
- `中`: app/protocol logic, multiple callbacks/timers, branch-specific behavior, or needs log confirmation.
- `高`: low-level power/modem/camera/driver, crash, platform interaction, unclear ownership, or requires hardware measurement.

## Can Codex Handle

- `可以先查`: UI/app/protocol issue with enough repro information.
- `待判断/可查`: automatic classification is uncertain, but the bug has a clear expected result or attachments, so keep it in the user-selectable work list instead of hiding it.
- `需要日志后再查`: protocol, crash, timing, network, SIM, power, or camera issue where logs decide the path.
- `不直接处理-底层`: low-level/hardware/driver; provide debug advice instead.
- `不直接处理-平台`: backend/platform/config; ask platform owner or API evidence.
- `需确认项目`: product/project/branch mapping ambiguous.

## Handling Queue

- `work-items.md`: include `可以先查` bugs, `待判断/可查` bugs, and `需要日志后再查` bugs when the detail page already provides relevant logs/videos/images.
- `ignored-items.md`: include `不直接处理-底层`, `不直接处理-平台`, unclear-without-expectation/evidence, closed/resolved, and log-needed bugs without evidence.
- List-only work items may be shown in `work-items.md`, but code edits must wait until that bug is deep-fetched with `--ids`.

## Reactivated Bugs

- If the detail history shows a solved bug was activated again, treat the latest activation note as the current problem statement.
- Include activation count, activation time, actor, version/build text, result, expected behavior, and activation attachments in `work-items.md`.
- Compare code history against the latest activation time. A commit before activation is not enough proof of fix when the tester says it still reproduces.
- When the activation note says a specific build was not fixed, report that build/version explicitly before code analysis.

## Report Table Columns

Use these columns unless the user asks otherwise:

| ID | 标题 | 类型 | 处理建议 | 附件 | 我能否先修 |
| --- | --- | --- | --- | --- | --- |

Use `triage.md` for the full wide table with product, severity, dates, activation, and detailed reasons. Chat replies should default to the compact table above.
