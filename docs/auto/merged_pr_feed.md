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

## PR #68 — 2026-03-12T10:17:49Z

- Title: Validate ANTHROPIC_MODEL env var and avoid API call for malformed values; exclude auto state files from docs commits
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/68
- Author: evinaeva
- Base branch: main
- Head branch: 43x4ew-codex/fix-documentation-auto-update-implementation
- Merge commit: 8603673271181921c1645257e8019ae472050b7a
- Changed files:
  - .github/scripts/docs_ai_sync.py
  - .github/workflows/docs-ai-sync.yml
  - docs/auto/docs_sync_state.json
  - tests/test_docs_autoupdate_scripts.py
- Notes: Auto-generated from merged PR metadata.

## PR #69 — 2026-03-12T10:49:50Z

- Title: Harden docs AI sync malformed JSON diagnostics
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/69
- Author: evinaeva
- Base branch: main
- Head branch: ksmiwi-codex/fix-json-parse-failure-handling
- Merge commit: b68e02c369a88826a0bee6f82ce1ecee09e9fc7f
- Changed files:
  - .github/prompts/docs_sync_prompt.txt
  - .github/scripts/docs_ai_sync.py
- Notes: Auto-generated from merged PR metadata.

## PR #70 — 2026-03-12T12:03:20Z

- Title: fix(docs-sync): increase Claude token limit, exclude docs/auto from AI edits, upload raw response on parse failure
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/70
- Author: evinaeva
- Base branch: main
- Head branch: vruefo-codex/fix-reliability-issues-in-docs-ai-sync
- Merge commit: 04f27840c4c05e80e7c6573dfb1135a339c56ea7
- Changed files:
  - .github/prompts/docs_sync_prompt.txt
  - .github/scripts/docs_ai_sync.py
  - .github/workflows/docs-ai-sync.yml
- Notes: Auto-generated from merged PR metadata.

## PR #71 — 2026-03-12T12:13:59Z

- Title: Add page-screenshot proxy and UI preview (include screenshots in /api/pulls)
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/71
- Author: evinaeva
- Base branch: main
- Head branch: 447ysg-codex/implement-screenshot-visualization-for-choose-needed
- Merge commit: f55ef4a039ca2001f83237fa993e2ca95075ae3d
- Changed files:
  - app/skeleton_server.py
  - tests/test_stage_a_read_routes_api.py
  - tests/test_stage_b_operator_flow_api.py
  - web/static/pulls.js
  - web/static/styles.css
  - web/templates/pulls.html
- Notes: Auto-generated from merged PR metadata.

## PR #72 — 2026-03-12T12:56:30Z

- Title: Add page-screenshot proxy, enrich /api/pulls with screenshot metadata, and preview UI
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/72
- Author: evinaeva
- Base branch: main
- Head branch: 7ysw7j-codex/implement-screenshot-visualization-for-choose-needed
- Merge commit: 20c631b28cc6eb176b2ba80d5851449a7fe267e1
- Changed files:
  - web/static/styles.css
- Notes: Auto-generated from merged PR metadata.
