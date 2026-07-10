# Zentao Project Map

Use this file to map local firmware branches and version tokens to Zentao product/project names. Prefer exact confirmed mappings. If only an unconfirmed candidate matches, ask the user before fetching project-specific bugs.
When a Zentao project ID is known, add `project_id` so the fetch script can avoid fragile project-name discovery.
When a Zentao product ID is known from a `bug-browse-<id>` URL, add `product_id`; do not store product IDs as `project_id`.

## Confirmed Exact Branch Mappings

These entries can be used automatically when the current branch name or `yl_device_ver` matches.

```yaml
- branch_contains:
    - TW38_LT49_3603主板20260601
  yl_device_ver_contains:
    - LT49_ZX_ASR3603_TW38
  zentao_names:
    - TW38-阿科奇-LT49（越南）
  verified: 2026-07-10
  note: User screenshot and bug details 2936/2935/2934/2932/2931/2930/2913/2868/2867/2866/2861/2850/2848 confirmed the product mapping; project id not live-verified yet.

- branch_contains:
    - TW18_LT52_3602_APP公版腕表20260707
  yl_device_ver_contains:
    - LT52_ZX_ASR3602_TW18
  zentao_names:
    - TW18_阿科奇_LT52_APP公版
    - TW18_阿科奇_LT52_APP
  project_id: 90
  product_id: 42
  verified: 2026-07-07
  note: User screenshot-confirmed product mapping; project id live-verified from `project-index-90.html`; product URL `bug-browse-42-all-.html`.

- branch_contains:
    - TW18_LT52_3602_电信乐智协议腕表20260610
  yl_device_ver_contains:
    - LT52_LZ_ASR3602_TW18
  zentao_names:
    - TW18_阿科奇_LT52_乐智
  project_id: 164
  verified: 2026-07-07
  note: Current c10lezhi family; exact branch/version match; project id live-verified.

- branch_contains:
    - TW10_3602_有屏电信乐智协议20260523
  yl_device_ver_contains:
    - C10_LZ_ASR3602_TW10
  zentao_names:
    - TW10_阿科奇_C10_九学王乐智
  project_id: 162
  verified: 2026-07-07
  note: User-confirmed mapping; branch name omits 九学王 but folder/project uses 九学王乐智; project id live-verified.

- branch_contains:
    - TW10_C10_3602_定乾有屏小程序20260528
  yl_device_ver_contains:
    - C10_DQ_ASR3602_TW10
  zentao_names:
    - TW18_阿科奇_C10_定乾太阳树小程序
  project_id: 173
  verified: 2026-07-07
  note: User-confirmed mapping; project name uses TW18+C10 while branch uses TW10_C10; project id live-verified.

- branch_contains:
    - TW10_C10_3602_光启象限有屏小程序20260624
  zentao_names:
    - TW10_阿科奇_C10_光启象限
  product_id: 140
  project_id: 202
  verified: 2026-07-07
  note: Screenshot-confirmed mapping; product id and project id verified from bug detail pages 3019/3014/2990.

- branch_contains:
    - TW10_C10_3602_有屏小程序协议20260325
  yl_device_ver_contains:
    - C10_ZX
  zentao_names:
    - TW10_阿科奇_C10_小程序公版
  project_id: 134
  verified: 2026-07-02
  note: Screenshot-confirmed mapping; project id live-verified 2026-07-03.

- branch_contains:
    - TW18_JC2_3602_艾闪_阿科奇_儿童陪伴机
  yl_device_ver_contains:
    - LINKI_AKQ
  zentao_names:
    - TW18_阿科奇_JC2_儿童陪伴机_小程序公版
  verified: 2026-07-02
  note: Screenshot-confirmed mapping; exact Zentao id not live-verified yet.

- branch_contains:
    - TW18_JC8_3602九颗桃老人腕表20260422
  zentao_names:
    - TW18_阿科奇_JC8_九颗桃
  project_id: 161
  verified: 2026-07-07
  note: Screenshot-confirmed mapping; project id live-verified.

- branch_contains:
    - TW18_JC8_3602小程序儿童版20260610
  zentao_names:
    - TW18_阿科奇_JC8_小程序儿童款公版
  project_id: 130
  verified: 2026-07-07
  note: Screenshot-confirmed mapping; project id live-verified.

- branch_contains:
    - TW18_JC8_3602_XD_小程序儿童版20260702
  zentao_names:
    - TW18-阿科奇-JC8-熊顿儿童款
    - TW18_阿科奇_JC8_熊顿小程序儿童款
  product_id: 131
  project_id: 190
  verified: 2026-07-07
  note: Screenshot-confirmed mapping; XD is treated as 熊顿; Zentao detail page product text uses hyphens and omits 小程序.

- branch_contains:
    - TW18_JC8_3602老人版公版
  zentao_names:
    - TW18_阿科奇_JC8_APP老人款公版
  project_id: 160
  verified: 2026-07-07
  note: Screenshot-confirmed mapping; project id live-verified.

- branch_contains:
    - TW18_LT52_3602_小程序公版物卡协议腕表20260410
  zentao_names:
    - TW18_阿科奇_LT52_小程序物卡公版
  project_id: 166
  verified: 2026-07-07
  note: Screenshot-confirmed mapping; project id live-verified.

- branch_contains:
    - TW18_LT52_3602_小程序协议腕表20251218
  zentao_names:
    - TW18_阿科奇_LT52_小程序公版
  project_id: 119
  product_id: 66
  verified: 2026-07-07
  note: Project id live-verified from `project-index-119.html`; product id live-verified from `product-browse-66.html`.

- branch_contains:
    - TW18_LT52_3602_小程序协议创维版腕表20260318
  zentao_names:
    - TW18_阿科奇_LT52_创维物卡小程序
  project_id: 132
  verified: 2026-07-07
  note: Project id live-verified from `project-index-132.html`; previous unconfirmed candidate `TW18_阿科奇_LT52_创维小程序` was incomplete.
```

