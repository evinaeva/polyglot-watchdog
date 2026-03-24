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

## PR #91 — 2026-03-13T12:13:06Z

- Title: Calibrate OCR trust in Phase 6 image-backed review
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/91
- Author: evinaeva
- Base branch: main
- Head branch: sf2yfd-codex/implement-ocr-quality-calibration-in-phase-6
- Merge commit: a71d15d1f9de227939413b61a765dc859e082da1
- Changed files:
  - pipeline/phase6_review.py
  - pipeline/run_phase6.py
  - tests/test_phase6_review_pipeline.py
- Description:
  ### Motivation
  - Phase 6 was treating OCR-backed text like normal text and could emit overconfident meaning claims when OCR was weak, noisy, or ambiguous.
  - Introduce a compact, deterministic way to surface OCR quality signals so Phase 6 makes more conservative, explainable decisions for image-backed items without changing Phase 4, Phase 6 contracts, or top-level issue semantics.
  
  ### Description
  - Added a small OCR quality helper `_assess_ocr_quality` in `pipeline/phase6_review.py` that computes simple signals/flags (e.g. `ocr_missing_text`, `ocr_too_short_absolute`, `ocr_symbol_heavy`, `ocr_low_alnum`, `ocr_fragmented_tokens`, `ocr_repeated_chars`, `ocr_provider_uncertainty`) and buckets trust into `good`/`borderline`/`weak` with a deterministic `trust_score` and `confidence_adjustment`.
  - Adjusted Phase 6 review logic so OCR-backed image items use these signals: `weak` OCR suppresses strong `MEANING` mismatch claims, `borderline` OCR reduces confidence, and `OCR_NOISE` issues are emitted with enriched uncertainty evidence when appropriate.
  - Enriched evidence backward-compatibly: `evidence.signals` may include `ocr_confidence_adjustment` and metric signals, and `evidence.ocr_quality` (optional) contains `trust_bucket`, `trust_score`, and `flags`; existing evidence fields and external `issues.json` contract remain unchanged.
  - Propagated minimal Phase 4 handoff metadata in `pipeline/run_phase6.py` to Phase 6 items when present (`ocr_engine`, `ocr_notes`) while keeping OCR scope limited to approved image-backed items.
  - Added focused unit tests in `tests/test_phase6_review_pipeline.py` to cover good vs weak OCR behavior, suppression of meaning claims for noisy OCR, nearly-empty OCR handling, OCR evidence presence, and to ensure non-image items are unaffected.
  
  ### Testing
  - Added/updated tests covering: good OCR path still allows normal meaning review (`test_good_ocr_allows_normal_meaning_review_for_image_items`), noisy OCR suppresses meaning claims and emits `OCR_NOISE` with `ocr_quality` (`test_weak_ocr_suppresses_strong_meaning_claims_and_adds_quality_evidence`), nearly-empty OCR treated as weak (`test_nearly_empty_ocr_text_is_treated_as_weak_quality_noise`), and other existing Phase 4/6 behaviors.
  - Test command run: `PYTHONPATH=. pytest -q tests/test_phase6_review_pipeline.py tests/test_phase4_ocr.py`.
  - Test results: all tests passed (`26 passed`).
  - Confirmations: no changes to `issues.json` schema or top-level category semantics, no OCR scope expansion beyond approved image-backed handoff, and no Phase 4 or provider architecture redesign were introduced.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69b3fba3ec80832c82595026cb8a574e)
- Notes: Auto-generated from merged PR metadata.

## PR #93 — 2026-03-13T12:24:35Z

- Title: fix(actions): restore docs auto-update workflows after script relocation
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/93
- Author: evinaeva
- Base branch: main
- Head branch: kcs5ey-codex/investigate-actions-failure-after-script-relocation
- Merge commit: 986e1826a4cfd015b2cea044351fbdaeb20006a8
- Changed files:
  - .github/scripts/check_schedule_sync.py
  - .github/workflows/docs-ai-sync.yml
  - .github/workflows/docs-pr-feed.yml
