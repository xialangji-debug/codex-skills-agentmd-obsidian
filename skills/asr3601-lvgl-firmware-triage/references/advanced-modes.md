# Reference UI And Feature Closure

Load only the section matching the request. Normal source lookup and Fast Fix do not need this file.

## Reference UI

From the supplied screenshots, videos, or effect drawings, establish page/state inventory and the old-UI removal boundary; encoder/key/touch/timer/back behavior; resources, fonts, languages, resolution, animation, focus, timeout, and persistence. Record an implementation order and page-by-page acceptance criteria.

Implement in small target-native steps. Check page registration, resource indexes, LVGL object lifetime, long-text layout, and excluded variants. Inspect both create and refresh paths. Visual references establish visible states, not unobserved behavior; resolve missing states from current source or the user's requirements.

## Feature Closure

Keep an audit read-only unless the request authorizes edits.

1. Confirm the customer/protocol variant only where it determines the feature boundary.
2. Choose narrow aliases from the feature name, macros, protocol enums, module names, and Chinese terms. Avoid generic tokens alone.
3. Run the deterministic scanner:

```powershell
python "$env:USERPROFILE\.codex\skills\asr3601-lvgl-firmware-triage\scripts\audit_feature_closure.py" `
  --repo <repo> --feature <feature> --expected removed `
  --keyword <alias1> --keyword <alias2> --guard <shared-switch> --output <report.md>
```

4. Inspect build lists, menus/factory UI, initialization/tasks, protocol senders/capabilities, and ID/NV definitions. Hiding a menu does not establish runtime removal.
5. Classify evidence as present, guarded, removed, compat-retained, or needs-review. Combine source hits with build lists and available ELF/map evidence. Static findings do not establish device/platform/QA acceptance.
6. Preserve protocol enums, Activity/Text/resource IDs, and NV sections unless compatibility evidence supports removal. After an authorized change, rerun the same scan.

Read [sample report](feature-closure-first-sample.md) only when a report example is needed. Use the main Skill's verification and memory closeout once.
