# Resource Changes: Reuse The Existing Build

Apply to images, fonts, resource registration and resource generation rules.
For UI layout alone, inspect the affected paths and use an available preview
when useful; rebuild resources only if an actual generator input changed.

## Normal Work

- Reuse the known resource path and build rule. For an existing asset replacement,
  inspect the changed asset and its reference. For a new or renamed asset, check
  its registration. Keep the check local to this change.
- Use the existing generation/build command within the user's scope. Reuse
  resource generation performed by the requested build; run a separate focused
  resource step only when the project requires it. Source-only work stays source-only.
- Reuse the build owner's existing artifact checks and result. Report the changed
  resource, actual generation/build result and requested output briefly. Additional
  input-hash manifests, resource receipts and evidence tables are not required.
  Their absence does not downgrade a successful build or release.

Formal/Quick Release keeps its single-controller path and recovery rules; a FOTA
pair uses its existing two builds. Existing artifact gates remain controller-owned.

## When To Investigate Further

Expand the check when an old asset still appears, registration or generation is
missing/failed, the wrong target is selected, or the user requests a deeper audit.
Inspect the relevant log, index or package to resolve that specific doubt.

Resolve ambiguous names such as `rf.bin` from the project when necessary; RF
inputs and `resource.bin` are distinct. Reuse confirmed mappings. An available
renderer can check the affected page; report actual preview/device observations
separately from build success.