- Description:
  ### Motivation
  - Workflows failed after the docs auto-update scripts/config were moved because the YAMLs used hardcoded paths like `.github/scripts/...` and could not find `config.json` or the Python scripts. 
  - The intent is to make the workflows resilient to relocating the auxiliary scripts/config without requiring manual edits to each workflow. 
  
  ### Description
  - Added a script-discovery step to both workflows that searches candidate dirs (`.github/scripts`, `.github/docs_autoupdate/scripts`, `scripts/docs_autoupdate`) and exports `DOCS_AUTOUPDATE_SCRIPT_DIR` and `DOCS_AUTOUPDATE_CONFIG` when found. 
  - Replaced hardcoded references to `.github/scripts/...` in `docs-ai-sync.yml` with dynamic invocations using `DOCS_AUTOUPDATE_SCRIPT_DIR` for config loading, `check_schedule_sync.py`, `docs_ai_sync.py`, and `validate_docs_diff.py`. 
  - Updated `docs-pr-feed.yml` to use the discovered script dir and `DOCS_AUTOUPDATE_CONFIG` when copying feed-writer scripts into the runner temp directory and when loading config values. 
  - Modified `check_schedule_sync.py` to call `load_config()` from `config_loader` (so it respects `DOCS_AUTOUPDATE_CONFIG` / relocated config) instead of reading a fixed path. 
  
  ### Testing
  - Ran `python -m py_compile .github/scripts/check_schedule_sync.py` and it succeeded. 
  - Executed `python .github/scripts/check_schedule_sync.py` to verify config loading and cron check and it succeeded. 
  - Parsed both workflow YAMLs with `ruby -e 'require "yaml"; YAML.load_file(...)'` to ensure valid syntax and the changes passed validation.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69b40066a248832c92e92cd39e1093a4)
- Notes: Auto-generated from merged PR metadata.

## PR #94 — 2026-03-13T12:33:22Z

- Title: Support locating docs auto-update scripts directory, use config_loader, and ignore bytecode files
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/94
- Author: evinaeva
- Base branch: main
- Head branch: qo5y1b-codex/investigate-actions-failure-after-script-relocation
- Merge commit: 0cbd20d1965e7e1ace1ed288e5e4234e0ba1a969
- Changed files:
  - .github/scripts/check_schedule_sync.py
  - .github/scripts/validate_docs_diff.py
  - .github/workflows/docs-ai-sync.yml
  - .github/workflows/docs-pr-feed.yml
- Description:
  ### Motivation
  
  - Centralize config loading and make the docs auto-update scripts relocatable so workflows can run the scripts from multiple possible paths. 
  - Prevent runtime noise from Python bytecode artifacts during allowed/ignored path checks. 
  - Ensure workflows avoid writing .pyc files by setting `PYTHONDONTWRITEBYTECODE` in runners.
  
  ### Description
  
  - Replaced direct JSON parsing with `load_config` from `config_loader` in `check_schedule_sync.py` to reuse the shared config loader. 
  - Enhanced `validate_docs_diff.py` to treat `__pycache__` directories and `.pyc/.pyo` filenames as ignored runtime artifacts by adding `IGNORED_RUNTIME_SUFFIXES` and updating `is_ignored_runtime_path`. 
  - Updated `docs-ai-sync.yml` and `docs-pr-feed.yml` to discover the docs auto-update scripts directory at runtime, export `DOCS_AUTOUPDATE_SCRIPT_DIR` and `DOCS_AUTOUPDATE_CONFIG`, set `PYTHONDONTWRITEBYTECODE: "1"`, and invoke scripts via the discovered directory (e.g. `python "$DOCS_AUTOUPDATE_SCRIPT_DIR/docs_ai_sync.py"`). 
  - In `docs-pr-feed.yml` preserved the feed writer scripts by copying them from the discovered directory into a temporary scripts directory and added that directory to `PYTHONPATH` for execution.
  
  ### Testing
  
  - No repository automated tests were modified and no automated test runs are included in this change.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69b40066a248832c92e92cd39e1093a4)
- Notes: Auto-generated from merged PR metadata.

## PR #98 — 2026-03-16T08:33:12Z

- Title: Add Check Languages UI and backend handlers (phase-6 readiness and job start)
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/98
- Author: evinaeva
- Base branch: main
- Head branch: 23bjsl-codex/add-/check-languages-workflow-implementation
- Merge commit: 37ed04bd7bb1c5d71b70e14201a2b326e0558288
- Changed files:
  - app/skeleton_server.py
  - tests/test_check_languages_page.py
  - web/templates/check-languages.html
