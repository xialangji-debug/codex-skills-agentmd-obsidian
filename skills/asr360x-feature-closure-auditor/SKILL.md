---
name: asr360x-feature-closure-auditor
description: Audit ASR3601/ASR3602/Crane/LVGL customer-branch feature additions, removals, and compatibility retention across build lists, menus/factory UI, initialization/tasks, protocol link/pro/sender/cap paths, and ID/NV definitions. Use when users ask “功能裁剪完整吗”, “客户版去掉XX”, “只保留XX”, “公版派生”, “菜单隐藏但还上报”, or need a read-only feature-closure report before editing a firmware branch.
---

# ASR360x 功能闭包审计

先运行确定性扫描，再基于证据判断是否需要改代码。默认保持只读。

## 工作流

1. 读取仓库级 `AGENTS.md` 与 `.codex-project/` 上下文（如存在），确认 repo、branch、short commit、版本、芯片、OS、协议、客户和构建参数。
2. 为功能准备窄别名。不要把泛化的 `AI` 或 `AVD` 单独当作防欺凌证据；优先传入 `antibully`、`bullyevent`、`防欺凌`、`jason_avd`、具体宏、协议枚举和模块名。短 ASCII 词会按完整 token 匹配，避免 `AVD` 误命中 `libavdevice`。
3. 运行：

```powershell
python "$env:USERPROFILE\.codex\skills\asr360x-feature-closure-auditor\scripts\audit_feature_closure.py" `
  --repo <repo> --feature <功能名> --expected removed `
  --keyword <别名1> --keyword <别名2> --guard <统一开关> `
  --output <报告.md>
```

4. 检查变体指纹和每个闭包环节。把 `present` 视为运行链路仍可能存在；把 `needs-review` 视为不能自动下结论。
5. 若用户要求修改，先给出最小修改计划；修改后重新运行同一命令，并交给相应 verifier 做编译、map、真机或平台验证。

## 判定规则

- `present`：发现未受目标宏保护的有效命中。
- `guarded`：命中仍在源码中，但位于目标预处理宏保护范围内，或统一开关显式为关闭。
- `removed`：目标环节未发现有效命中，或只剩注释命中。
- `compat-retained`：ID、NV、Activity/Text ID 或协议枚举按兼容策略保留。
- `needs-review`：证据不足、别名歧义或兼容项缺失，必须人工核对。

## 边界

- 默认保留协议枚举、Activity/Text ID、资源 ID 和 NV section；除非协议或持久化兼容性证据明确要求删除。
- 不把菜单隐藏等同于功能关闭；同时检查构建、初始化/任务、收发协议和上报链路。
- 不跨 APP、XCX/小程序、乐智等协议机械套用扫描结论。
- 把报告视为静态证据，不把它表述成编译、真机或平台验证结果。
- `present` 只表示源码层仍有未直接受宏保护的命中；若源码已从 CMake 移除或只有受保护的注册/调用点，必须结合构建清单与 ELF map 判断运行闭包，不能据此单独判定功能仍生效。
- 对二进制、生成目录、第三方代码和超大文件只做排除，不尝试反编译。

## 资源

- 使用 `scripts/audit_feature_closure.py` 生成 Markdown 变体指纹和闭包表。
- 需要核对报告格式或韫一防欺凌基线时，读取 `references/first-sample.md`。
