# Docs auto-update subsystem

This subsystem records merged-PR context and performs scheduled AI-driven docs synchronization with strict patch-only safety checks.

## Workflows
- `.github/workflows/docs-pr-feed.yml` calls `scripts/update_merged_pr_feed.py` after PR merges to append feed entries.
- `.github/workflows/docs-ai-sync.yml` calls `scripts/docs_ai_sync.py` and `scripts/validate_docs_diff.py` for scheduled/manual sync.

## Canonical config
- Single source of truth: `.github/docs_autoupdate/config.json`
- Workflow YAML files should stay thin wrappers; repo/operator settings should be changed in `config.json`.

## What to customize when copying to another repo
Update `config.json` values for:
- workflow branches and cron metadata
- feed/state/prompt/runtime paths
- allowlist, machine-managed paths, blacklist, runtime ignore prefixes
- Claude defaults (model, timeout, token/temperature limits)
- processing limits and commit message templates
- expected GitHub environment variable names

## Required GitHub configuration
- **Secret**: `ANTHROPIC_API_KEY` (or the name configured in `ai.api_key_env`).
- **Optional Variable**: `ANTHROPIC_MODEL` (or the name configured in `ai.model_env`) to override the default model.
- `GITHUB_TOKEN`, `GITHUB_EVENT_PATH`, `GITHUB_REPOSITORY`, and `GITHUB_OUTPUT` are provided by GitHub Actions and referenced via config.