- Description:
  ### Motivation
  
  - Provide an interactive "Check Languages" page to run phase-six language checks comparing a target run against an English reference and to surface readiness, job status, and issue summaries.
  - Validate prerequisites (artifacts like `page_screenshots.json`, `collected_items.json`, `eligible_dataset.json`) before queuing phase-6 work and prevent duplicate concurrent jobs.
  
  ### Description
  
  - Added server-side support for a new `/check-languages` route with GET and POST handling and CSRF-aware redirects via `_serve_check_languages_page`, `_start_check_languages`, and `_redirect_check_languages`.
  - Implemented helpers for artifact readiness and run language detection: `_phase6_artifact_readiness`, `_run_languages`, `_load_check_language_runs`, `_latest_phase6_job`, `_summarize_issues_payload`, `_format_summary_pairs`, and an HTML-escaping helper `_h` (and imported `html`).
  - Started jobs by upserting job status via `_upsert_job_status` and launching `_run_phase6_async` in a background thread, and prevented starting when prerequisites are missing or when a phase-6 job is already `running`/`queued`.
  - Added a new template `web/templates/check-languages.html` to present notices, selection controls, readiness details, job status, and issue summaries, and wired it into the main page routing.
  - Introduced comprehensive functional tests in `tests/test_check_languages_page.py` that exercise rendering, validation, readiness checks, starting the async job, and summary/stale-summary behavior using a fake storage client.
  
  ### Testing
  
  - Ran `pytest tests/test_check_languages_page.py` which starts a `ThreadingHTTPServer` against `SkeletonHandler` and uses a fake GCS client; all tests in the file passed.
  - The new tests cover GET rendering, input validation, refusal to start when prerequisites are missing, successful POST start behavior that queues a phase-6 job, and issue-summary/stale-summary states; these cases succeeded.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69b7b79f98b0832cb2a950b10f7527fb)
- Notes: Auto-generated from merged PR metadata.

## PR #99 — 2026-03-16T09:48:51Z

- Title: Orchestrate composed "check languages" workflow and update UI/tests
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/99
- Author: evinaeva
- Base branch: main
- Head branch: cwj2jd-codex/refactor-/check-languages-for-operator-workflow
- Merge commit: a1f3d52c3a044200eef33686b397edd5b035eecd
- Changed files:
  - app/skeleton_server.py
  - tests/test_check_languages_page.py
  - web/templates/check-languages.html
- Description:
  ### Motivation
  - Replace the previous approach of selecting an existing target run with a composed workflow that generates a target-language capture from an English reference and then runs comparison phases automatically.
  - Provide safer guards and clearer status reporting for in-progress composed checks and avoid re-running duplicate checks.
  - Surface the new orchestration status and generated target run in the UI and make the page input model simpler (choose English reference + target language).
  
  ### Description
  - Added helpers to determine available non-English `target` languages (`_load_target_languages`), to detect English-only runs (`_run_is_english_only`), to generate a unique target run id (`_generate_target_run_id`), to find in-progress composed jobs (`_find_in_progress_check_languages_job`), and to fetch the latest check-languages job for a run (`_latest_check_languages_job`).
  - Implemented `_replay_scope_from_reference_run` which builds a list of exact-context jobs from an English reference run using `pipeline.run_phase1.build_exact_context_job`.
  - Added `_run_check_languages_async` orchestration that (1) prepares the target run, (2) runs the target capture via `pipeline.run_phase1.main` (using `asyncio.run`), and (3) runs comparison phases (`phase3` and `phase6`) while updating job status and error handling through `_upsert_job_status`.
  - Updated request handlers to accept `target_language` instead of an existing target `run_id`, to validate inputs (English-only requirement for reference, non-English requirement for target), to prevent duplicate in-progress checks, to queue a new `check_languages` job record, and to redirect with the generated `target_run_id`.
  - Modified the check-languages template to remove target-run selection, add a `target_language` select, and show `target_language` and the generated `target_run_id` in the state block.
  - Updated and extended `tests/test_check_languages_page.py` to reflect the new input model and orchestrator behavior, and added unit tests for the replay helper and orchestration failure/success paths.
  
  ### Testing
  - Ran the test module `tests/test_check_languages_page.py` which was updated to exercise the new flows, including input validation, duplicate-guarding, queued/completed states, replay-scope generation, and orchestrator error handling; all tests in the file passed locally.
  - Existing storage fakes and monkeypatches are used in tests to simulate artifacts and to stub `pipeline.run_phase1/main`, `pipeline.run_phase3.run`, and `pipeline.run_phase6.run` during orchestration unit tests, and those scenarios succeeded.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69b7ca6bff7c832cb8f30fd792cd5f50)
