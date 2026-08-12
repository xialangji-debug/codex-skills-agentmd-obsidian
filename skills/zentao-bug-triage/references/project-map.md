# Zentao Project Map Template

This bundled file documents the mapping schema only. Keep real branch names, customer/product names, device/version tokens, external-system IDs, and notes in the private local file:

`%USERPROFILE%\.codex\zentao-bug-triage\project-map.local.md`

Never commit or synchronize the private file.

```yaml
- branch_contains:
    - example-firmware-main
  yl_device_ver_contains:
    - EXAMPLE_DEVICE_V1
  zentao_names:
    - Example Firmware Project
  product_names:
    - Example Firmware Product
  project_id: "100"
  product_id: "200"
  verified: 2000-01-01
  status: confirmed
  note: Synthetic example only.

- local_tokens:
    - example-repository
    - example-device
  candidate: Example Candidate Project
  status: unconfirmed
  note: Synthetic fallback example; require confirmation before project-specific fetching.
```
