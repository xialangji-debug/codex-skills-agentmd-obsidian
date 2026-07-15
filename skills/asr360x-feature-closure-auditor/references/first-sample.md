# ASR360x 功能闭包审计

## 审计输入

- 生成时间：`2026-07-13T19:44:55+08:00`
- 功能：`AI/防欺凌`
- 期望：`removed`
- 兼容策略：`retain`
- 关键词：`antibully`, `bullyevent`, `防欺凌`, `USE_LV_WATCH_AI_ANTIBULLY`, `APP_AIA`, `XCX_ANTIBULLY`, `XCX_BULLYEVENT`, `jason_avd`, `init_avd_irq_set`, `gxw8002.c`
- 目标宏：`USE_LV_WATCH_AI_ANTIBULLY`

## 变体指纹

| 字段 | 值 |
|---|---|
| repo | `C:\Users\84365\Desktop\inside\lt52_DX_LZ` |
| branch | `TW18_LT52_3602_韫一乐智协议腕表20260713` |
| short commit | `28dda9455` |
| upstream | `origin/TW18_LT52_3602_韫一乐智协议腕表20260713` |
| ahead/behind | `ahead 0 / behind 0` |
| worktree | `clean` |
| yl_device_name | `LT52` |
| yl_device_ver | `LT52_LZYY_ASR3602_TW18_V1.1_RTOS_CN_20260713_1915_V1.0.1_Release_WX` |
| yl_hw_ver | `TW18_LZ_3602` |
| chip / OS | `CRANEL` / `ALIOS` |
| protocol / customer | `LT52 电信乐智协议` / `TW18_LT52_3602_韫一乐智协议腕表20260713` |
| build params | `make craneg_modem_watch TARGET_OS=ALIOS PS_MODE=LITE_LTEONLY CHIP_ID=CRANEL` |
| fingerprint source | `C:\Users\84365\Desktop\inside\lt52_DX_LZ\.codex-project\variant.md` |

## 功能闭包表