- Notes: Auto-generated from merged PR metadata.

## PR #100 — 2026-03-24T13:39:07Z

- Title: Add optional run display_name handling and UI formatting for workflow runs
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/100
- Author: evinaeva
- Base branch: main
- Head branch: 5hf1d7-codex/add-display-name-to-run-metadata
- Merge commit: 1cc1701e7d27f82a38790e940d9346594e945eca
- Changed files:
  - app/skeleton_server.py
  - web/static/workflow.js
- Description:
  ### Motivation
  
  - Make it possible to attach, persist and display a human-friendly `display_name` for capture runs when starting or listing runs in the workflow. 
  - Ensure the UI presents readable run labels and hides placeholder values like `null`/`none` while keeping run IDs available.
  
  ### Description
  
  - Added `_default_run_display_name()` to produce a default display name and updated `/api/workflow/start-capture` to accept a `display_name` payload, prefer an existing display name for an existing run, and use a default for a new run when requested name is explicitly `null`/`none`.
  - Updated `_upsert_job_status()` to propagate a run-level `display_name` (normalized via `_normalize_optional_string`) while removing `display_name` from individual job records saved under `jobs`.
  - Normalized the `/api/capture/runs` response to always include a normalized `display_name` per run in the returned JSON.
  - Frontend changes in `web/static/workflow.js` add `normalizeDisplayName()` and `formatRunLabel()` and use them to render run labels in the status summary and the existing-runs dropdown, falling back to the run ID when no human name exists.
  
  ### Testing
  
  - No automated tests were run for these changes.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c28fae4be8832ca26e3352db222c50)
- Notes: Auto-generated from merged PR metadata.

## PR #101 — 2026-03-24T13:39:23Z

- Title: Add capture review helper and integrate contexts review into Workflow UI
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/101
- Author: evinaeva
- Base branch: main
- Head branch: e66t9p-codex/update-workflow.html-and-workflow.js
- Merge commit: d063d46928064d76e612494c31d8a8a45b28a6ef
- Changed files:
  - web/static/capture-review.js
  - web/static/contexts.js
  - web/static/workflow.js
  - web/templates/contexts.html
  - web/templates/workflow.html
- Description:
  ### Motivation
  - Provide a reusable client-side function to post capture context reviews and enable reviewing capture contexts directly from the Workflow hub UI.
  - Reduce duplicated review-posting code by centralizing the payload construction and POST logic in a single module.
  
  ### Description
  - Add a new module `web/static/capture-review.js` which implements `buildCaptureReviewPayload` and `postCaptureReview` for sending reviews to `POST /api/capture/reviews`.
  - Refactor `web/static/contexts.js` to remove the inline `saveReview` implementation and call the shared `postCaptureReview` instead.
  - Extend `web/static/workflow.js` to render a contexts review table inside the Workflow page, including `setContextsStatus`, `renderContextsRows`, and `loadContexts`, and to call `loadContexts` when workflow status is refreshed.
  - Update templates `web/templates/contexts.html` and `web/templates/workflow.html` to include the new script `web/static/capture-review.js` and add the contexts status/table markup to the Workflow page, plus minor heading reorganizations.
  
  ### Testing
  - No automated tests were run for this change.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c28fc9af90832cb5ecab142bbf00a7)
- Notes: Auto-generated from merged PR metadata.

## PR #102 — 2026-03-24T13:39:38Z

- Title: Default pull decision to 'eligible' when decision is unset
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/102
- Author: evinaeva
- Base branch: main
- Head branch: 1msvb8-codex/update-renderrows-default-decision-value
- Merge commit: cedf5a3af2a86a0760c22db33b27f6d94407ec33
- Changed files:
  - web/static/pulls.js
