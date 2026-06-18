# Project Patterns

Load this reference only for ASR3601/LVGL children-watch firmware tasks that match recurring local patterns.

## Recurring Bug Types

### Calculator Branch Porting

Use this frame for requests like “把这个分支的计算器移植到当前分支”:

```text
现象：source branch works, target branch lacks or breaks calculator behavior
可能模块：calculator page/app, menu entry, resources, build macros, variant-specific files
验证点：source vs target diff, file ownership, watch/phone/sport guards, resource IDs, compile targets
修复路径：port minimal files/functions/resources, add missing menu/registration only if target lacks it, preserve excluded variants
```

Checklist:

- Identify source branch and target branch before editing.
- Compare calculator-related files, resource IDs, menu entries, app registration, and compile macros.
- If the user says “不动运动版”, verify sport-specific paths are untouched or guarded.
- Avoid copying unrelated framework, menu, or resource churn from the source branch.

### Low Battery, SIM Removal, Power UI

Check state priority before changing UI:

1. shutdown or power key dialog
2. low battery / power-save mode
3. SIM removal reminder
4. secondary prompts and toasts

Look for state flags, popup guards, event handlers, and duplicate refresh paths. The usual risk is fixing one trigger path while another timer or callback still shows the old prompt.

Use this fixed frame:

```text
现象：low battery/power-save screen overlaps with SIM removal or another reminder
可能模块：power state manager, SIM event handler, popup manager, LVGL page refresh, timers/callbacks
验证点：state priority, popup guard, event order, repeated timer refresh, resume/wakeup path
修复路径：block lower-priority SIM/reminder UI while low-power/shutdown UI is active, then verify every callback path
```

Do not stop after finding only the direct button/event handler. Search for timer, wakeup, network, and UI refresh callbacks that can reopen the reminder.

### Location Scheduling

For “power-save mode has no location record for more than 30 minutes”:

- Find the location plan scheduler and power-save branch.
- Check timer interval, wake/sleep conditions, retry logic, and upload success/failure paths.
- Distinguish “no fix attempt”, “fix succeeded but upload failed”, and “record hidden in UI”.

### Friend Add, IMEI, Protocol Display

For friend and IMEI issues:

- Check protocol documentation or PDFs when provided.
- Trace field parse -> storage -> UI list/detail display -> delete-friend page.
- Check whether both devices receive or display success acknowledgments.
- Avoid assuming IMEI is available unless the protocol or local model stores it.

### LVGL Text and Layout

For multilingual overflow or special display such as `O2`:

- Inspect font support, rich-text/subscript support, label long mode, width constraints, and text preprocessing.
- For long translated strings, prefer scroll/long mode plus explicit width constraints over hardcoded truncation.
- Reuse existing project font and label helpers.

### Pixel-Level UI Offset Fixes

Use this frame for requests like “这一行向右移动 6 个像素” or “看截图这个控件多大”:

```text
现象：one visible LVGL element is misaligned or has the wrong size/position
可能模块：page create function, label/image style, container layout, update/refresh path, resource size
验证点：screen resolution, parent container coordinates, current x/y/w/h, language-dependent width, variant guards
修复路径：apply the smallest local coordinate/style change, then verify create and refresh paths keep the same result
```

Checklist:

- Locate the page/control from visible text, resource IDs, or nearby labels.
- Inspect both initial creation and later refresh/update functions.
- Prefer changing the specific object position/style over global container layout.
- Re-check long Chinese/translated text if moving a label can cause clipping.
- State whether the fix is watch-only, phone-only, sport-only, or shared.

### Screenshot-Driven UI Triage

Use this when the user attaches an image/video and asks whether a problem exists, what size something is, or where to change it:

```text
现象：visible screenshot/video mismatch
可能模块：page/screen from visible text, LVGL object tree, image/font resources, status-driven update path
验证点：visible strings, icon names, coordinates, screen resolution, active state, matching resource file
修复路径：search stable visual clues first, then trace create -> update -> resource/style before editing
```

Process:

- Extract visible text, icon/resource appearance, approximate coordinates, and active UI state from the screenshot.
- Search text keys, image/resource names, and nearby page names before broad function searches.
- If measuring pixels, state whether it is measured from screenshot pixels, configured LVGL resolution, or source constants.
- Treat screenshots as evidence, not proof of the code path; confirm the path in source before changing code.

### Screen Size, Wallpaper, Resources

For new project/screen size questions:

- Find configured horizontal/vertical resolution first.
- Then inspect wallpaper/image resource dimensions and scaling rules.
- Report whether mismatch is harmless, cropped, stretched, or requires new assets.

### Branch Porting

For “move this working feature from another branch”:

- Compare source and target branches before editing.
- Identify variant-specific compile flags and resource directories.
- Port minimal files/functions.
- Re-check excluded variants such as sport watch when the user names them.

## Preferred Evidence

Use these before editing when available:

- `AGENTS.md`
- screenshots or videos
- user-provided logs
- protocol PDFs or requirement docs
- existing UI text/resource files
- build scripts and make targets
- codegraph context for call chains

## Final Answer Shape

For Chinese bug work, use this concise structure:

```text
存在/未确认：
原因：
修复路径/修改：
影响：
验证：
风险：
```

If the user asked only for analysis, stop after feasibility and proposed fix. If they asked to fix or approved the approach, implement and verify.
