# ASR360x Feature-Closure Report Shape

This synthetic sample documents report structure only. Never copy a real repository path, branch, device/version identifier, customer mapping, commit, server address, or proprietary source evidence into this bundled reference.

## Audit Input

- Feature: `example_feature`
- Expected state: `removed`
- Compatibility policy: `retain`
- Keywords: `EXAMPLE_FEATURE`, `example_event`
- Target macro: `USE_EXAMPLE_FEATURE`

## Variant Fingerprint

| Field | Value |
|---|---|
| repo | `repo-<hash>` |
| branch | `branch-<hash>` |
| target | `target-<hash>` |
| worktree | `clean` |
| source | `.codex-project/variant.md` |

## Closure Table

| Layer | State | Active | Guarded | Commented | Evidence |
|---|---|---:|---:|---:|---|
| Build | `guarded` | 0 | 1 | 0 | `path/to/build-file:10` |
| UI | `removed` | 0 | 0 | 0 | none |
| Runtime hooks | `needs-review` | 1 | 0 | 0 | `path/to/source.c:20` |
| Protocol | `compat-retained` | 1 | 1 | 0 | `path/to/protocol.h:30` |

## Conclusion

- Static evidence shows the public entry point is removed, while one runtime hook still requires review.
- `compat-retained` identifiers are intentionally preserved for wire/storage compatibility.
- This report is static evidence and does not claim build, device, platform, or QA verification.