- Description:
  ### Motivation
  - Ensure rows with no recorded decision render with a sensible default so the UI presents a usable initial selection instead of an empty choice.
  
  ### Description
  - Use `decisionToValue(row.decision) || 'eligible'` when building the row controls so missing decisions default to `eligible` (Keep).
  
  ### Testing
  - Ran frontend lint with `npm run lint` and unit tests with `npm test`, and executed a local build with `npm run build`, all of which completed successfully.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c28fd07bc0832ca89656ad1312beb7)
- Notes: Auto-generated from merged PR metadata.

## PR #105 — 2026-03-24T13:40:10Z

- Title: Canonicalize target languages and normalize aliases for language checks
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/105
- Author: evinaeva
- Base branch: main
- Head branch: 40r8b1-codex/update-target-language-handling-in-skeleton_server
- Merge commit: 6a59e5178ce1a37a1b2caa27b09e3716ef35fdb7
- Changed files:
  - app/skeleton_server.py
- Description:
  ### Motivation
  - Ensure consistent handling of target languages across the check-languages workflow by using a canonical language list instead of ad-hoc environment parsing. 
  - Accept common country-code aliases (e.g. `cz`, `jp`, `kr`) and normalize them to stable language codes. 
  - Prevent mismatches when comparing or selecting target languages in job queries, redirects, and UI flows.
  
  ### Description
  - Introduced `CANONICAL_TARGET_LANGUAGES` constant containing the supported target language codes and `TARGET_LANGUAGE_ALIASES` mapping for common aliases. 
  - Added `_normalize_target_language(value)` helper to normalize input and apply aliases. 
  - Replaced the previous environment-driven `_load_target_languages` implementation with a function that returns the canonical non-English target list. 
  - Updated language comparisons and query/redirect handling to use `_normalize_target_language` in `_find_in_progress_check_languages_job`, `_redirect_check_languages`, `_start_check_languages`, and `_serve_check_languages_page`.
  
  ### Testing
  - No automated tests were run as part of this rollout.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c28fd52b1c832c8c34e224a83da821)
- Notes: Auto-generated from merged PR metadata.

## PR #103 — 2026-03-24T13:40:29Z

- Title: Add 'Prepare captured data' button to pulls page
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/103
- Author: evinaeva
- Base branch: main
- Head branch: ritipd-codex/update-pulls.html-and-pulls.js-with-new-button
- Merge commit: 87a2bb90a1179e4d894dd1f8c2780d147a41b89b
- Changed files:
  - web/static/pulls.js
  - web/templates/pulls.html
- Description:
  ### Motivation
  - Provide a manual UI action on the pulls review page to trigger eligible-dataset generation for the current workflow run using the existing backend endpoint. 
  - Surface immediate plain-text feedback for success/failure so operators can see the result of the action without changing existing workflow phase logic.
  
  ### Description
  - Added a `Prepare captured data` button and a status paragraph directly under `#pullsTable` in `web/templates/pulls.html`.
  - Wired new DOM references and a small status helper (`setPrepareCapturedDataStatus`) into `web/static/pulls.js` and implemented a click handler that posts `{ domain, run_id }` to the existing endpoint `/api/workflow/generate-eligible-dataset` using the same contract as other workflow actions.
  - The button remains enabled at all times (no change-tracking gating) and the implementation reuses `safeReadPayload` for response handling and does not duplicate any backend phase logic.
  
  ### Testing
  - Ran `node --check web/static/pulls.js` to validate the JS syntax; it succeeded.
  - Reviewed the diff and file placements with `git diff`/file previews to confirm the UI and handler were added to `web/templates/pulls.html` and `web/static/pulls.js` as intended.
  - Committed the changes locally after verification (`git commit`).
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c28fd2ab84832cb70795bb251be43b)
- Notes: Auto-generated from merged PR metadata.

## PR #104 — 2026-03-24T13:41:00Z

- Title: Auto-select latest successful English standard run and surface run metadata in check-languages UI
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/104
- Author: evinaeva
- Base branch: main
- Head branch: bnxbqi-codex/add-helper-for-latest-successful-en-run
- Merge commit: d4ebb85d6c3e9feb737c7322114e2e716708226b
- Changed files:
  - app/skeleton_server.py
  - tests/test_check_languages_page.py
