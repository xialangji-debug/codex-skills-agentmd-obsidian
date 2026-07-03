# Project Folder Map

Use this file to map local projects/branches to fnOS domestic product folders. Add entries after the user confirms a mapping.

## Known Local Projects

### `D:\XM\c10lezhi`

- Current observed branch: `TW18_LT52_3602_电信乐智协议腕表20260610`
- Observed `yl_device_ver` stem: `LT52_LZ_ASR3602_TW18_...`
- fnOS folder: `TW18_阿科奇_LT52_乐智`

### `D:\XM\c10gongban`

- Observed output path: `D:\XM\c10gongban\out\product\craneg_modem_watch`
- fnOS folder: unresolved; infer from branch/product only after checking.

## Confirmed Mappings

```text
local_path: D:\XM\c10lezhi or D:\XM\c10gongban
branch_contains: TW10_3602_有屏电信乐智协议20260523
yl_device_ver_contains: C10_LZ_ASR3602_TW10
fnos_folder: TW10_阿科奇_C10_九学王乐智
verified: 2026-07-02
note: User confirmed this mapping even though the local branch name does not contain 九学王.
```

```text
local_path: D:\XM\c10lezhi or D:\XM\c10gongban
branch_contains: TW10_C10_3602_定乾有屏小程序20260528
yl_device_ver_contains: C10_DQ_ASR3602_TW10
fnos_folder: TW18_阿科奇_C10_定乾太阳树小程序
verified: 2026-07-02
note: User confirmed this mapping; the remote folder name uses TW18+C10 while the branch is TW10_C10.
```

```text
local_path: D:\XM\c10lezhi
branch_contains: TW18_LT52_3602_电信乐智协议腕表20260610
yl_device_ver_contains: LT52_LZ_ASR3602_TW18
fnos_folder: TW18_阿科奇_LT52_乐智
verified: 2026-07-02
note: Resolved from fnOS team path during upload API verification.
```

```text
local_path: D:\XM\c10lezhi or D:\XM\c10gongban
branch_contains: TW10_C10_3602_光启象限有屏小程序20260624
fnos_folder: TW10_阿科奇_C10_光启象限
verified: 2026-07-02
note: Screenshot-confirmed mapping; branch name directly matches 光启象限.
```

```text
local_path: D:\XM\c10lezhi or D:\XM\c10gongban
branch_contains: TW10_C10_3602_有屏小程序协议20260325
yl_device_ver_contains: C10_ZX
fnos_folder: TW10_阿科奇_C10_小程序公版
verified: 2026-07-02
note: Screenshot-confirmed mapping; branch and yl_device_ver point to TW10 C10 small-program public release.
```

```text
local_path: D:\XM\c10lezhi or D:\XM\c10gongban
branch_contains: TW18_JC2_3602_艾闪_阿科奇_儿童陪伴机
yl_device_ver_contains: LINKI_AKQ
fnos_folder: TW18_阿科奇_JC2_儿童陪伴机_小程序公版
verified: 2026-07-02
note: Screenshot-confirmed mapping; branch directly contains 阿科奇/儿童陪伴机 and version contains LINKI_AKQ.
```

```text
local_path: D:\XM\c10lezhi or D:\XM\c10gongban
branch_contains: TW18_JC8_3602九颗桃老人腕表20260422
fnos_folder: TW18_阿科奇_JC8_九颗桃
verified: 2026-07-02
note: Screenshot-confirmed mapping; branch name directly matches 九颗桃老人腕表.
```

```text
local_path: D:\XM\c10lezhi or D:\XM\c10gongban
branch_contains: TW18_JC8_3602小程序儿童版20260610
fnos_folder: TW18_阿科奇_JC8_小程序儿童款公版
verified: 2026-07-02
note: Screenshot-confirmed mapping; branch name and Release_WX evidence point to JC8 small-program child public folder.
```

```text
local_path: D:\XM\c10lezhi or D:\XM\c10gongban
branch_contains: TW18_JC8_3602_XD_小程序儿童版20260702
fnos_folder: TW18_阿科奇_JC8_熊顿小程序儿童款
verified: 2026-07-02
note: Screenshot-confirmed mapping; XD is noted as likely 熊顿.
```

```text
local_path: D:\XM\c10lezhi or D:\XM\c10gongban
branch_contains: TW18_JC8_3602老人版公版
fnos_folder: TW18_阿科奇_JC8_APP老人款公版
verified: 2026-07-02
note: Screenshot-confirmed mapping; branch name directly matches 老人版公版.
```

```text
local_path: D:\XM\c10lezhi or D:\XM\c10gongban
branch_contains: TW18_LT52_3602_小程序公版物卡协议腕表20260410
fnos_folder: TW18_阿科奇_LT52_小程序物卡公版
verified: 2026-07-02
note: Screenshot-confirmed mapping; branch name directly matches LT52 small-program public IoT-card protocol watch.
```

Add confirmed mappings in this format:

```text
local_path: D:\XM\<repo>
branch_contains: <keyword>
yl_device_ver_contains: <keyword>
fnos_folder: <folder under 团队文件 > 阿科奇 > 阿科奇-国内>
verified: YYYY-MM-DD
```

Do not silently guess a folder if multiple TW10/TW18 folders match.