## Generic Confirmed Families

Use these only when an exact branch mapping above does not match. If more than one candidate remains, ask the user.

```yaml
- local_tokens:
    - TW18
    - LT52
    - LZ
    - ASR3602
    - 3602
    - 电信乐智
  zentao_names:
    - TW18_阿科奇_LT52_乐智
  project_id: 164
  note: Prefer exact current-family match for branches like TW18_LT52_3602_电信乐智协议腕表 and versions like LT52_LZ_ASR3602_TW18.

- local_tokens:
    - TW18
    - LT52
    - 小程序
  zentao_names:
    - TW18_阿科奇_LT52_小程序
    - TW18_阿科奇_LT52_小程序物卡公版
  note: Ask if branch does not include 物卡, 创维, i武当, or other customer marker.

- local_tokens:
    - TW18
    - LT52
    - APP
    - 公版
    - ZX
  zentao_names:
    - TW18_阿科奇_LT52_APP
  product_id: 42
  note: Generic LT52 APP public family. Local branch may contain APP公版, while the confirmed Zentao project name is TW18_阿科奇_LT52_APP.

- local_tokens:
    - TW10
    - C10
    - 小程序
  zentao_names:
    - TW10_阿科奇_C10_小程序公版
  project_id: 134
  note: Generic TW10/C10 mini-program public family.

- local_tokens:
    - TW18
    - JC8
    - 小程序
    - 儿童
  zentao_names:
    - TW18_阿科奇_JC8_小程序儿童款公版
  project_id: 130
  note: Generic JC8 child mini-program family.

- local_tokens:
    - TW18
    - JC8
    - 老人
  zentao_names:
    - TW18_阿科奇_JC8_APP老人款公版
  project_id: 160
  note: Generic JC8 elder APP family.

- local_tokens:
    - TW18
    - JC2
    - 儿童陪伴机
  zentao_names:
    - TW18_阿科奇_JC2_儿童陪伴机_小程序公版
  note: Generic JC2 child companion device family.

- local_tokens:
    - TW18
    - JC2
    - 腕表
  zentao_names:
    - TW18_阿科奇_JC2_APP公版
  note: Generic JC2 watch family; ask if branch indicates 小程序/儿童陪伴机/艾闪.
```

## Unconfirmed Visible Branch Candidates

These branch names are visible in the current repo, but the exact Zentao product still needs user confirmation or live Zentao product discovery before automatic project filtering.

