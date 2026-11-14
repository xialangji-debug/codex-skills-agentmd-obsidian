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

If CATStudio is already running, pass its exact `existingCaptureSession` receipt,
including PID, process start, executable path and physical USB identity. The owner
finalizes only that session before flashing. Ambiguous/unbound sessions or other
downloaders stop the operation without closing them. An explicitly discarded log
still requires the exact session binding; it does not authorize a name-wide kill.

Previous capture finalization is reported separately. A failed or cancelled flash
does not imply that prior capture resumed. Preserve its saved files and session
receipt; use the existing supervisor's exact-session recovery only within its
authorized scope. In particular, supervisor `resume` can include reflash and must
not be used as an implicit generic logger restart.
