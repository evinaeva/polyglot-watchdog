# Docs auto-update subsystem

This subsystem records merged-PR context and performs scheduled AI-driven docs synchronization with strict patch-only safety checks.

## Workflows
- `.github/workflows/docs-pr-feed.yml` calls `.github/docs_autoupdate/scripts/update_merged_pr_feed.py` after PR merges to append feed entries to `docs/auto/merged_pr_feed.md`.
- `.github/workflows/docs-ai-sync.yml` calls `.github/docs_autoupdate/scripts/docs_ai_sync.py` and `.github/docs_autoupdate/scripts/validate_docs_diff.py` on schedule/manual trigger to process feed delta and current allowlisted docs snapshot.

## Canonical config
- This subsystem uses constants and defaults in `.github/docs_autoupdate/scripts/*.py` plus workflow env/paths in `.github/workflows/docs-*.yml`.

## What to customize when copying to another repo
Update script constants/workflow values for:
- workflow branches and cron metadata
- feed/state/prompt/runtime paths
- allowlist, machine-managed paths, blacklist, runtime ignore prefixes
- AI defaults (model, timeout, token/temperature limits)
- processing limits and commit message templates
- expected GitHub environment variable names

## Required GitHub configuration
- **Secret**: `AI_API_KEY`.
- **Optional Variable**: `AI_MODEL` to override the default model (`gemini-2.5-flash-lite`).
- `GITHUB_TOKEN`, `GITHUB_EVENT_PATH`, `GITHUB_REPOSITORY`, and `GITHUB_OUTPUT` are provided by GitHub Actions.

## Incremental sync state
- The sync cursor/state is stored at `docs/auto/docs_sync_state.json` on the `DOCS_AUTOUPDATE` branch.
