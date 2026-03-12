# Merged PR Feed

Append-only feed of merged pull requests into `main`.

This file is machine-updated by `.github/workflows/docs-pr-feed.yml` on branch `DOCS_AUTOUPDATE`.

## PR #67 — 2026-03-12T09:40:23Z

- Title: Add AI-driven docs auto-sync (scripts, workflows, and tests)
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/67
- Author: evinaeva
- Base branch: main
- Head branch: jtchyu-codex/implement-documentation-auto-update-system
- Merge commit: 3d46850994182226214919bf03a2825d07547388
- Changed files:
  - .github/prompts/docs_sync_prompt.txt
  - .github/scripts/docs_ai_sync.py
  - .github/scripts/update_merged_pr_feed.py
  - .github/scripts/validate_docs_diff.py
  - .github/workflows/docs-ai-sync.yml
  - .github/workflows/docs-pr-feed.yml
  - docs/auto/docs_sync_state.json
  - docs/auto/merged_pr_feed.md
  - tests/test_docs_autoupdate_scripts.py
- Notes: Auto-generated from merged PR metadata.

## PR #66 — 2026-03-12T09:40:34Z

- Title: Exclude script elements from pulls and add UI filters and existing-run support
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/66
- Author: evinaeva
- Base branch: main
- Head branch: dloxqu-codex/implement-operator-ui-fixes-for-pulls-and-workflow
- Merge commit: 77cdd7840d73135196e9a458dbdb369807b69bbe
- Changed files:
  - app/skeleton_server.py
  - tests/test_stage_a_read_routes_api.py
  - tests/test_stage_c_operator_workflow.py
  - web/static/pulls.js
  - web/static/workflow.js
  - web/templates/pulls.html
  - web/templates/workflow.html
- Notes: Auto-generated from merged PR metadata.