- Description:
  ### Motivation
  
  - Improve the check-languages page by automatically choosing a sensible English reference run when the user does not pick one and by showing human-friendly labels from run metadata.
  
  ### Description
  
  - Include run `metadata` in the output of `_load_check_language_runs` to surface fields like `display_label` and `en_standard_status`.
  - Add `_run_display_label` to prefer `metadata.display_label` or `metadata.display_name` when rendering English run options in the dropdown, falling back to `run_id` when absent.
  - Add `_run_has_en_standard_success_marker` and `_latest_successful_en_standard_run_id` to detect an English run that is either phase6-ready or marked successful via metadata (e.g. `en_standard_status: "succeeded"`) and auto-select the latest such run when none is provided by the query.
  - Change page logic to distinguish between an explicitly provided `en_run_id` and an auto-selected one, so the UI does not mistakably require a target language when the English run was auto-selected.
  
  ### Testing
  
  - Added tests `test_get_check_languages_auto_selects_latest_successful_english_standard`, `test_get_check_languages_auto_selects_en_standard_success_marker_when_not_ready`, `test_get_check_languages_en_option_uses_metadata_display_label`, and `test_get_check_languages_en_option_uses_metadata_display_name` to verify auto-selection and label behavior.
  - Ran `pytest tests/test_check_languages_page.py` and the test suite for the modified behavior succeeded.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c28fd50698832c9f938afcb080d1c4)
- Notes: Auto-generated from merged PR metadata.

## PR #106 — 2026-03-24T13:42:26Z

- Title: Add eligible-dataset generation UI and Phase 3 metadata tracking
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/106
- Author: evinaeva
- Base branch: main
- Head branch: faw8tx-codex/add-metadata-fields-and-status-handling
- Merge commit: 2b02dac28415859f867545fe38544b4cebf4d6a1
- Changed files:
  - app/skeleton_server.py
  - web/static/pulls.js
- Description:
  ### Motivation
  
  - Surface Phase 3 eligible-dataset generation status and allow users to trigger generation from the pulls UI. 
  - Persist an `en_standard_display_name` produced during Phase 3 to run metadata so the UI can label generated datasets. 
  - Expose generation readiness, status, and errors in the workflow status API to enable polling and user feedback.
  
  ### Description
  
  - Added `_latest_phase3_job` to select the most recent Phase 3 job and reused stale-running job normalization logic. 
  - Introduced `_en_standard_display_name_today` and `_upsert_run_metadata` helpers and updated `_run_phase3_async` to require the `eligible_dataset.json` artifact, capture an `en_standard_display_name`, and upsert run metadata while also recording job success/failure via `_upsert_job_status`. 
  - Extended `_workflow_status_payload` to include `run.en_standard_display_name` and expanded the `eligible_dataset` section with `ready`, `en_standard_display_name`, `generation_status`, and `generation_error` fields. 
  - Implemented front-end controls and logic in `web/static/pulls.js` to render a "Generate eligible dataset" button, POST to `/api/workflow/generate-eligible-dataset`, poll `/api/workflow/status` with `waitForEligibleDatasetReady`, and surface generation messages/errors to the user.
  
  ### Testing
  
  - No automated tests were added or executed as part of this rollout; recommend running the existing test suite with `pytest` and verifying the front-end build and UI flows.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c28fd4216c832caaea4d621f8af9ff)
- Notes: Auto-generated from merged PR metadata.

## PR #107 — 2026-03-24T14:14:00Z

- Title: Add language:auto to OCR.space payload and raise timeout default to 40s
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/107
- Author: evinaeva
- Base branch: main
- Head branch: dl85je-codex/update-ocrspace_extract_text-payload
- Merge commit: b24c8672b181352148589ddd84b1d4f773012b7d
- Changed files:
  - pipeline/phase4_ocr_provider.py