```yaml
- branch_contains: TW10_C10_3602_展能版有屏小程序20260513
  candidate: TW10_阿科奇_C10_展能小程序
  status: unconfirmed

- branch_contains: TW10_C10_3602_有屏兔盯协议20260613
  candidate: TW10_阿科奇_C10_兔盯
  status: unconfirmed

- branch_contains: TW10_C10_3602_有屏小程序移动DM专用
  candidate: TW10_阿科奇_C10_移动DM小程序
  status: unconfirmed

- branch_contains: TW10_NOLCD_3602_无屏小程序协议20260412
  candidate: TW10_阿科奇_NOLCD_无屏小程序
  status: unconfirmed

- branch_contains: TW18_JC2_3602_九学王学伴机20260414
  candidate: TW18_阿科奇_JC2_九学王学伴机
  status: unconfirmed

- branch_contains:
    - TW18_JC2_3602_腕表20251211
    - TW18_JC2_3602_腕表20251226
    - TW18_JC2_3602腕表20260109
  candidate: TW18_阿科奇_JC2_APP公版
  status: unconfirmed

- branch_contains: TW18_JC2_3602艾闪AI手表
  candidate: TW18_阿科奇_JC2_艾闪AI手表
  status: unconfirmed

- branch_contains: TW18_JC8_3602_儿童心率小程序协议腕表20260609
  candidate: TW18_阿科奇_JC8_儿童心率小程序
  status: unconfirmed

- branch_contains:
    - TW18_LT52_3602_北斗定制腕表20251202
    - TW18_LT52_3602_北斗定制腕表20260107
  candidate: TW18_阿科奇_LT52_北斗定制
  status: unconfirmed

- branch_contains: TW18_LT52_3602_i武当支付宝腕表
  candidate: TW18_阿科奇_LT52_i武当支付宝
  status: unconfirmed

- branch_contains: TW18_LT52_3602_小程序协议i武当腕表20260202
  candidate: TW18_阿科奇_LT52_i武当小程序
  status: unconfirmed

- branch_contains: TW18_LT55_3602带心率腕表固件20260203
  candidate: TW18_阿科奇_LT55_带心率腕表
  status: unconfirmed

- branch_contains:
    - TW18_LT66E_3602腕表固件20251211
    - TW18_LT66E_3602腕表固件20251226
    - TW18_LT66E_3602腕表固件20260109
  candidate: TW18_阿科奇_LT66E_腕表公版
  status: unconfirmed

- branch_contains: TW18_LT66E_3602移动入库专用腕表固件20260418
  candidate: TW18_阿科奇_LT66E_移动入库专用
  status: unconfirmed

- branch_contains:
    - TW18_3602腕表固件20250823
    - TW22_3602_腕表固件20260115
    - TW24_3602_腕表固件20260122
  candidate: 阿科奇腕表公版
  status: unconfirmed

- branch_contains:
    - TW18H_3602_海外腕表20251024
    - TW18_流式播放测试20251031
    - TW18_蓝牙跳绳测试20251010
    - TW18_3602改3603测试
  candidate: test-or-export-branch
  status: unconfirmed
  note: Do not auto-select a domestic Zentao project from these names.

- branch_contains:
    - TW62_3602_AI打印机20260520
    - TW62_3602_Printer拓步拍照打印机20260320
    - TW62_3602_Printer拓步拍照打印机20260415
    - TW62_3602_printer拓步打印机固件20260317
    - TW82_3602_AI打印机20260520
    - TW82_3602_Printer_双摄拍照打印机20260512
  candidate: printer-project
  status: unconfirmed
  note: Printer family, not watch/LVGL watch bug project by default.

- branch_contains:
    - TW66_3602_AI相机20260413
    - TW80_3602_双摄AI相机20260409
    - TW90_3602_双摄AI相机20260629
    - 3602_ai相机陈程用
    - 博升3602AI相机20260408
    - 拓步3602AI相机20260410
  candidate: ai-camera-project
  status: unconfirmed
  note: AI camera family, not watch/LVGL watch bug project by default.

- branch_contains: 3601_zy
  candidate: asr3601-generic-project
  status: unconfirmed
  note: Generic 3601 branch; ask for the exact product/project before Zentao project filtering.

- branch_contains:
    - 公版3602手表183屏8M_20240910
    - 山西联创3602手表183屏_20241008
    - 陕西联创新有屏_3602_8M_20240903
  candidate: legacy-183-8m-watch-project
  status: unconfirmed
  note: Older 183-screen/8M watch branches; do not auto-map to TW18/TW10 Akq folders.

- branch_contains: 支付宝TW18_3602腕表测试
  candidate: TW18_支付宝腕表测试
  status: unconfirmed
  note: Alipay test branch; ask before using a production Zentao project.

- branch_contains: JC8_JKT_xx
  candidate: TW18_阿科奇_JC8_九颗桃
  status: unconfirmed
  note: JKT may mean 九颗桃, but confirm before filtering.

- branch_contains:
    - TW18_LT36_3602腕表_20251203
    - TW18_LT36_3602腕表_20260408
  candidate: TW18_阿科奇_LT36_腕表
  status: unconfirmed

- branch_contains: TW66_游戏_x
  candidate: game-test-branch
  status: unconfirmed
  note: Game/test branch; not a normal watch bug project by default.
```

## Mapping Rules

- Prefer `Confirmed Exact Branch Mappings` over generic token matches.
- Prefer exact branch text over generic hardware tokens.
- Treat `ASR3601`, `ASR3602`, `3601`, `3602`, `360x`, `crane`, `gui/lv_watch`, `product/craneg_modem`, and `yl.h` as firmware-family clues for enabling Zentao bug triage, but do not use them alone to choose a Zentao product.
- Use `yl_device_ver` and `yl_hw_ver` to confirm `TW10/TW18`, model, chip family, protocol/customer marker, and domestic/export markers.
- If the branch contains customer words such as 乐智, 定乾, 九学王, 光启象限, 创维, 熊顿, 九颗桃, 艾闪, 北斗, i武当, 兔盯, 展能, or 移动DM, include them in the match.
- Do not infer a single project from `TW18`, `TW10`, `C10`, `LT52`, or `3602` alone.
- If the user asks for “当前分支” and an exact confirmed mapping matches, fetch that project directly.
- If only an unconfirmed candidate matches, list the candidate and ask the user before project-specific fetching.
- If no project mapping matches but the workspace is a 3601/3602 firmware family, fetch assigned bugs first, then classify by product/title without project filtering.
