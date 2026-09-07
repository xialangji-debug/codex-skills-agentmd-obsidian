# Public Snapshot Publication

`public-sync-manifest.json` owns the public allowlist. The synchronizer copies
listed global files, Skills, runtime dependencies, and MCP metadata. It generates
README inventory and `skills-index/index.md` from the same list. `retired_skills`
permits removal of named obsolete Skill copies without reading their local archives.
Never infer public eligibility from local installation or copy a private Vault.

## Routine Sync

1. Verify the exact origin and a clean dedicated checkout. GitHub commands run
   directly without changing proxy configuration. Fetch `main`; only fast-forward
   the local base. Stop for divergence, unknown edits, or authentication failures.
2. Query open `automation/public-sync-*` PRs before reading local sources. If one
   exists, report its URL and check status, then stop. Do not create duplicates or
   append unattended changes to a PR being reviewed.
3. Run `python -X utf8 scripts/sync_public_snapshot.py` with the external
   repo-privacy denylist. Zero changes need no branch, commit, or PR.
4. Create a unique `automation/public-sync-YYYYMMDD-HHmm` branch from current
   `main` and record its base SHA. Run the same sync command with `--apply`.
5. Review the generated paths and whitespace. Stage only changed managed paths:
   `AGENTS.md`, `README.md`, `skills/`, `skills-index/`, `runtime/`, and `mcp/`.
   Run the staged privacy scan with the external denylist, then
   `python -X utf8 scripts/run_public_checks.py` and `git diff --cached --check`.
6. Commit `chore(sync): refresh public Codex snapshot`, push the exact branch,
   and create a PR to `main`. Verify the remote SHA and checks for that commit.
   Never push `main`, enable auto-merge, force-push, or publish a release.

Install test dependencies with `python -m pip install -r requirements-dev.txt`.
Install Node.js dependencies with `npm ci --ignore-scripts`; mocked tests do not
launch or download browsers.
The check runner installs into a temporary profile and runs tests there, so a
developer's installed Skills and runtime cannot mask missing package dependencies.
Windows-only build helper tests run on Windows; portable checks run on both CI OSes.

## Authorized Maintenance

An interactive request may update manifest, scripts, workflows, and an existing
PR together. Preserve concurrent changes. Generate the snapshot in an isolated
clean checkout using the reviewed manifest, verify the exact baseline for every
destination, and transfer only generated paths to the maintenance checkout.
This keeps the normal synchronizer's clean-worktree gate intact. Run full checks
and the staged privacy scan before committing the complete consistent change.

## Interrupted Publication

Retry transient network errors at most twice after 10 and 30 seconds. Before
retrying push, compare the exact remote branch SHA; before retrying PR creation,
query the exact head branch. An existing matching remote commit or PR is success.
Record the base SHA and branch in `.git/public-sync-state.json` before applying.
After committing, record the commit SHA. Resume only that recorded branch when
its base-to-HEAD diff contains only managed paths and its routine commit title
matches. Validate the full snapshot with the external denylist, full checks, and
the base-to-HEAD whitespace check. An empty staged scan cannot validate a commit.
Unknown dirty changes, privacy findings, and failed tests require review. Keep
the failed candidate for diagnosis; do not discard files or repair local sources
during unattended runs. Never include this private runtime receipt in Git.