- Description:
  ### Motivation
  - Improve OCR accuracy by allowing OCR.space to auto-detect the input language via the `language` parameter.
  - Reduce spurious timeouts for slower OCR requests by increasing the default timeout from 20s to 40s while preserving the existing env var override behavior.
  
  ### Description
  - Change the default timeout expression from `os.getenv("OCR_SPACE_TIMEOUT_S", "20")` to `os.getenv("OCR_SPACE_TIMEOUT_S", "40")`.
  - Add `
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c297142fa0832cb62230c47ed03beb)
- Notes: Auto-generated from merged PR metadata.

## PR #108 — 2026-03-24T14:24:17Z

- Title: Add language:auto to OCR.space payload and raise timeout default to 40s
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/108
- Author: evinaeva
- Base branch: main
- Head branch: f37lw1-codex/update-ocrspace_extract_text-payload
- Merge commit: 8da3142193093ab867da36ff7e09d8da53c4081d
- Changed files:
  - pipeline/phase4_ocr_provider.py
- Description:
  ### Motivation
  - Improve OCR accuracy by allowing OCR.space to auto-detect the input language via the `language` parameter.
  - Reduce spurious timeouts for slower OCR requests by increasing the default timeout from 20s to 40s while preserving the existing env var override behavior.
  
  ### Description
  - Change the default timeout expression from `os.getenv("OCR_SPACE_TIMEOUT_S", "20")` to `os.getenv("OCR_SPACE_TIMEOUT_S", "40")`.
  - Add `
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c297142fa0832cb62230c47ed03beb)
- Notes: Auto-generated from merged PR metadata.

## PR #114 — 2026-03-24T14:24:27Z

- Title: Add 'Prepare captured data' button and status handling for eligible dataset generation
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/114
- Author: evinaeva
- Base branch: main
- Head branch: fz6wwx-codex/add-captured-data-preparation-functions
- Merge commit: 9df69d41bda3c188e599ec740c5a32959484140f
- Changed files:
  - web/static/pulls.js
- Description:
  ### Motivation
  - Provide a UI control to trigger preparation of captured data for downstream eligible-dataset generation from the pulls view.
  - Surface progress and error information to the user when calling the server-side workflow endpoint.
  
  ### Description
  - Added DOM hooks for the new controls: `pullsPrepareCapturedData` and `pullsPrepareCapturedDataStatus`.
  - Implemented `setPrepareCapturedDataStatus` to update the status element text and class.
  - Added a click handler on `pullsPrepareCapturedData` that posts to `/api/workflow/generate-eligible-dataset` with `{ domain, run_id }` and updates the status on success or failure.
  - Improved error handling for the fetch response by setting the status message on non-OK responses instead of throwing directly.
  
  ### Testing
  - No automated tests were run for this change.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c297293574832c9dd4d5cdb090da8e)
- Notes: Auto-generated from merged PR metadata.

## PR #116 — 2026-03-24T14:24:47Z

- Title: Validate and sanitize run_id across HTTP endpoints
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/116
- Author: evinaeva
- Base branch: main
- Head branch: 73p8qz-codex/add-helper-for-run_id-validation
- Merge commit: efa97c9eb92bffe79e1627ecfefce0d1a41bebd6
- Changed files:
  - app/skeleton_server.py
