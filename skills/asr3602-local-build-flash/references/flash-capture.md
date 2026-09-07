# Normal Flash And Current-Session Capture

Use this reference only when the user explicitly requests both flashing and log
capture.

1. Build with `local_build_flash.ps1 -NoFlash -CleanTargetOutput
   -RequireFreshPackage`. Cleanup is limited to the validated generated target
   output; it must not run repository-wide clean or touch source files.
2. Pin the emitted absolute package path and SHA256. Pass both to
   `aboot_flash_then_capture`; never let a later step choose a different newest
   package.
3. Require package hash, project target, chip compatibility, live branch/commit,
   and unique physical USB identity to match.
4. Let the combined owner perform the single flash and current-session CATStudio
   Stop/save operation.
5. Use `requiredKeywords` or `requiredRegex` only for real business assertions.
   Plain `keywords` are extraction hints. `businessStatus=NOT_REQUESTED` is
   capture-only evidence.

Keep release/readme/fnOS/`yl.h` and watchdog/Dump operations outside this mode.
