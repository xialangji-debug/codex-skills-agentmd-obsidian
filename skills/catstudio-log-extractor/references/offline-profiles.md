# Offline Profiles

Use the smallest profile that can answer the question.

| Need | Command option |
|---|---|
| Application, UI, protocol, micro-chat | `--fast-evidence` or `--profile mmi` |
| Memory or CPU hints | `--profile mmi --profile memory --summary` |
| LTE, SIM, WiFi, GPS, or location | `--profile mmi --profile network --require-keyword <term>` |
| Crash, reset, watchdog, or fatal | `--profile mmi --profile crash --profile system --summary` |
| Unknown broad failure after compact pass | `--evidence-pack` |
| Exact category/term selection | `--profile custom --include <path> --keyword <term>` |

Profiles may be repeated. `all` can be large and is only for a deliberately broad offline scan.

Examples:

```powershell
python "%USERPROFILE%\.codex\skills\catstudio-log-extractor\scripts\extract_catstudio_logs.py" "<log.zip>" --fast-evidence --keyword TXT --keyword CHAT1 --output-dir "<output>"

python "%USERPROFILE%\.codex\skills\catstudio-log-extractor\scripts\extract_catstudio_logs.py" "<log.zip>" --profile mmi --profile crash --profile system --summary --output-dir "<output>"
```

Output notes:

- `mmi` uses the compact 11-column format unless extended output is requested.
- Other profiles preserve category IDs, database format strings, printable previews, and bounded payload hex.
- The parser does not fully emulate every CATStudio binary struct decoder.
- Repeating the same fast-evidence input and options reuses cached output.
