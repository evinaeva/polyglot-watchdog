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

## PR #73 — 2026-03-12T13:13:06Z

- Title: Fix pulls preview bbox scaling using actual screenshot dimensions
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/73
- Author: evinaeva
- Base branch: main
- Head branch: h0kmtz-codex/find-cause-of-incorrect-bbox-positioning
- Merge commit: 6572a8351f551338069bca8640347591942cefa2
- Changed files:
  - tests/test_stage_c_operator_workflow.py
  - web/static/pulls.js
- Notes: Auto-generated from merged PR metadata.

## PR #74 — 2026-03-12T14:13:00Z

- Title: Add element-type whitelist for pulls UI and skip header-online dynamic counters in phase6
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/74
- Author: evinaeva
- Base branch: main
- Head branch: xtq56l-codex/implement-feature-set-for-choose-needed-page
- Merge commit: 88d5b63cd074cefe0e301631859b624a38bbe0e3
- Changed files:
  - app/skeleton_server.py
  - pipeline/run_phase6.py
  - tests/test_auth_flow.py
  - tests/test_phase6_schema_compliance.py
  - tests/test_stage_a_read_routes_api.py
  - tests/test_stage_c_operator_workflow.py
  - web/static/pulls.js
  - web/templates/pulls.html
- Notes: Auto-generated from merged PR metadata.

## PR #75 — 2026-03-12T14:42:06Z

- Title: Include PR description in merged feed and AI payload; ignore .github/tmp in validation
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/75
- Author: evinaeva
- Base branch: main
- Head branch: 2q0y4i-codex/fix-docs-auto-update-system-issues
- Merge commit: 0fb642d6eb8f40b92c1497cd8cfaa794a9aa7923
- Changed files:
  - .github/scripts/docs_ai_sync.py
  - .github/scripts/update_merged_pr_feed.py
  - .github/scripts/validate_docs_diff.py
  - tests/test_docs_autoupdate_scripts.py
- Notes: Auto-generated from merged PR metadata.

## PR #76 — 2026-03-12T14:57:18Z

- Title: Use element-signature whitelist (specific signatures) instead of simple element-type strings
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/76
- Author: evinaeva
- Base branch: main
- Head branch: 6b993u-codex/fix-broad-whitelist-implementation
- Merge commit: 79db262ae91c112ebae63567a6fadf58f81d62a3
- Changed files:
  - app/skeleton_server.py
  - tests/test_stage_a_read_routes_api.py
  - web/static/pulls.js
  - web/templates/pulls.html
- Notes: Auto-generated from merged PR metadata.

## PR #77 — 2026-03-13T06:47:05Z

- Title: Refactor Phase 6 into modular deterministic translation QA pipeline
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/77
- Author: evinaeva
- Base branch: main
- Head branch: mngqo2-codex/implement-phase-6-translation-qa-pipeline
- Merge commit: 1dd3302ad1e748d1dcc50302220ee7f5f260a309
- Changed files:
  - pipeline/phase6_providers.py
  - pipeline/phase6_review.py
  - pipeline/run_phase6.py
  - tests/test_phase6_review_pipeline.py
  - tests/test_phase6_schema_compliance.py
- Notes: Auto-generated from merged PR metadata.

## PR #78 — 2026-03-13T06:54:10Z

- Title: Fix Phase 6 dynamic counter normalization, missing-target evidence sourcing, and evidence signals
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/78
- Author: evinaeva
- Base branch: main
- Head branch: i6tccp-codex/fix-phase-6-review-pipeline-issues
- Merge commit: 4fa2d695e9f14bd781e97f164d528d5311c212e7
- Changed files:
  - pipeline/phase6_review.py
  - pipeline/run_phase6.py
  - tests/test_phase6_review_pipeline.py
  - tests/test_phase6_schema_compliance.py
- Notes: Auto-generated from merged PR metadata.

## PR #79 — 2026-03-13T07:07:12Z

- Title: Switch docs AI sync to strict patch-based updates
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/79
- Author: evinaeva
- Base branch: main
- Head branch: 4yjpr1-codex/change-ai-sync-to-use-patch-updates
- Merge commit: b2f00ef52c77ec9185f73b0a42caecacf69ab111
- Changed files:
  - .github/prompts/docs_sync_prompt.txt
  - .github/scripts/docs_ai_sync.py
  - tests/test_docs_autoupdate_scripts.py
- Notes: Auto-generated from merged PR metadata.

## PR #80 — 2026-03-13T07:19:26Z

- Title: Phase 6: Clarify persisted category vs evidence review_class semantics
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/80
- Author: evinaeva
- Base branch: main
- Head branch: ygmid6-codex/align-phase-6-contract-semantics
- Merge commit: 81488894993f6997421202e05628ce43cea649ee
- Changed files:
  - README.md
  - contract/schemas/issues.schema.json
  - docs/PHASE6_TRANSLATION_QA.md
  - docs/architecture.md
  - pipeline/phase6_review.py
  - pipeline/run_phase6.py
  - tests/test_phase6_schema_compliance.py