| 环节 | 状态 | active | guarded | commented | 证据 |
|---|---|---:|---:|---:|---|
| 构建/CMake | `present` | 1 | 0 | 0 | `gui/lv_drivers/CMakeLists.txt:75` indev/gxw8002.c |
| 菜单/工模/UI | `present` | 39 | 7 | 3 | `gui/lv_watch/include/ui_textid.h:2307` WATCH_TEXT_ID_AI_ANTIBULLY,     //AI防欺凌<br>`gui/lv_watch/include/ui_textid.h:2309` WATCH_TEXT_ID_AI_ANTIBULLY_TEST,//AI防欺凌测试<br>`gui/lv_watch/lv_apps/ai_antibully/antibully.c:7` lv_obj_t *antibully_create(lv_obj_t *activity_obj)<br>`gui/lv_watch/lv_apps/ai_antibully/antibully.c:14` activity_ext.actId = ACT_ID_ANTIBULLY;<br>`gui/lv_watch/lv_apps/ai_antibully/antibully.c:15` activity_ext.create = antibully_create;<br>另有 44 条 |
| 初始化/周期任务/事件 | `present` | 50 | 27 | 22 | `gui/lv_drivers/indev/gxw8002.c:237` extern void init_avd_irq_set(){<br>`gui/lv_watch/lv_apps/factory_mode/factory_mode_ai_antibully.c:22` static void antibully_check_nv_task(lv_task_t *task);<br>`gui/lv_watch/lv_apps/factory_mode/factory_mode_ai_antibully.c:54` static void antibully_open_close_event_cb(lv_obj_t *btn, lv_event_t event)<br>`gui/lv_watch/lv_apps/factory_mode/factory_mode_ai_antibully.c:72` static void antibully_check_nv_task(lv_task_t *task)<br>`gui/lv_watch/lv_apps/factory_mode/factory_mode_ai_antibully.c:106` static void antibully_download_event_cb(lv_obj_t *btn, lv_event_t event)<br>另有 94 条 |
| 协议 link/pro | `present` | 10 | 15 | 7 | `gui/lv_watch/lv_apps/yl/akq_link_pro.c:978` static void akq_message_recv_antibully(akq_tls_recv_message_all *msg, tls_handle_t handle) //...<br>`gui/lv_watch/lv_apps/yl/akq_link_pro.c:981` printf("Received  antibully buf=%.*s\n", msg->message_length, msg->body);<br>`gui/lv_watch/lv_apps/yl/akq_link_pro.c:984` nv_antibully_list_t *list = (nv_antibully_list_t *)Hal_Mem_Alloc(sizeof(nv_antibully_list_t));<br>`gui/lv_watch/lv_apps/yl/akq_link_pro.c:985` memset(list, 0, sizeof(nv_antibully_list_t));<br>`gui/lv_watch/lv_apps/yl/akq_link_pro.c:1042` if (get_msg_status(AKQ_ANTIBULLY) == 1)<br>另有 27 条 |
| 协议 sender/cap | `present` | 52 | 23 | 9 | `gui/lv_watch/lv_apps/akq_xcx_protocal/xcx_cap.c:56` "ANTIBULLY",      // 设置防欺凌<br>`gui/lv_watch/lv_apps/akq_xcx_protocal/xcx_cap.c:57` "BULLYEVENT",     // 上报欺凌<br>`gui/lv_watch/lv_apps/akq_xcx_protocal/xcx_cap.h:51` XCX_ANTIBULLY,      // 设置防欺凌<br>`gui/lv_watch/lv_apps/akq_xcx_protocal/xcx_cap.h:52` XCX_BULLYEVENT,     // 上报欺凌<br>`gui/lv_watch/lv_apps/akq_xcx_protocal/xcx_cap.h:98` APP_AIA,     // AI防欺凌<br>另有 79 条 |
| ID/NV/枚举兼容项 | `compat-retained` | 32 | 18 | 2 | `gui/lv_watch/framework/nvm/yl_nvm_api.c:101` case NV_SECTION_AKQ_ANTIBULLY:<br>`gui/lv_watch/framework/nvm/yl_nvm_api.c:102` return (NV_SECTION_LEN(NV_SECTION_AKQ_ANTIBULLY));<br>`gui/lv_watch/framework/nvm/yl_nvm_api.c:103` case NV_SECTION_AKQ_ANTIBULLY_FIREWARE_STATUES:<br>`gui/lv_watch/framework/nvm/yl_nvm_api.c:104` return (NV_SECTION_LEN(NV_SECTION_AKQ_ANTIBULLY_FIREWARE_STATUES));<br>`gui/lv_watch/framework/nvm/yl_nvm_api.c:207` case NV_SECTION_AKQ_ANTIBULLY:<br>另有 47 条 |
| 其他命中 | `present` | 33 | 3 | 10 | `gui/lv_drivers/indev/gxw8002.c:134` extern void jason_avd_clean_rx(void){<br>`gui/lv_drivers/indev/gxw8002.c:139` extern void jason_avd_get_rx(void *buf){<br>`gui/lv_drivers/indev/gxw8002.c:199` extern void jason_avd_power(int status)<br>`gui/lv_drivers/indev/gxw8002.c:245` extern void jason_avd_irq_open(int status)<br>`gui/lv_watch/framework/language/lang_ch.c:2301` "AI防欺凌",<br>另有 41 条 |

## 目标宏取值

- `USE_LV_WATCH_AI_ANTIBULLY` = `0`

## 状态定义

- `present`：存在未受目标宏保护的有效命中。
- `guarded`：源码仍保留，但受目标宏保护或统一开关显式关闭。
- `removed`：该环节无有效命中或仅剩注释命中。
- `compat-retained`：ID、NV 或协议枚举按兼容策略保留。
- `needs-review`：证据不足或兼容项缺失，不能自动下结论。

## 结论

- 需优先复核：构建/CMake, 菜单/工模/UI, 初始化/周期任务/事件, 协议 link/pro, 协议 sender/cap, 其他命中。
- 本报告是只读静态扫描结果，不等同于编译、链接 map、真机或平台验证。
- `removed` 依赖当前关键词集合；出现新别名时必须使用相同参数补扫。

## 样板人工判读

- canonical 指纹与当前 checkout 一致；统一宏 `USE_LV_WATCH_AI_ANTIBULLY=0`。
- `7ebe5b109` 已从 `gui/lv_watch/CMakeLists.txt` 移除 6 个防欺凌专用页面/任务源文件，并给菜单、初始化、主动请求、处理注册和上报入口加统一宏。
- `gui/lv_drivers/CMakeLists.txt` 仍列出 `indev/gxw8002.c`，协议函数体、UI/Text ID、NV 和枚举源码也仍保留。因此静态源码层应保持 `present/compat-retained`，不能伪装成物理删除。
- 现有 fix-pattern 记录此前全量构建、ELF map、远端发布已验证；当前 checkout 的 `out` 下没有可重新核验的 `.map`，本次只读样板不把历史 map 结论冒充当前验证。
- 最终判读：产品运行入口已按宏和构建裁剪，兼容 ID/NV/枚举按设计保留；在另一个客户分支复用时，必须重新跑目标全量构建并检查 ELF map，确认 `antibully/bullyevent/jason_avd/gxw8002` 不进入最终镜像。