- Description:
  ### Motivation
  - Ensure `run_id` values are normalized and safe to use as file/storage keys to prevent path-traversal and control-character issues.
  - Centralize `run_id` validation to produce consistent 400 responses for invalid identifiers.
  - Harden several API endpoints that accept `run_id` (query or payload) to avoid downstream errors caused by malformed IDs.
  
  ### Description
  - Added a new helper function `
  _validate_run_id
  ` that trims the input and rejects empty strings, path-like segments (`/`, `\`, `..`) and control characters.
  - Integrated `
  _validate_run_id
  ` across many request handlers and payload parsers including `
  _parse_rerun_payload
  `, `/api/page-screenshot`, `/api/pulls`, `/api/rules` (GET and POST flows), `/api/issues`, `/api/issues/detail`, capture context/review endpoints, workflow endpoints (`/api/workflow/status`, `/api/phase0/run`, `/api/phase1/run`, `/api/phase3/run`, `/api/workflow/start-capture`, `/api/workflow/generate-issues`, `/api/workflow/generate-eligible-dataset`, etc.), and the check-languages flow to validate `en_run_id`.
  - Adjusted error handling so validation failures return `400` with an explanatory `error` message; preserved `artifact_invalid`/internal server error paths for other failures.
  - Special-case change in `/api/rules` GET error handling to return `400` when the `run_id` validation fails and keep `artifact_invalid` for other `ValueError` causes.
  
  ### Testing
  - Ran the existing unit test suite with `pytest -q`, and all tests completed successfully.
  - Ran the project's automated test run that covers request handling to ensure endpoints return `400` for malformed `run_id` values and unchanged behavior for valid IDs.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c2972a6384832cb6371b8cbbb4d199)
- Notes: Auto-generated from merged PR metadata.

## PR #115 — 2026-03-24T14:25:00Z

- Title: Prefer en_standard_display_name and normalize run display fields
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/115
- Author: evinaeva
- Base branch: main
- Head branch: bmnrq1-codex/update-option-labels-for-runs
- Merge commit: f911cfd6ddbdffe5f6ac929e02e49b4a2b73972f
- Changed files:
  - app/skeleton_server.py
- Description:
  ### Motivation
  - Ensure run listing and display label resolution prefer normalized display names and the English-standard display name when present.
  - Surface top-level `display_name` and `en_standard_display_name` in run summaries for downstream UI/logic.
  - Improve robustness by normalizing optional string fields and falling back to `run_id` when no display name exists.
  
  ### Description
  - Added `display_name` and `en_standard_display_name` to the objects returned by `_load_check_language_runs` using `_normalize_optional_string` and defaulting to an empty string when missing. 
  - Updated `_run_display_label` to build a display label by preferring `en_standard_display_name`, then `display_label`, then `display_name` from the run itself before checking metadata, and normalize all optional string sources via `_normalize_optional_string`.
  - Preserved the previous fallback behavior to return `run_id` when no other display value is available, and added a defensive `isinstance(run, dict)` check prior to reading top-level fields.
  
  ### Testing
  - Ran the project's unit test suite with `pytest -q`, and all tests completed successfully. 
  - Ran a quick smoke check of run list generation and label resolution for runs with combinations of top-level and metadata display fields, and observed expected label selection behavior.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c297299d94832c9ee20cda9f592f56)
- Notes: Auto-generated from merged PR metadata.

## PR #111 — 2026-03-24T14:25:14Z

- Title: Add Google Vision fallback and update OCR schema/metadata
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/111
- Author: evinaeva
- Base branch: main
- Head branch: 6s0yfd-codex/enhance-fallback-metadata-handling
- Merge commit: e2d60a13eede976094aee8be9ea81965d7af1a3a
- Changed files:
  - contract/schemas/phase4_ocr.schema.json
  - pipeline/phase4_ocr.py
  - pipeline/phase4_ocr_provider.py
  - tests/test_phase4_ocr.py
- Description:
  ### Motivation
  - Provide a resilient OCR pipeline by using Google Vision as a fallback when OCR.Space is unavailable or fails, and surface concise, deterministic metadata about primary and fallback attempts.
  - Broaden the contract shape so phase4 OCR rows can record multiple providers and non-numeric engine identifiers.
  
  ### Description
  - Updated the phase4 OCR JSON schema to allow `ocr_provider` to be either `ocr.space` or `google_vision` and relaxed `ocr_engine` to accept any non-empty string instead of a fixed value.
  - Replaced direct calls to the OCR.Space extractor with a new `extract_text_with_ocrspace_fallback` orchestrator in `pipeline/phase4_ocr.py` and updated the run manifest to record `primary_provider` and `fallback_provider` information.
  - Implemented `google_vision_extract_text`, a Google Vision request helper, `_default_google_request`, and `_short_error_from_meta` in `pipeline/phase4_ocr_provider.py`, and added `extract_text_with_ocrspace_fallback` which attempts OCR.Space first and then Google Vision, merging notes and concise error summaries into `provider_meta`.
  - Added and updated unit tests in `tests/test_phase4_ocr.py` to cover fallback success, fallback failure metadata, short error summaries, and schema acceptance of Google Vision rows.
  
  ### Testing
  - Ran the updated unit tests in `tests/test_phase4_ocr.py` (including new fallback tests) using `pytest`, and all tests passed.
  - Validated phase4 OCR rows against the updated JSON schema via the test suite, and schema validations succeeded.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c297173018832ca3d489c96e231b15)
- Notes: Auto-generated from merged PR metadata.