- Notes: Auto-generated from merged PR metadata.

## PR #83 — 2026-03-13T09:43:09Z

- Title: phase6: reuse one AI review result per EN-target-language pair
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/83
- Author: evinaeva
- Base branch: main
- Head branch: brbcq6-codex/fix-phase-6-ai-provider-inefficiency
- Merge commit: 4d952d47c7e4ee9c2c387856bee425b3bbebc4bc
- Changed files:
  - pipeline/phase6_providers.py
  - tests/test_phase6_providers.py
- Notes: Auto-generated from merged PR metadata.

## PR #84 — 2026-03-13T10:10:02Z

- Title: Fix docs workflows to use .github/scripts paths
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/84
- Author: evinaeva
- Base branch: main
- Head branch: em6bhr-codex/fix-github-actions-workflow-paths
- Merge commit: 62e74925112050d36f107a60cfe8fc5b80e9d624
- Changed files:
  - .github/scripts/check_schedule_sync.py
  - .github/scripts/config_loader.py
  - .github/scripts/docs_ai_sync.py
  - .github/scripts/update_merged_pr_feed.py
  - .github/scripts/validate_docs_diff.py
  - .github/workflows/docs-ai-sync.yml
- Notes: Auto-generated from merged PR metadata.

## PR #85 — 2026-03-13T10:33:47Z

- Title: Implement Phase 4 OCR (OCR.Space engine 3) and Phase 6 integration
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/85
- Author: evinaeva
- Base branch: main
- Head branch: ixj2os-codex/implement-phase-4-ocr-using-ocr.space-logic
- Merge commit: 49f7b7ff3d5f46c285a8c7cd59ff0de28fd0d718
- Changed files:
  - pipeline/phase4_ocr.py
  - pipeline/phase4_ocr_provider.py
  - pipeline/run_phase6.py
  - tests/test_phase4_ocr.py
- Notes: Auto-generated from merged PR metadata.

## PR #92 — 2026-03-13T12:09:13Z

- Title: fix: complete docs auto-update path migration to .github/scripts
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/92
- Author: evinaeva
- Base branch: main
- Head branch: tcnch7-codex/fix-path-migration-in-docs-auto-update-system
- Merge commit: e1f1f7b170abc12b11a92d0ffebf86d3271c92e2
- Changed files:
  - .github/docs_autoupdate/README.md
  - .github/scripts/check_schedule_sync.py
  - .github/scripts/config.json
  - .github/scripts/config_loader.py
  - .github/workflows/docs-ai-sync.yml
  - .github/workflows/docs-pr-feed.yml
  - tests/test_docs_autoupdate_scripts.py
- Description:
  ### Motivation
  - The docs auto-update subsystem was in a mixed state where workflows and scripts referenced both `.github/docs_autoupdate/` and `.github/scripts/`, causing a `FileNotFoundError` for the old config path. 
  - The goal was to converge onto a single canonical automation bundle location so workflows run reliably and preserved temporary execution has all required local dependencies. 
  - This change is strictly a path migration and stabilization to `.github/scripts/` without changing workflow triggers, branch strategy, or product behavior.
  
  ### Description
  - Moved the canonical config into `.github/scripts/config.json` and updated the shared loader default to point at `.github/scripts/config.json` while preserving the `DOCS_AUTOUPDATE_CONFIG` override mechanism. 
  - Updated `check_schedule_sync.py` to read the schedule from `.github/scripts/config.json` instead of the obsolete location. 
  - Updated both workflow YAML files (`.github/workflows/docs-pr-feed.yml` and `.github/workflows/docs-ai-sync.yml`) to load config from `.github/scripts/config.json` and to invoke scripts from `.github/scripts/...` only. 
  - Made the Docs PR Feed workflow preserve `update_merged_pr_feed.py`, `config_loader.py`, and `config.json` from `main` into the runner temp directory and export `DOCS_AUTOUPDATE_CONFIG` to that preserved config path so preserved execution has the needed files and imports work. 
  - Adjusted tests and README references to point to the canonical `.github/scripts/` paths so repository tests validate the migration.
  
  ### Testing
  - Ran `pytest -q tests/test_docs_autoupdate_scripts.py` and all tests passed (`19 passed`). 
  - Performed repository-wide searches to confirm workflows and scripts no longer reference `.github/docs_autoupdate/config.json` or `.github/docs_autoupdate/scripts/` and to verify the canonical path is `.github/scripts/`. 
  - Verified `check_schedule_sync.py`, `config_loader.py`, workflows, and preserved-temp execution logic resolve and use `.github/scripts/config.json` as intended.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69b3fc3e79e0832c99e4364f18b1c288)
- Notes: Auto-generated from merged PR metadata.
