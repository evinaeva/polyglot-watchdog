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

## PR #109 — 2026-03-24T14:26:36Z

- Title: Add Google Vision fallback to OCR.space extraction and improve response handling
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/109
- Author: evinaeva
- Base branch: main
- Head branch: p7s0bq-codex/implement-two-step-ocr-provider-flow
- Merge commit: 79c6e024704c4e0ffba79ccd346b5a334e43ca7f
- Changed files:
  - pipeline/phase4_ocr_provider.py
  - tests/test_phase4_ocr.py
- Description:
  ### Motivation
  
  - Make OCR extraction more robust by falling back to Google Vision when OCR.space is unavailable, yields empty text, or returns malformed responses.
  - Normalize and validate extracted text so whitespace-only results are treated as unusable.
  - Preserve and expose provider metadata and notes to aid debugging when fallback behavior occurs.
  
  ### Description
  
  - Introduce `GOOGLE_VISION_ENGINE_DEFAULT` and a new `_is_usable_text` helper to determine whether OCR output contains real text.
  - Factor the original OCR.space logic into `_ocrspace_extract_text` and add `_google_vision_extract_text` which wraps `google.cloud.vision` and accepts a `vision_client_factory` for testability.
  - Replace `ocrspace_extract_text` with a coordinator that calls the primary OCR.space extractor and, on failure or empty output, attempts Google Vision and merges provider metadata and notes to indicate fallback usage.
  - Update tests in `tests/test_phase4_ocr.py` to add fake vision client/response classes and new tests covering missing API key, malformed responses, successful primary results, and fallback behavior.
  
  ### Testing
  
  - Ran unit tests with `pytest tests/test_phase4_ocr.py` which exercised `test_ocrspace_request_path_with_engine3_and_base64`, `test_ocrspace_missing_key_and_malformed_response_are_non_fatal`, `test_ocrspace_success_keeps_primary_provider`, and `test_ocrspace_empty_text_falls_back_to_google_vision`, and they all passed.
  - The updated OCR extraction tests validate primary success, fallback success, and combined metadata/notes for failure cases.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c297151d34832c9aa9e1ee8334fb5b)
- Notes: Auto-generated from merged PR metadata.

## PR #113 — 2026-03-24T14:27:06Z

- Title: Consolidate eligible dataset generation to template button
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/113
- Author: evinaeva
- Base branch: main
- Head branch: 9kfe1z-codex/remove-one-control-path-in-pulls.js
- Merge commit: 7f34c47c252996101b9d1bb05e71cf3f5c48447e
- Changed files:
  - web/static/pulls.js
- Description:
  ### Motivation
  - Remove a duplicated UX path and duplicated trigger code so there is a single, predictable way to start eligible-dataset generation and observe status. 
  - Reuse the existing readiness-polling and status messaging utilities so generation state is centralized and not repeated in two places.
  
  ### Description
  - Replaced the injected dynamic controls with references to the template elements `#pullsPrepareCapturedData` and `#pullsPrepareCapturedDataStatus` and removed the created nodes. 
  - Deleted `ensureEligibleDatasetControls()` and its invocation so the page no longer inserts a second "Generate eligible dataset" control. 
  - Removed the duplicate bottom-of-file `pullsPrepareCapturedData` click handler that independently POSTed to `/api/workflow/generate-eligible-dataset`. 
  - Wired the template button into the existing `triggerEligibleDatasetGeneration()` + `waitForEligibleDatasetReady()` flow so polling and status messages are shared. 
  
  ### Testing
  - Ran `node --check web/static/pulls.js` which completed without errors.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c297288a50832c82a05c3af5575bb0)
- Notes: Auto-generated from merged PR metadata.

## PR #110 — 2026-03-24T14:27:52Z

- Title: Add Google Vision fallback for ocr.space failures
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/110
- Author: evinaeva
- Base branch: main
- Head branch: zj5hiu-codex/locate-google-vision-ocr-implementation
- Merge commit: a43176b695cf2c16a88d949d52679f4f4c34c0c0
- Changed files:
  - pipeline/phase4_ocr_provider.py
  - tests/test_phase4_ocr.py
- Description:
  ### Motivation
  
  - Reduce failed OCR outcomes when `ocr.space` is unavailable, returns malformed responses, or produces empty text by attempting a fallback to Google Vision.
  
  ### Description
  
  - Added a lightweight Google Vision integration with `_google_client`, `_parse_google_text`, and `_googlevision_extract_text` to request and parse text from Google Vision.
  - Introduced `_fallback_to_google_if_needed` and wired fallback logic into `ocrspace_extract_text` for missing API key, request failures, malformed responses, processing errors, and empty text outcomes so that a successful Google result can replace an unusable `ocr.space` result while preserving provider metadata.
  - Added a cached global `_GOOGLE_VISION_CLIENT` and a `_sanitize_ocr_text` normalization step is reused for Google responses.
  - Updated tests in `tests/test_phase4_ocr.py` to cover successful fallback and preservation of original failure metadata when the Google fallback also fails.
  
  ### Testing
  
  - Ran the `tests/test_phase4_ocr.py` unit tests including the new `test_ocrspace_falls_back_to_google_on_non_usable_outcome` and `test_ocrspace_preserves_original_failure_when_google_fallback_fails` tests, and they passed.
  - Existing OCR request-path test `test_ocrspace_request_path_with_engine3_and_base64` and `test_ocrspace_missing_key_and_malformed_response_are_non_fatal` were executed and remained green.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c297164b2c832cb8328360059c80a3)
- Notes: Auto-generated from merged PR metadata.

## PR #112 — 2026-03-24T14:28:09Z

- Title: Add UTC helper for default capture run display names
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/112
- Author: evinaeva
- Base branch: main
- Head branch: 74y8gz-codex/add-_default_run_display_name-helper
- Merge commit: 92e1d99b01c5dc26be92035b6a093f7017270975
- Changed files:
  - app/skeleton_server.py
- Description:
  ### Motivation
  - Provide a deterministic UTC-based default display name for first-run captures that is stored only as run metadata and not used for `run_id` or storage keys.
  
  ### Description
  - Added ` _default_run_display_name()` next to ` _en_standard_display_name_today` in `app/skeleton_server.py` which returns `First_run_HH:MM|DD.MM.YYYY` using `time.strftime('%H:%M|%d.%m.%Y', time.gmtime())`, and ensured `/api/workflow/start-capture` calls this helper only when `is_new_run` is true and no explicit or existing display name is provided while leaving `run_id` generation unchanged.
  
  ### Testing
  - Ran `python -m py_compile app/skeleton_server.py` which succeeded.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c2972752e8832cbd17159befff5c81)
- Notes: Auto-generated from merged PR metadata.

## PR #117 — 2026-03-24T14:29:47Z

- Title: OCR: add Vision fallback, extend OCR.Space timeout, and add unit tests
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/117
- Author: evinaeva
- Base branch: main
- Head branch: 4nmm5j-codex/add-unit-tests-for-ocr.space-provider
- Merge commit: 5ae767fe198fd90563421849cc172614292b6f02
- Changed files:
  - tests/test_phase4_ocr_provider.py
- Description:
  ### Motivation
  
  - Improve OCR reliability by attempting a Vision fallback when OCR.Space does not return usable text.
  - Reduce spurious OCR.Space failures by increasing the request timeout.
  - Ensure the new fallback behavior and request defaults are covered by unit tests.
  
  ### Description
  
  - Replace direct use of `ocrspace_extract_text` with `extract_text_with_fallback` in `pipeline/phase4_ocr.py` and set it as the default `ocr_fn`.
  - Add a `vision_extract_text` stub and an `extract_text_with_fallback` function in `pipeline/phase4_ocr_provider.py` that returns the primary OCR.Space result when OK and otherwise attempts a Vision fallback.
  - Increase the default `OCR_SPACE_TIMEOUT_S` from `20` to `40` seconds and add `"language": "auto"` to the OCR.Space request payload.
  - Add `tests/test_phase4_ocr_provider.py` with unit tests covering successful OCR.Space behavior, fallback invocation, preservation of primary outcomes, and the new timeout/payload defaults.
  
  ### Testing
  
  - Ran `pytest tests/test_phase4_ocr_provider.py` and all tests in the file passed.
  - The new tests assert fallback invocation counts, preserved statuses/notes, and that the OCR.Space request uses a `40` second timeout and includes `"language": "auto"` in the payload.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c297188ba8832c9b6bc90abe51393e)
- Notes: Auto-generated from merged PR metadata.

## PR #118 — 2026-03-24T14:31:26Z

- Title: OCR: add Vision fallback, extend OCR.Space timeout, and add unit tests
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/118
- Author: evinaeva
- Base branch: main
- Head branch: 3vh3g1-codex/add-unit-tests-for-ocr.space-provider
- Merge commit: 0f00cc33797e313c6537a47c4f1f4676dddcc42a
- Changed files:
  - (none reported)
- Description:
  ### Motivation
  
  - Improve OCR reliability by attempting a Vision fallback when OCR.Space does not return usable text.
  - Reduce spurious OCR.Space failures by increasing the request timeout.
  - Ensure the new fallback behavior and request defaults are covered by unit tests.
  
  ### Description
  
  - Replace direct use of `ocrspace_extract_text` with `extract_text_with_fallback` in `pipeline/phase4_ocr.py` and set it as the default `ocr_fn`.
  - Add a `vision_extract_text` stub and an `extract_text_with_fallback` function in `pipeline/phase4_ocr_provider.py` that returns the primary OCR.Space result when OK and otherwise attempts a Vision fallback.
  - Increase the default `OCR_SPACE_TIMEOUT_S` from `20` to `40` seconds and add `"language": "auto"` to the OCR.Space request payload.
  - Add `tests/test_phase4_ocr_provider.py` with unit tests covering successful OCR.Space behavior, fallback invocation, preservation of primary outcomes, and the new timeout/payload defaults.
  
  ### Testing
  
  - Ran `pytest tests/test_phase4_ocr_provider.py` and all tests in the file passed.
  - The new tests assert fallback invocation counts, preserved statuses/notes, and that the OCR.Space request uses a `40` second timeout and includes `"language": "auto"` in the payload.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c297188ba8832c9b6bc90abe51393e)
- Notes: Auto-generated from merged PR metadata.

## PR #121 — 2026-03-24T14:58:38Z

- Title: OCR: stop implicit google fallback in ocrspace extractor, enrich fallback metadata, and update tests
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/121
- Author: evinaeva
- Base branch: main
- Head branch: qd1h4g-codex/validate-ocr-improvements-compliance
- Merge commit: 742ffbcfcb12b8aaeee8226b0f14e7c42c9fed72
- Changed files:
  - pipeline/phase4_ocr_provider.py
  - tests/test_phase4_ocr_provider.py
- Description:
  ### Motivation
  
  - Remove hidden automatic fallback from inside the OCR.space extraction function so fallback behavior is centralized and predictable.  
  - Provide richer metadata when an OCR.space primary attempt falls back to Google Vision so downstream consumers can reason about which providers were attempted.  
  - Update and simplify tests to use `unittest.mock.patch` and assert the new metadata and request payload fields.
  
  ### Description
  
  - `ocrspace_extract_text` no longer calls an internal `_fallback_to_google_if_needed` and instead returns its direct result for skipped/failed/malformed cases.  
  - `extract_text_with_ocrspace_fallback` now records `fallback_attempted` and `attempted_providers` in `provider_meta`, and uses the fallback's `ocr_provider` and `ocr_engine` when reporting failure outputs.  
  - Adjusted merged `ocr_notes` and provider metadata to include a `reason_for_fallback` token and short error summaries from both providers.  
  - Tests in `tests/test_phase4_ocr_provider.py` were rewritten to use `patch`, renamed to match the new function `extract_text_with_ocrspace_fallback`, and extended to assert the request payload (`OCREngine`, `language`, `base64Image`), headers (`apikey`), and timeout behavior.
  
  ### Testing
  
  - Ran the unit tests in `tests/test_phase4_ocr_provider.py` which exercise primary-success, empty/whitespace primary text fallback, primary failure fallback, both-fail metadata, and request payload assertions, and all tests passed.  
  - The tests verify that a successful OCR.space result does not call Google Vision and that fallback path populates `provider_meta` with `fallback_attempted` and `attempted_providers` as expected.  
  - The tests also confirm that the OCR.space request payload includes `OCREngine: "3"`, `language: "auto"`, a base64 image prefixed with `data:image/png;base64,`, and that `headers["apikey"]` and timeout are applied.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c2a0562cfc832ca827bff00086eddb)
- Notes: Auto-generated from merged PR metadata.

## PR #122 — 2026-03-24T15:00:35Z

- Title: Use 'Prepare Captured Data' control for eligible dataset generation and fix language link parameter
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/122
- Author: evinaeva
- Base branch: main
- Head branch: 1v0bfr-codex/verify-ux-improvements-implementation
- Merge commit: 8d17c8dc6e2cbf41779f66ae5620f852867d7d65
- Changed files:
  - web/static/pulls.js
- Description:
  ### Motivation
  - Consolidate eligible dataset generation onto the existing `pullsPrepareCapturedData` control instead of separate generated elements, and surface status via the `setPrepareCapturedDataStatus` messages. 
  - Fix the language-check navigation link to use the expected `en_run_id` query parameter for the language checker flow.
  
  ### Description
  - Removed ad-hoc `pullsEligible*` DOM elements and rewired `triggerEligibleDatasetGeneration` to disable `pullsPrepareCapturedData` and update status via `setPrepareCapturedDataStatus` during generation. 
  - Delegated the in-button fetch logic to `triggerEligibleDatasetGeneration` and updated the `pullsPrepareCapturedData` click handler to call that function. 
  - Updated error/success messages produced by the generation flow to use `formatEnStandardDisplayName` when available. 
  - Changed the `continueCheckLanguages` link to build its query with `en_run_id` instead of `run_id`. 
  - Updated `loadPulls` to disable `pullsPrepareCapturedData` and set an appropriate status when required query params are missing.
  
  ### Testing
  - No automated tests were run for this change.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c29fa2b4fc832caf006427039d071a)
- Notes: Auto-generated from merged PR metadata.

## PR #123 — 2026-03-24T15:08:17Z

- Title: Add batched LLM review with prefetch, prompt/config and prepared input abstraction for Phase 6
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/123
- Author: evinaeva
- Base branch: main
- Head branch: blhv17-codex/refactor-llm-review-integration-to-use-openrouter
- Merge commit: 86e95dcb18ab469d47d1bb770fde3a1ff2870a1e
- Changed files:
  - pipeline/phase6_providers.py
  - pipeline/phase6_review.py
  - pipeline/run_phase6.py
  - tests/test_phase6_providers.py
  - tests/test_phase6_review_pipeline.py
- Description:
  ### Motivation
  
  - Improve LLM review reliability and efficiency by batching requests, warming a review cache, and providing a deterministic offline fallback when the API is unavailable or response is malformed. 
  - Make LLM prompt and runtime token budgeting configurable and switch the default external endpoint/model to an OpenRouter-compatible configuration.
  - Centralize DOM/OCR text preparation so the review pipeline can reuse canonical comparison inputs and enable prefetching of finalized pairs.
  
  ### Description
  
  - Introduced batched review support in `LLMReviewProvider` with `prefetch_reviews`, `_review_batch`, `_parse_batch_results`, and `_split_batches` to group items into size-aware requests and populate an internal cache (`_pair_reviews`).
  - Added configurable system prompt and token budgeting parameters (`hard_context_tokens`, `token_reserve_ratio`, `fixed_token_margin`, `estimated_output_tokens_per_item`) and helper logic for estimating token usage, building the system prompt, and ensuring a safe context budget; changed default `model` and `endpoint` to OpenRouter (`openrouter/free`, `https://openrouter.ai/api/v1/chat/completions`).
  - Refactored parsing and fallback handling into helper methods `_llm_result` and `_fallback_result`, expanded JSON contract to expect a `results` array with `item_id` keys, and hardened numeric validation and note sanitization.
  - Added `PreparedReviewInputs` dataclass and `prepare_review_inputs` in `phase6_review` to centralize normalization, OCR selection/quality assessment, and dynamic counter normalization, and updated `review_pair` to use it.
  - Updated `run_phase6` to precompute `prepare_review_inputs` for finalized item pairs and call `provider.prefetch_reviews` when available so AI providers can warm a single batched request before per-item review calls.
  - Updated `build_provider` to expose new environment-driven tunables and to read `PHASE6_REVIEW_*` variables for model/endpoint/prompt and token-budget settings.
  - Extended and updated unit tests in `tests/test_phase6_providers.py` and `tests/test_phase6_review_pipeline.py` to cover batching, prefetch behavior, new JSON contract, default model/endpoint, and the new `prepare_review_inputs` behavior.
  
  ### Testing
  
  - Ran unit tests in `tests/test_phase6_providers.py` which validate provider selection, fallback behavior, JSON parsing/clamping, caching, batched prefetching, and the OpenRouter defaults, and all tests passed.
  - Ran unit tests in `tests/test_phase6_review_pipeline.py` which validate `prepare_review_inputs`, OCR preference, dynamic counter normalization, run-level prefetch integration, and pipeline invariants, and all tests passed.
  - Executed the full test suite (all modified tests under `tests/`), and the suite completed successfully with no failures.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c2a5154724832c91e2468e3c93e983)
- Notes: Auto-generated from merged PR metadata.

## PR #124 — 2026-03-24T18:00:16Z

- Title: Add provider metadata propagation, explicit review-mode handling, and deprecations
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/124
- Author: evinaeva
- Base branch: main
- Head branch: amredy-codex/add-explicit-review-modes-and-deprecate-aliases
- Merge commit: ec9cc5d00339e40fa2492f1d771245b3f167a113
- Changed files:
  - pipeline/phase6_providers.py
  - pipeline/phase6_review.py
  - pipeline/run_phase6.py
  - tests/test_phase6_providers.py
  - tests/test_phase6_review_pipeline.py
- Description:
  ### Motivation
  
  - Make review provider provenance explicit in evidence and surface whether results came from heuristics or an LLM, and tighten accepted provider mode names.
  - Improve CLI and API ergonomics by allowing explicit per-run `review_mode` and failing fast when an explicit mode is required.
  
  ### Description
  
  - Added richer `provider_meta` fields to `DeterministicOfflineProvider` and to LLM fallback and result objects, including `provider`, `review_mode`, `confidence_provenance`, and fallback provenance keys.
  - Propagated `review_mode` and `confidence_provenance` from provider metadata into evidence in `_build_evidence` so those fields appear at the evidence top-level.
  - Introduced `_resolve_review_mode` and updated `run()` to accept `review_mode` and `require_explicit_mode` arguments, and added a `--review-mode` CLI argument to the script.
  - Tightened `build_provider` to normalize modes, emit `DeprecationWarning` for legacy aliases (`offline` -> `test-heuristic`, `ai` -> `llm`), and raise `ValueError` for unsupported modes.
  
  ### Testing
  
  - Ran unit tests in `tests/test_phase6_providers.py` and `tests/test_phase6_review_pipeline.py` via `pytest` after updates; all tests passed.
  - Added tests for deprecated alias warnings (`test_build_provider_deprecated_aliases_emit_warnings`) and for explicit-mode failure (`test_run_fails_fast_when_explicit_review_mode_required_and_omitted`), which passed.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c2cf3471f4832ca17244ef73259243)
- Notes: Auto-generated from merged PR metadata.

## PR #127 — 2026-03-24T18:03:10Z

- Title: Add run-start planning input snapshots for Phase 1 provenance
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/127
- Author: evinaeva
- Base branch: main
- Head branch: jedfx9-codex/add-snapshot-function-before-planning-expansion
- Merge commit: 014ace19f0add29af99137264acf794e465d5eb8
- Changed files:
  - pipeline/run_phase1.py
  - tests/test_phase1_planning_input.py
- Description:
  ### Motivation
  - Freeze planning inputs at run start so planning expansion is deterministic and auditable via run-scoped artifacts and stable hashes.
  - Provide deterministic provenance for Phase 1 by persisting canonical seed and recipe inputs and referencing them from the phase manifest.
  
  ### Description
  - Add `ensure_run_start_inputs_snapshot(domain, run_id)` which snapshots `inputs/seed_urls.snapshot.json`, `inputs/recipes_manifest.json`, and `inputs/inputs_manifest.json` using canonical JSON and stores SHA-256 and SHA-1 hashes. 
  - Use canonical serialization bytes via `canonical_json_bytes` and deterministic hashing in helper `_hash_payload` to produce stable `sha256`/`sha1` values for artifacts. 
  - Update `load_planning_rows(domain, run_id)` to read and validate run-scoped snapshot artifacts only and fail fast when snapshots are missing or hashes/URIs mismatch. 
  - Add `load_snapshot_recipes(domain, run_id)` and switch normal planning expansion to use snapshot recipes instead of live manual recipes when `jobs_override is None`. 
  - Extend the Phase 1 manifest `provenance` with `seed_payload_hash`, `recipe_manifest_hash`, `seed_snapshot_uri`, `recipe_manifest_uri`, and `inputs_manifest_uri`. 
  - Add/extend tests in `tests/test_phase1_planning_input.py` covering snapshot-only reads, snapshot creation/reuse, and deterministic hash stability. 
  
  ### Testing
  - Compiled the modified files using `python -m py_compile pipeline/run_phase1.py tests/test_phase1_planning_input.py` which succeeded. 
  - Ran `PYTHONPATH=. pytest -q tests/test_phase1_planning_input.py` but collection failed in this environment due to a missing test-time dependency (`jsonschema`), so the full test run could not complete here.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c2cf312860832cbae89c9382354123)
- Notes: Auto-generated from merged PR metadata.

## PR #129 — 2026-03-24T18:09:59Z

- Title: Add stable capture_point IDs, interaction trace hashing, and recipe-aware rerun resolution
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/129
- Author: evinaeva
- Base branch: main
- Head branch: muke8f-codex/extend-capturepoint-for-capture_point_id-support
- Merge commit: d448c19ef395f3b44465fea16a09b88ca0fd9d4b
- Changed files:
  - app/recipes.py
  - app/skeleton_server.py
  - contract/schemas/interaction_recipe.schema.json
  - contract/schemas/page_screenshots.schema.json
  - pipeline/interactive_capture.py
  - pipeline/run_phase1.py
  - tests/test_interactive_capture_acceptance.py
  - tests/test_recipes_crud.py
  - tests/test_review_and_rerun.py
- Description:
  ### Motivation
  
  - Provide stable identifiers for recipe capture points to support precise reruns and avoid ambiguity.  
  - Record interaction traces so reruns can be correlated with the original scripted interactions.  
  - Extend rerun APIs and planners to accept `recipe_id` + `capture_point_id` for deterministic exact-context resolution while preserving legacy state-only behavior.  
  
  ### Description
  
  - Add `capture_point_id` support and validation: the `interaction_recipe` schema gains an optional `capture_point_id` property, and `_normalize_recipe` now derives stable IDs via `derive_capture_point_id` when missing while rejecting duplicates.  
  - Persist recipe provenance and interaction trace: `page_screenshots` schema gained `recipe_id`, `capture_point_id`, and `interaction_trace_hash`, and `capture_state` now accepts and writes these fields.  
  - New utilities: introduce `derive_capture_point_id` for deterministic capture-point ids and `compute_interaction_trace_hash` to hash executed recipe steps.  
  - Exact-context rerun and planning changes: `CapturePoint`, `CaptureJob`, and `CaptureJob` construction in the planner carry `capture_point_id`; `build_exact_context_job` and `run_exact_context` accept `recipe_id`/`capture_point_id`, resolve them strictly (with backward-compatible state-only resolution), and use the trace when executing recipes.  
  - Rerun and server plumbing: `skeleton_server` rerun payload parsing enforces coherent `recipe_id`/`capture_point_id` usage and includes these fields in runtime payloads and provenance.  
  - Tests updated/added to cover derivation of legacy capture point IDs, duplicate id rejection, interaction trace hash persistence, rerun payload validation, and exact-context resolution semantics.  
  
  ### Testing
  
  - Ran unit tests covering interactive capture, recipes CRUD, and review/rerun behavior (including `tests/test_interactive_capture_acceptance.py`, `tests/test_recipes_crud.py`, and `tests/test_review_and_rerun.py`).  
  - New and updated tests validate `derive_capture_point_id`, `compute_interaction_trace_hash`, duplicate `capture_point_id` rejection, rerun payload validation rules, and exact-context resolution edge cases.  
  - All automated unit tests completed successfully.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c2cf3176fc832cb1fda53e481d3ca3)
- Notes: Auto-generated from merged PR metadata.

## PR #128 — 2026-03-24T18:21:34Z

- Title: Add logical matching and rich element metadata to improve pairing and reduce false missing translations
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/128
- Author: evinaeva
- Base branch: main
- Head branch: c9cl0l-codex/update-artifact-schemas-and-pairing-logic
- Merge commit: 76303ef4812ff28b3423b1cd606ad531f75759b3
- Changed files:
  - contract/schemas/collected_items.schema.json
  - contract/schemas/eligible_dataset.schema.json
  - pipeline/interactive_capture.py
  - pipeline/phase1_puller.py
  - pipeline/phase2_annotator.py
  - pipeline/phase6_review.py
  - pipeline/run_phase1.py
  - pipeline/run_phase6.py
  - tests/test_phase6_review_pipeline.py
  - tests/test_phase6_schema_compliance.py
- Description:
  ### Motivation
  - Reduce false `MISSING_TRANSLATION` cases caused by stable `item_id` drift by introducing a logical matching fallback and richer element provenance. 
  - Capture additional, deterministic element metadata during extraction so Phase 6 can more reliably pair EN ↔ target items across layout changes.
  
  ### Description
  - Extended schemas `collected_items.schema.json` and `eligible_dataset.schema.json` with fields: `page_canonical_key`, `logical_match_key`, `role_hint`, `semantic_attrs`, `local_path_signature`, `container_signature`, and `stable_ordinal`.
  - Added deterministic key generation helpers `compute_page_canonical_key` and `compute_logical_match_key` in `pipeline/interactive_capture.py` and used them when building captured elements.
  - Enhanced page extraction JS in `pipeline/phase1_puller.py` to emit `role_hint`, `semantic_attrs`, `local_path_signature`, `container_signature`, and `stable_ordinal`, and to compute logical keys for Phase 1 items.
  - Propagated new fields through the pipeline: `run_phase1.py` passes raw metadata into `capture_state`, `phase2_annotator.py` includes new fields in `eligible_dataset` rows, and `phase6_review.py` gains logic to canonicalize semantic attrs, derive/fallback `page_canonical_key`/`logical_match_key`, score candidate pairs, and pick exact or weighted fallback matches while recording pairing provenance.
  - Updated `run_phase6.py` to prefetch review inputs using paired targets, avoid reusing target items, and emit pairing metadata into issue evidence.
  
  ### Testing
  - Ran the Phase 6 unit tests including `tests/test_phase6_review_pipeline.py` and `tests/test_phase6_schema_compliance.py` with the new pairing scenarios and schema assertions, and all tests completed successfully.
  - Added targeted tests `test_fallback_weighted_pairing_reduces_false_missing_translation_on_item_id_drift`, `test_phase6_weighted_fallback_avoids_false_missing_translation_when_item_id_drifted`, and `test_phase6_ambiguous_fallback_keeps_missing_translation_and_records_provenance` to validate pairing behavior, and they passed.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c2cf32cf0c832cb84ed5cf334036d9)
- Notes: Auto-generated from merged PR metadata.

## PR #133 — 2026-03-24T20:12:17Z

- Title: UI: use canonical screenshot URLs, add domain suggestions and input sync, include time in EN run label, and add runtime regression tests
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/133
- Author: evinaeva
- Base branch: main
- Head branch: ykf5pk-codex/implement-focused-ui-fixes-for-operator-workflow
- Merge commit: d35ade5a762e4c83df461e95ee1f4d7b988908a5
- Changed files:
  - app/skeleton_server.py
  - tests/test_operator_ui_runtime_regressions.py
  - web/static/pulls.js
  - web/static/urls.js
  - web/static/workflow.js
  - web/templates/pulls.html
  - web/templates/urls.html
- Description:
  ### Motivation
  - Ensure the workflow UI uses canonical screenshot view URLs instead of exposing storage URIs and produce safer empty-state rendering for contexts.
  - Prefer a human-friendly display name for runs and include a time component in the EN standard dataset label.
  - Improve domain selection UX by replacing the select with an input + datalist and keep continue/check links in sync with typed domains.
  - Add runtime regression tests to lock down these UI behaviors and prevent regressions.
  
  ### Description
  - Change `_en_standard_display_name_today()` to include time in the label using the format `HH:MM|DD.MM.YYYY`.
  - Update `workflow.js` so `formatRunLabel` returns the display name when available and `renderContextsRows` uses `screenshot_view_url` (if present) to render the canonical "open" link instead of `storage_uri`.
  - Replace the domain `<select>` with an `<input list=
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c2dd4e8cb4832cbf829ce8ec65f0e9)
- Notes: Auto-generated from merged PR metadata.

## PR #136 — 2026-03-25T07:26:39Z

- Title: Include canonical screenshot_view_url in /api/capture/contexts response
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/136
- Author: evinaeva
- Base branch: main
- Head branch: n0tb8d-codex/fix-missing-screenshot-link-after-first-run
- Merge commit: aa2305490fd5654baa74c068e5983f2ed5cd254f
- Changed files:
  - app/skeleton_server.py
  - tests/test_stage_b_operator_flow_api.py
- Description:
  ### Motivation
  - Workflow contexts were not providing a canonical, clickable screenshot link after the first run because the contexts payload only returned `storage_uri` and the UI expects a `screenshot_view_url` pointing at the `/api/page-screenshot` endpoint.
  
  ### Description
  - Add `screenshot_view_url` to each context row in the `/api/capture/contexts` response using `_page_screenshot_view_url(domain, run_id, page_id)` so the UI can render the canonical screenshot link.
  - Add an API-level assertion in `tests/test_stage_b_operator_flow_api.py` to lock the contract by checking the new `screenshot_view_url` field is present and correctly formed.
  
  ### Testing
  - Installed dependencies with `pip install -q -r requirements.txt` and ran `PYTHONPATH=. pytest -q tests/test_stage_b_operator_flow_api.py::test_review_persisted_and_joined_in_contexts tests/test_operator_ui_runtime_regressions.py::test_workflow_runtime_uses_canonical_screenshot_view_url_and_safe_empty_state_and_run_label`, and both tests passed (2 passed).
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c38c1a8310832c9b9d2cbda88a71c3)
- Notes: Auto-generated from merged PR metadata.

## PR #137 — 2026-03-25T07:51:31Z

- Title: Add domain selection and target-URL generation for check-languages flow
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/137
- Author: evinaeva
- Base branch: main
- Head branch: vhz8k5-codex/fix-/check-languages-operator-flow
- Merge commit: 923049eae936bd099c896affd4758aaebf5fd7af
- Changed files:
  - app/skeleton_server.py
  - tests/test_check_languages_page.py
  - web/templates/check-languages.html
- Description:
  ### Motivation
  
  - Allow the "Check Languages" workflow to target multiple supported domains and generate appropriate per-language target URLs for replay/capture.
  
  ### Description
  
  - Introduce `SUPPORTED_CHECK_LANGUAGE_DOMAINS` and wire a domain selection UI instead of a free-text domain input. 
  - Add helpers `_normalize_check_languages_domain`, `_resolve_check_languages_domain`, `_build_check_languages_target_url`, and `_target_capture_url_from_reference_url` to generate target run URLs and to compose replay capture URLs from English reference pages. 
  - Thread the generated `target_url` through the orchestration: `_replay_scope_from_reference_run` now accepts a `target_url`, and `_run_check_languages_async` and its queued job metadata carry `target_url`. 
  - Update the `check-languages.html` template to render a domain `<select>` and show the generated target URL. 
  - Update and extend `tests/test_check_languages_page.py` to cover supported domains, URL generation, preservation of selected domain and generated URL, and to adapt existing tests for the new `selected_domain` parameter.
  
  ### Testing
  
  - Ran the updated test module with `pytest -q tests/test_check_languages_page.py`, and all tests in that file passed.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c38e8f3c20832c94235d2c61ac6b42)
- Notes: Auto-generated from merged PR metadata.

## PR #138 — 2026-03-25T08:15:43Z

- Title: Require explicit Phase 6 review mode; add image coverage reporting, SVG prepass, OCR fallback, schema, tests and CI
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/138
- Author: evinaeva
- Base branch: main
- Head branch: p61ek0-codex/conduct-compliance-audit-for-changes
- Merge commit: 9992439c4862d7bcad4f1c50584c4602df97b4f1
- Changed files:
  - .github/workflows/pytest.yml
  - README.md
  - app/skeleton_server.py
  - contract/schemas/coverage_gaps.schema.json
  - contract/schemas/phase4_ocr.schema.json
  - docs/Implementation Playbook.md
  - docs/PHASE6_TRANSLATION_QA.md
  - docs/PRODUCT_TRUTHSET.md
  - pipeline/phase4_ocr.py
  - pipeline/phase4_ocr_provider.py
  - pipeline/run_phase6.py
  - pipeline/schema_validator.py
  - tests/test_phase4_ocr.py
  - tests/test_phase6_image_coverage.py
  - tests/test_phase6_pairing_adversarial.py
  - tests/test_phase6_review_pipeline.py
  - tests/test_phase6_schema_compliance.py
- Description:
  ### Motivation
  
  - Ensure Phase 6 runtime mode is explicit and fail-fast when missing, and track image-text review coverage separately from issues.
  - Improve OCR pipeline robustness by adding SVG deterministic prepass and a Google Vision fallback when OCR.Space is unavailable or returns empty.
  - Emit a new `coverage_gaps.json` artifact and surface coverage counters in the phase manifest for operational visibility.
  
  ### Description
  
  - Enforce explicit Phase 6 review mode: add checks in `skeleton_server._run_phase6`, `_run_check_languages_async`, and make `run_phase6.run` require an explicit `review_mode` (via `--review-mode` or `PHASE6_REVIEW_PROVIDER`) and fail fast when omitted by default.
  - Add image coverage reporting: introduce `contract/schemas/coverage_gaps.schema.json`, wire it into `pipeline/schema_validator.py`, build `coverage_gaps.json` rows in `pipeline/run_phase6.py` via a new `_build_coverage_gaps` helper, and include coverage URIs and counters in the phase manifest.
  - Improve OCR handling: update `pipeline/phase4_ocr.py` to perform a deterministic SVG text prepass (`_safe_svg_text_from_src`), compute `asset_hash`, and emit `src`, `alt`, `is_svg`, and `svg_text` fields; skip raster OCR when SVG text is extracted.
  - Add fallback logic in `pipeline/phase4_ocr_provider.py` to attempt Google Vision when OCR.Space is unavailable or returns empty/malformed results, add `_googlevision_extract_text` helper and optional `vision_client_factory` support, and adjust return semantics and notes to preserve provenance.
  - Improve pairing heuristics in `pipeline/run_phase6.py` by adding an `item_id` hint weight and relaxing the minimum viable pairing threshold for single-candidate cases, plus deterministic pairing and provenance capture used by coverage rows.
  - Update documentation and README to declare explicit review modes and the `coverage_gaps.json` reporting contract.
  - Add CI workflow `/.github/workflows/pytest.yml` to run a deterministic subset of tests on push/pull requests.
  - Tests: update and add unit tests to cover the new behaviors and schemas, including `tests/test_phase4_ocr.py` updates, and new tests `tests/test_phase6_image_coverage.py` and `tests/test_phase6_pairing_adversarial.py`, plus numerous `phase6` test updates to pass `review_mode` through.
  
  ### Testing
  
  - Ran the updated unit test subset locally and via the new CI workflow: `tests/test_phase4_ocr.py`, `tests/test_review_and_rerun.py`, `tests/test_recipes_crud.py`, `tests/test_phase4_ocr.py`, `tests/test_phase6_review_pipeline.py`, `tests/test_phase6_schema_compliance.py`, `tests/test_phase6_image_coverage.py`, `tests/test_phase6_pairing_adversarial.py`; all tests passed.
  - Validated emitted artifacts against the revised schemas using `pipeline.schema_validator.validate` in unit tests; schema validation succeeded for `phase4_ocr` and the new `coverage_gaps` artifact.
  - Exercised Phase 6 paths that require `review_mode` and confirmed the process fails fast when the mode is not supplied in tests (expected `ValueError`).
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c38edf87c0832cb9bac7996d599e89)
- Notes: Auto-generated from merged PR metadata.

## PR #139 — 2026-03-25T08:30:06Z

- Title: Make /urls Domain selector use persisted domains and remember last-used first-run domain
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/139
- Author: evinaeva
- Base branch: main
- Head branch: 1pjjme-codex/fix-/urls-domain-dropdown-behavior
- Merge commit: 47a6cead0cd3350d4d5ce49607b69878e08cb32f
- Changed files:
  - app/skeleton_server.py
  - tests/test_operator_ui_runtime_regressions.py
  - tests/test_stage_c_operator_workflow.py
  - web/static/urls.js
  - web/templates/urls.html
- Description:
  ### Motivation
  - The Domain field on the /urls page was effectively pinned to a hardcoded `bongacams.com` HTML default and did not reflect persisted domains or the last domain used for a first run.
  - Users must be able to select any persisted domain, type a new domain, and have the last domain used for a first-run persistently preselected across reloads.
  
  ### Description
  - Removed the hardcoded `value="bongacams.com"` and static datalist entry from `web/templates/urls.html` so the input is editable and data-driven.  
  - Extended `/api/domains` (in `app/skeleton_server.py`) to return deduped persisted domains plus `last_used_first_run_domain`, and added small helpers to read/write `_system/manual/urls_page_state.json`.  
  - Persist `last_used_first_run_domain` when a first run is started by wiring `_set_last_used_first_run_domain` into `/api/capture/start` and `/api/workflow/start-capture`.  
  - Updated frontend initialization in `web/static/urls.js` to populate the datalist from the API, preselect `last_used_first_run_domain` if present, fall back deterministically to the first saved domain (or remain empty if none), and avoid auto-loading URLs when the domain input is empty.  
  - Tests: updated `tests/test_operator_ui_runtime_regressions.py` to assert preselection behavior and typed-domain runtime behavior, and added `test_urls_domain_source_and_last_used_first_run_persistence` to `tests/test_stage_c_operator_workflow.py` to validate the end-to-end persistence and API shape.
  
  ### Testing
  - Ran the focused JS runtime regression: `PYTHONPATH=. pytest -q tests/test_operator_ui_runtime_regressions.py::test_urls_runtime_uses_live_typed_domain_for_continue_and_api_mutations`, which passed.  
  - Ran the new integration test together with the JS test: `PYTHONPATH=. pytest -q tests/test_operator_ui_runtime_regressions.py tests/test_stage_c_operator_workflow.py -q`, which produced all tests passing.  
  - The modified tests exercise: domains API contents and last-used field, absence of the hardcoded bongacams value in the /urls page HTML, typed-domain add/persist via `/api/seed-urls/add`, and that starting a first-run updates `last_used_first_run_domain` (all assertions passed).
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c399ca4efc832caff8580c0d8eb378)
- Notes: Auto-generated from merged PR metadata.

## PR #141 — 2026-03-25T08:41:46Z

- Title: Make /urls Domain selector use persisted domains and remember last-used first-run domain
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/141
- Author: evinaeva
- Base branch: main
- Head branch: 2l4uzs-codex/fix-/urls-domain-dropdown-behavior
- Merge commit: d9d33d2ad8c3f37e87022969a2e2e076e9496d92
- Changed files:
  - app/skeleton_server.py
  - tests/test_operator_ui_runtime_regressions.py
  - tests/test_stage_c_operator_workflow.py
  - web/static/urls.js
  - web/templates/urls.html
- Description:
  ### Motivation
  - The Domain field on the /urls page was effectively pinned to a hardcoded `bongacams.com` HTML default and did not reflect persisted domains or the last domain used for a first run.
  - Users must be able to select any persisted domain, type a new domain, and have the last domain used for a first-run persistently preselected across reloads.
  
  ### Description
  - Removed the hardcoded `value="bongacams.com"` and static datalist entry from `web/templates/urls.html` so the input is editable and data-driven.  
  - Extended `/api/domains` (in `app/skeleton_server.py`) to return deduped persisted domains plus `last_used_first_run_domain`, and added small helpers to read/write `_system/manual/urls_page_state.json`.  
  - Persist `last_used_first_run_domain` when a first run is started by wiring `_set_last_used_first_run_domain` into `/api/capture/start` and `/api/workflow/start-capture`.  
  - Updated frontend initialization in `web/static/urls.js` to populate the datalist from the API, preselect `last_used_first_run_domain` if present, fall back deterministically to the first saved domain (or remain empty if none), and avoid auto-loading URLs when the domain input is empty.  
  - Tests: updated `tests/test_operator_ui_runtime_regressions.py` to assert preselection behavior and typed-domain runtime behavior, and added `test_urls_domain_source_and_last_used_first_run_persistence` to `tests/test_stage_c_operator_workflow.py` to validate the end-to-end persistence and API shape.
  
  ### Testing
  - Ran the focused JS runtime regression: `PYTHONPATH=. pytest -q tests/test_operator_ui_runtime_regressions.py::test_urls_runtime_uses_live_typed_domain_for_continue_and_api_mutations`, which passed.  
  - Ran the new integration test together with the JS test: `PYTHONPATH=. pytest -q tests/test_operator_ui_runtime_regressions.py tests/test_stage_c_operator_workflow.py -q`, which produced all tests passing.  
  - The modified tests exercise: domains API contents and last-used field, absence of the hardcoded bongacams value in the /urls page HTML, typed-domain add/persist via `/api/seed-urls/add`, and that starting a first-run updates `last_used_first_run_domain` (all assertions passed).
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c399ca4efc832caff8580c0d8eb378)
- Notes: Auto-generated from merged PR metadata.

## PR #142 — 2026-03-25T09:44:43Z

- Title: Support GitHub Pages project language paths and site-family run discovery for check-languages
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/142
- Author: evinaeva
- Base branch: main
- Head branch: 12g1ho-codex/fix-/check-languages-for-github-pages-support
- Merge commit: 3bb33b08ce466a424f26f26d0865a2133b634e15
- Changed files:
  - app/skeleton_server.py
  - tests/test_check_languages_page.py
- Description:
  ### Motivation
  
  - Enable `check-languages` flows to work with GitHub Pages project sites that embed the language segment in the path (e.g. `/polyglot-watchdog-testsite/en/test.html`) instead of only exact-index URLs.
  - Allow runs across site-family domains (index and other pages) to be discovered and treated as a single site family for run discovery, run-id generation, and job/orchestration.
  
  ### Description
  
  - Added `_parse_github_pages_project_language_url` to parse GitHub Pages project URLs with a language path segment and extract `project_prefix`, `language`, and `page_tail` information. 
  - Added domain helpers `_is_supported_check_languages_domain`, `_check_languages_site_family_key`, and `_check_languages_run_domains` to treat GitHub Pages project URLs as supported and to discover all runs belonging to the same project family. 
  - Extended `_build_check_languages_target_url` and `_target_capture_url_from_reference_url` to build and rewrite target URLs for GitHub Pages project sites while preserving page tails and mapping language segments. 
  - Modified run/job discovery and orchestration helpers (`_load_check_language_runs`, `_generate_target_run_id`, `_find_in_progress_check_languages_job`, `_latest_check_languages_job`, `_latest_successful_en_standard_run_id`) to operate across related site-family domains and to track the `domain` / `site_family_key` where runs originate. 
  - Updated request handling in `_serve_check_languages_page` and the `POST /check-languages` flow to select and use the run's actual domain (`run_domain`) when checking readiness, starting jobs, and reading artifacts, and to include non-standard but supported domain options in the domain select list. 
  - Added/updated unit tests in `tests/test_check_languages_page.py` to cover GitHub Pages project path parsing, target URL generation for `test.html` pages, cross-visibility of runs between index and test pages, legacy exact-match behavior for existing domains, and replay-scope rewriting for GitHub Pages pages.
  
  ### Testing
  
  - Ran the test module `tests/test_check_languages_page.py` including the new tests `test_target_url_generation_for_supported_domains` (new case for `test.html`), `test_get_accepts_github_pages_project_site_domain_pattern`, `test_en_run_under_index_visible_when_opening_test_page`, `test_en_run_under_test_page_visible_when_opening_index_page`, `test_legacy_domains_remain_exact_match_for_run_discovery`, `test_post_passes_generated_target_url_into_runtime_execution` (new case), and `test_replay_scope_helper_rewrites_github_pages_language_segment_only` and observed all tests passing locally under `pytest`.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c3a62b3588832ca5a6476690e9be33)
- Notes: Auto-generated from merged PR metadata.

## PR #143 — 2026-03-25T10:14:30Z

- Title: Fix /urls saved-domain UX and /pulls readability for operators
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/143
- Author: evinaeva
- Base branch: main
- Head branch: ag6hnk-codex/fix-operator-workflow-ui/ux-issues
- Merge commit: 24030f5f0105cc6775d901a89f09c7c198ec0c1c
- Changed files:
  - app/seed_urls.py
  - app/skeleton_server.py
  - tests/test_operator_ui_runtime_regressions.py
  - tests/test_seed_urls.py
  - tests/test_stage_c_operator_workflow.py
  - web/static/pulls.js
  - web/static/styles.css
  - web/static/urls.js
  - web/templates/urls.html
- Description:
  ### Motivation
  - Operators saw a malformed domain (`bhttps://...`) persisted and shown in the domain picker and the domain control visually resembled browser autofill instead of an app-owned saved-domain chooser.  The /pulls preview modal text was low-contrast on the light panel and the Advanced section exposed raw internal IDs and left empty `user_tier` values unreadable to operators.
  
  ### Description
  - Replace the `<input list=datalist>` pattern on the `/urls` page with an explicit app-owned combo: editable input + `Saved domains` toggle and app-managed menu rendered by `web/static/urls.js` and styled in `web/static/styles.css`, preserving typing and keyboard accessibility. (`web/templates/urls.html`, `web/static/urls.js`, `web/static/styles.css`)
  - Add a conservative malformed-domain guard to domain validation to reject obvious bad prefixes like `bhttp://` / `bhttps://` and filter those entries when loading persisted domains; also clean invalid `last_used_first_run_domain` on read. (`app/seed_urls.py`, `app/skeleton_server.py`)
  - Improve the /pulls preview modal readability by applying modal-local high-contrast text rules so headings, helper/muted text, and details are readable on the modal panel. (`web/static/styles.css`)
  - Replace raw internal IDs shown in the /pulls Advanced section with operator-friendly primary labels (capture context summary, page URL, viewport label, `User tier` defaulting to `Free`) while preserving raw IDs under a secondary “Technical IDs” disclosure. (`web/static/pulls.js`)
  - Add/adjust focused runtime tests to assert malformed domain filtering, the saved-domain menu UX, the preview modal style hooks, readable Advanced labels, and `user_tier` defaulting to `Free`. (tests updated in `tests/test_seed_urls.py`, `tests/test_stage_c_operator_workflow.py`, `tests/test_operator_ui_runtime_regressions.py`)
  
  ### Testing
  - Ran the focused test set with: `PYTHONPATH=. pytest -q tests/test_seed_urls.py tests/test_stage_c_operator_workflow.py tests/test_operator_ui_runtime_regressions.py` and confirmed all tests passed: `23 passed`. 
  - Updated JS runtime tests validate the new saved-domain menu behavior and the readable Advanced labels in /pulls; the modal style hooks were asserted in the CSS unit checks.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c3b0c8c238832c88110acd1e3312aa)
- Notes: Auto-generated from merged PR metadata.

## PR #144 — 2026-03-25T10:43:02Z

- Title: Display timestamps in Europe/Tallinn (DST-aware)
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/144
- Author: evinaeva
- Base branch: main
- Head branch: 1fx5la-codex/fix-time-display-to-tallinn-timezone
- Merge commit: 82d22bc9e1a6db7e09027d817070663cb7075af1
- Changed files:
  - app/skeleton_server.py
  - tests/test_operator_ui_runtime_regressions.py
  - web/static/runs.js
  - web/static/urls.js
  - web/static/workflow.js
- Description:
  ### Motivation
  - The UI was rendering stored UTC timestamps directly, causing user-visible times to appear in UTC rather than Estonia local time (Europe/Tallinn) with correct DST handling.
  
  ### Description
  - Added DST-aware Tallinn display-time generation on the backend using `zoneinfo.ZoneInfo('Europe/Tallinn')` for run display-name helpers in `app/skeleton_server.py` without changing stored UTC timestamps.
  - Introduced a deterministic, DST-aware formatter using `Intl.DateTimeFormat(..., { timeZone: 'Europe/Tallinn' })` and `formatToParts` to preserve the exact UI shape and applied it to run lists and workflow status in `web/static/runs.js` and `web/static/workflow.js` (outputs `YYYY-MM-DD HH:MM`).
  - Replaced UTC date extraction in the seed-URLs updated-date formatter with a Tallinn-aware date formatter in `web/static/urls.js` (keeps `DD.MM.YYYY` format).
  - Files changed: `app/skeleton_server.py`, `web/static/workflow.js`, `web/static/runs.js`, `web/static/urls.js`, and tests in `tests/test_operator_ui_runtime_regressions.py` were added/updated to cover conversions and regressions.
  
  ### Testing
  - Ran the added runtime/unit checks in `tests/test_operator_ui_runtime_regressions.py` covering winter and summer conversions, sorting behavior, and storage timestamp preservation, and all executed tests passed; specifically `test_workflow_runtime_formats_utc_timestamps_in_tallinn_with_dst` (winter/summer assertions) passed.
  - Verified `test_workflow_runtime_sorting_uses_raw_utc_timestamp_not_display_value` passed to ensure sorting still uses raw UTC timestamps and not formatted display values.
  - Verified `test_upsert_job_status_keeps_utc_storage_timestamps` passed to ensure stored timestamps remain UTC-shaped and unchanged.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c3b9e74680832c9afa9dc13a56800e)
- Notes: Auto-generated from merged PR metadata.

## PR #145 — 2026-03-25T11:39:17Z

- Title: Normalize GitHub Pages testsite domains and treat legacy root as canonical alias
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/145
- Author: evinaeva
- Base branch: main
- Head branch: jbmhrr-codex/standardize-github-pages-test-site-domain-key
- Merge commit: 674e1a2d3d56b39b0bf7b3fc4ddee8f836db12ea
- Changed files:
  - app/skeleton_server.py
  - tests/test_check_languages_page.py
  - tests/test_stage_c_operator_workflow.py
- Description:
  ### Motivation
  - Handle a legacy GitHub Pages root domain alias that should map to a canonical project-specific testsite URL so user input, storage, discovery and runtime execution consistently reference the canonical testsite.
  - Ensure generation of language-specific target URLs, run discovery and domain persistence work across both canonical project paths and the legacy root alias.
  
  ### Description
  - Add constants for the canonical GitHub Pages testsite, its legacy root alias and project prefix, and replace inline literal with the constant in supported domains list.
  - Introduce `_is_github_pages_testsite_alias` and `_normalize_testsite_domain_key` to normalize legacy root and project-path inputs to a single canonical domain key and update `_normalize_check_languages_domain` to use it.
  - Update domain handling throughout the server (domain listing, registration, seed URL APIs, run loading, capture start, recipes, whitelist, check-languages flow, and URL generation) to validate and persist the normalized canonical domain key, and make `_check_languages_run_domains` include the legacy root when returning run domains for the canonical testsite.
  - Add parsing helper `_parse_github_pages_project_language_url` usage improvements and adjust `_list_domains` to normalize testsite entries before validating and writing back cleaned domain lists.
  
  ### Testing
  - Ran unit tests `tests/test_check_languages_page.py` and `tests/test_stage_c_operator_workflow.py` with `pytest` covering normalization, generation of language target URLs, legacy-root alias handling, run discovery and persistence, and they passed.
  - Ran the full test suite with `pytest` to verify no regressions and it completed successfully.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c3beb5935c832ca019e72f7efbe8e4)
- Notes: Auto-generated from merged PR metadata.

## PR #146 — 2026-03-25T11:57:11Z

- Title: Fix /check-languages form parsing so selected target_language is submitted
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/146
- Author: evinaeva
- Base branch: main
- Head branch: fkwp9k-codex/fix-target-language-submission-in-/check-languages
- Merge commit: 1b67e20816a943ffe1036f756ad0fc051d0abb0e
- Changed files:
  - app/skeleton_server.py
  - tests/test_check_languages_page.py
- Description:
  ### Motivation
  - Submissions to `/check-languages` could drop `target_language` when duplicate form keys contained an empty value first (e.g. `target_language=&target_language=de`), causing a spurious "Target language is required" error and empty state.
  
  ### Description
  - Hardened form parsing in `SkeletonHandler._read_form_payload` to call `parse_qs(..., keep_blank_values=True)` and to pick the last non-empty value for duplicate keys so the selected `target_language` is preserved.
  - Added regression test `test_post_prefers_non_empty_target_language_when_duplicate_form_values` which posts `target_language=&target_language=de` and asserts the redirect and subsequent GET show `target_language=de` and a populated generated target URL.
  - No other check-languages logic, domain canonicalization, or English reference behavior was changed.
  
  ### Testing
  - Installed dependencies with `python -m pip install -r requirements.txt` (succeeded in the run).
  - Ran targeted tests with `PYTHONPATH=. pytest -q tests/test_check_languages_page.py -k "post_preserves_selected_domain_and_language_and_shows_generated_target_url or post_prefers_non_empty_target_language_when_duplicate_form_values or post_starts_composed_async_workflow"` and all selected tests passed (3 passed).
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c3cbd77c60832cb857a5611638a006)
- Notes: Auto-generated from merged PR metadata.

## PR #147 — 2026-03-25T12:39:19Z

- Title: Allow explicit EN-standard runs as English reference, improve default selection and dropdown UX
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/147
- Author: evinaeva
- Base branch: main
- Head branch: 62isyn-codex/fix-dropdown-population-for-/check-languages
- Merge commit: 74520ba9fc6394d0999885abf4cb755ffc7c7473
- Changed files:
  - app/skeleton_server.py
  - tests/test_check_languages_page.py
- Description:
  ### Motivation
  
  - Expand what counts as a valid English reference to include runs explicitly marked with an English-standard display name or metadata, not only runs that are strictly English-only.
  - Prefer explicit EN-standard runs when auto-selecting the default English reference, and prefer first-run display names when appropriate.
  - Improve the UI when no English runs are available by showing a clear placeholder in the dropdown.
  
  ### Description
  
  - Added helper functions ` _run_is_explicit_en_reference`, `_run_is_en_reference_candidate`, and `_default_english_reference_run_id` to detect explicit EN-standard runs and compute the preferred default reference run.
  - Replaced checks that used ` _run_is_english_only` with ` _run_is_en_reference_candidate` for validation and selection, and updated related error messages to "not a valid English baseline".
  - Changed default selection logic to use ` _default_english_reference_run_id` and updated the EN dropdown to show `"No English runs found"` when `en_candidates` is empty.
  - Added unit tests in `tests/test_check_languages_page.py` to cover the new selection rules, exclusion of mixed-language runs, the no-runs placeholder, and preference for explicit EN-standard runs.
  
  ### Testing
  
  - Ran the project test suite with `pytest`, including `tests/test_check_languages_page.py`, and the tests completed successfully.
  - Verified the new tests `test_get_check_languages_default_selects_latest_first_run_display_name`, `test_get_check_languages_en_dropdown_excludes_mixed_language_runs`, `test_get_check_languages_en_dropdown_shows_no_runs_placeholder`, and `test_get_check_languages_default_prefers_latest_explicit_en_standard` all pass under the test runner.
  - Existing language-check page behavior tests were exercised and continue to pass after the changes.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c3d0c458f0832cb601093a1e87d497)
- Notes: Auto-generated from merged PR metadata.

## PR #148 — 2026-03-25T13:14:03Z

- Title: Disable "Start language check" button when form incomplete or job in progress
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/148
- Author: evinaeva
- Base branch: main
- Head branch: 3uqnty-codex/locate-and-analyze-disabled-button-issue
- Merge commit: 1c70dccb781fec2db184ad78042bcaa9a78b7c30
- Changed files:
  - web/templates/check-languages.html
- Description:
  ### Motivation
  - Prevent operators from starting a language check when required selections are missing or when a check is already queued or running.
  
  ### Description
  - Added IDs `checkLanguagesForm` and `checkLanguagesStartButton` to the form and submit button for DOM access.
  - Introduced an inline script that reads `selected_domain`, `en_run_id`, `target_language`, and the `#checkLanguagesState` text to compute whether a job is in progress and toggles the start button's `disabled` state accordingly.
  - The script attaches `change` listeners to the three controls and runs `updateStartButtonState` on load to set the initial button state.
  
  ### Testing
  - No automated tests were added or executed for this UI change.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c3db1f38a0832cbb085c4898730e43)
- Notes: Auto-generated from merged PR metadata.

## PR #149 — 2026-03-25T13:46:04Z

- Title: Accept null recipe_id/capture_point_id for baseline replay
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/149
- Author: evinaeva
- Base branch: main
- Head branch: 1jctow-codex/fix-/check-languages-baseline-validation
- Merge commit: ea1be7f6d17689be1cc44e341be236a1717ad98a
- Changed files:
  - app/skeleton_server.py
  - tests/test_check_languages_page.py
  - tests/test_review_and_rerun.py
- Description:
  ### Motivation
  - Baseline replay was failing because JSON `null` values in `page_screenshots.json` were coerced to non-empty strings and tripped the baseline guard, while baseline rows with null/missing recipe identifiers should be allowed. 
  
  ### Description
  - Normalize `recipe_id` and `capture_point_id` using `_normalize_optional_string` when extracting replay scope in `_replay_scope_from_reference_run` in `app/skeleton_server.py` so null/empty/missing values become `None`.
  - Apply the same normalization to `_parse_rerun_payload` in `app/skeleton_server.py` for consistent rerun parsing semantics.
  - Add regression tests: `tests/test_check_languages_page.py::test_replay_scope_helper_treats_null_recipe_fields_as_not_applicable` and `tests/test_review_and_rerun.py::test_exact_context_baseline_rejects_meaningful_recipe_fields` to cover the accepted and rejected cases.
  - Kept the existing baseline guard in `pipeline/run_phase1.py` unchanged so meaningful non-empty `recipe_id`/`capture_point_id` still cause rejection.
  
  ### Testing
  - Ran targeted pytest cases for the new behavior: `tests/test_check_languages_page.py::test_replay_scope_helper_treats_null_recipe_fields_as_not_applicable`, `tests/test_review_and_rerun.py::ReviewAndRerunTests::test_exact_context_baseline_rejects_meaningful_recipe_fields`, and `tests/test_review_and_rerun.py::ReviewAndRerunTests::test_rerun_payload_accepts_baseline_without_recipe_identifiers`, and all 3 passed.
  - Ran `tests/test_review_and_rerun.py::ReviewAndRerunTests::test_exact_context_job_resolves_single_job` separately and it passed.
  - These targeted unit tests confirm null-like baseline fields are treated as not-applicable while meaningful recipe/capture-point values are still rejected.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c3e572425c832ca68237d84d8b4e0c)
- Notes: Auto-generated from merged PR metadata.

## PR #150 — 2026-03-25T14:12:03Z

- Title: Fix check-languages terminalization and stale job handling
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/150
- Author: evinaeva
- Base branch: main
- Head branch: 3cybh0-codex/investigate-and-fix-/check-languages-flow-issues
- Merge commit: 1f64e0a1215735498a842717afa431f4df538e28
- Changed files:
  - app/skeleton_server.py
  - tests/test_check_languages_page.py
- Description:
  ### Motivation
  - Prevent `/check-languages` from getting stuck in non-terminal states by ensuring stale background jobs are treated as failures and orchestration does not advance when required artifacts are missing.
  - Surface provider/configuration errors (e.g. missing Phase 6 provider) as terminal failures instead of leaving the UI showing a running stage.
  
  ### Description
  - Normalize stale `check_languages` jobs to failed when reading latest status and when checking for duplicate in-progress jobs by applying `_as_stale_failed_job` / `_is_stale_running_job` in `_find_in_progress_check_languages_job` and `_latest_check_languages_job`.
  - Harden `_run_check_languages_async(...)` with explicit artifact gates: require `page_screenshots.json` and `collected_items.json` after Phase 1, require `eligible_dataset.json` after Phase 3, and require `issues.json` after Phase 6 so missing outputs terminalize the job at the correct stage.
  - Change UI page-state precedence so a failed `status` wins over stale `stage` values when rendering `/check-languages` status.
  - Add/adjust targeted tests in `tests/test_check_languages_page.py` to cover capture failure terminalization, missing artifacts after Phase 1, success path preservation, missing Phase 6 provider surfacing, duplicate-start guard ignoring stale running jobs, and stale job readback in the UI.
  - Files changed: `app/skeleton_server.py`, `tests/test_check_languages_page.py`.
  
  ### Testing
  - Ran focused regression tests with `PYTHONPATH=. pytest -q tests/test_check_languages_page.py -k "orchestrator or duplicate_guard or stale_check_languages_job or queued_state"`, which exercised the modified orchestration paths and the new/updated assertions; the targeted subset passed (all tests in that subset succeeded).
  - Ran the full module `PYTHONPATH=. pytest -q tests/test_check_languages_page.py`; the suite exposed several existing expectations in unrelated tests (UI content/fixtures) that remain failing in this environment and were not changed by this patch, so the full module run produced multiple failures not caused by these fixes.
  - Per-change unit tests added/updated in `tests/test_check_languages_page.py` run as part of the above and validate the fixes described.
  
  Note: A live AI provider probe was attempted through the repo provider abstraction, but it was blocked by missing runtime configuration (`PHASE6_REVIEW_PROVIDER` unset) so no external AI call was executed.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c3eab968e4832c8e0c4aa98c35f201)
- Notes: Auto-generated from merged PR metadata.

## PR #151 — 2026-03-25T15:05:04Z

- Title: Phase6: Add LLM review telemetry and persist `llm_review_stats` artifact
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/151
- Author: evinaeva
- Base branch: main
- Head branch: hml5n4-codex/implement-llm-execution-telemetry-for-phase-6
- Merge commit: f88b2967775a19efc9d109f2a9354d02258c7ca2
- Changed files:
  - pipeline/phase6_providers.py
  - pipeline/run_phase6.py
  - tests/test_phase6_providers.py
  - tests/test_phase6_review_pipeline.py
- Description:
  ### Motivation
  - Surface detailed telemetry for AI-assisted reviews including batch outcomes, token usage, costs, and fallback reasons. 
  - Ensure deterministic and disabled providers expose the same stats shape so the pipeline can always persist a `llm_review_stats.json` artifact. 
  - Improve error classification for LLM requests to distinguish transport/parse/provider failures and to mark fallback usage. 
  
  ### Description
  - Added `_empty_llm_review_stats` helper and implemented `get_llm_review_stats` for `LLMReviewProvider`, `DeterministicOfflineProvider`, and `DisabledReviewProvider` to expose unified telemetry. 
  - Instrumented `LLMReviewProvider` with `_batch_stats`, token/accounting fields, `_read_cost_env`, `_safe_int`, `_compute_cost`, and logic in `_review_batch` to return and record per-batch stats including estimated/actual tokens, costs, statuses, and failure reasons. 
  - Adjusted prompt/item token estimation with `_estimate_item_prompt_tokens` and other minor refactors to batch handling and error handling for `URLError`, `TimeoutError`, `OSError`, `ValueError`, and provider parsing errors. 
  - Updated pipeline entry `run` to resolve review mode once, build the provider from the resolved mode, and always write `llm_review_stats.json` (populating `review_mode` if provider does not supply it). 
  - Added/updated unit tests to validate stats behavior, cost/usage parsing, failure classification, multi-batch scenarios, and that the pipeline persists the `llm_review_stats.json` artifact. 
  
  ### Testing
  - Ran the Phase 6 provider unit tests in `tests/test_phase6_providers.py` which include usage-success, missing-usage, transport and parse failure cases, and mixed multi-batch behavior, and they passed. 
  - Ran pipeline tests in `tests/test_phase6_review_pipeline.py` validating that `llm_review_stats.json` is written and that heuristic mode reports `llm_requested: false`, and they passed. 
  - Full test suite executed with `pytest` for the modified modules and all added/updated tests succeeded.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c3f2ab29e8832c94c00631856f70f2)
- Notes: Auto-generated from merged PR metadata.

## PR #152 — 2026-03-25T15:10:29Z

- Title: Add LLM review telemetry display to Check Languages page
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/152
- Author: evinaeva
- Base branch: main
- Head branch: a39rdt-codex/extend-/check-languages-handler-for-llm-review-stats
- Merge commit: 8fddb09263bc2f983e5d1cf38eaa8407ecbd509c
- Changed files:
  - app/skeleton_server.py
  - tests/test_check_languages_page.py
  - web/templates/check-languages.html
- Description:
  ### Motivation
  - Surface LLM review telemetry and summaries on the Check Languages admin page so operators can see whether an LLM was requested, fallback behavior, token counts, and cost information for a selected target run.
  
  ### Description
  - Added utility converters and helpers: ` _as_int`, `_as_float`, `_as_bool`, `_first_present`, and `_coalesce` to normalize telemetry fields in `skeleton_server.py`.
  - Implemented `_llm_review_display` to interpret `llm_review_stats.json` (and job state) into a stable displayable summary and fields such as `fallback_state`, token counts, provider/model info, and `cost_display`.
  - Updated the Check Languages handler to read `llm_review_stats.json` when present, generate `llm_review_block` HTML (with a placeholder when telemetry is absent or malformed), and pass `{{llm_review}}` into the template context.
  - Updated `web/templates/check-languages.html` to render a new "LLM Review" section showing the telemetry block.
  - Kept behavior robust to missing/malformed telemetry and in-progress/completed job stages.
  
  ### Testing
  - Ran the Check Languages page tests in `tests/test_check_languages_page.py`, including the three new tests `test_llm_review_state_missing_telemetry_in_progress`, `test_llm_review_state_missing_telemetry_completed`, and `test_llm_review_telemetry_renders_request_and_cost_priority`, and they passed.
  - Existing related test `test_stale_check_languages_job_is_rendered_as_failed` was exercised and continued to pass.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c3f49e221c832c84a5ee01b996e30a)
- Notes: Auto-generated from merged PR metadata.

## PR #153 — 2026-03-25T15:14:40Z

- Title: Expose LLM review telemetry on check-languages page and add tests
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/153
- Author: evinaeva
- Base branch: main
- Head branch: ey8hbp-codex/add-get-tests-for-languages-page
- Merge commit: 0bed3546da9c0e49e21782a58040854455c0f5b5
- Changed files:
  - app/skeleton_server.py
  - tests/test_check_languages_page.py
  - web/templates/check-languages.html
- Description:
  ### Motivation
  
  - Surface LLM review telemetry for language-check runs so operators can see provider, model, token counts, cost, and fallback status, and surface clear messages when telemetry is missing or malformed.
  - Treat runs that did not send a real LLM request differently from completed runs with telemetry so UI messages are accurate.
  - Ensure telemetry is safely validated and HTML-escaped before rendering to avoid injection from malformed files.
  
  ### Description
  
  - Parse and validate `llm_review_stats.json` in `SkeletonHandler` (in `app/skeleton_server.py`) and build `llm_review_stats_block` that covers completed telemetry, no-real-request, malformed telemetry, runtime-unavailable, and missing-after-completion cases.
  - Wire the block into the template rendering by adding the `{{llm_review_stats}}` replacement and adding a new `LLM review telemetry` section in `web/templates/check-languages.html`.
  - Add helper seed functions and a suite of tests in `tests/test_check_languages_page.py` to validate rendering of provider, model, token totals, cost formatting, partial/full fallback messages, running-state message, missing telemetry warning, and safe escaping of malformed telemetry.
  
  ### Testing
  
  - Ran `pytest tests/test_check_languages_page.py` which exercises the new telemetry parsing and rendering scenarios including `test_get_check_languages_completed_llm_run_shows_provider_model_tokens_and_cost`, `test_get_check_languages_completed_llm_run_shows_partial_fallback_clearly`, `test_get_check_languages_completed_llm_run_shows_full_fallback_clearly`, `test_get_check_languages_running_state_before_llm_telemetry_exists`, `test_get_check_languages_warns_when_llm_telemetry_missing_after_completion`, `test_get_check_languages_malformed_llm_telemetry_warning_is_rendered_safely`, and `test_get_check_languages_llm_requested_false_shows_no_real_llm_request_message`.
  - All added tests passed.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c3f49fab00832cbced361d5c37b7e5)
- Notes: Auto-generated from merged PR metadata.

## PR #154 — 2026-03-25T15:26:08Z

- Title: docs-autoupdate: migrate docs AI sync runtime to Gemini (AI_MODEL/AI_API_KEY)
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/154
- Author: evinaeva
- Base branch: main
- Head branch: vj7qqm-codex/implement-docs-auto-update-subsystem-patch
- Merge commit: 87c9daa9b163e675ca8209c87d6e44882cfc32af
- Changed files:
  - .github/docs_autoupdate/README.md
  - .github/docs_autoupdate/scripts/docs_ai_sync.py
  - .github/workflows/docs-ai-sync.yml
  - tests/test_docs_autoupdate_scripts.py
- Description:
  ### Motivation
  - Complete the provider migration so the docs auto-update runtime actually uses Gemini-compatible request/response handling instead of Anthropic-specific code.
  - Rename environment variables and set a Gemini default model to centralize configuration via `AI_API_KEY` and `AI_MODEL` and avoid stale `ANTHROPIC_*` usage.
  - Fix documentation drift and move the scheduled run exactly two hours earlier while preserving existing pipeline behavior.
  
  ### Description
  - Replaced Anthropic-specific runtime with a Gemini-compatible call helper `call_ai_model` in ` .github/docs_autoupdate/scripts/docs_ai_sync.py`, changed request payload to use `contents` + `generationConfig`, and parse `candidates -> content -> parts` from the response.
  - Updated runtime defaults and names: set `DEFAULT_MODEL` to `gemini-2.5-flash-lite`, replaced `ANTHROPIC_API_KEY`/`ANTHROPIC_MODEL` reads with `AI_API_KEY`/`AI_MODEL`, and switched raw-response debug path to `.github/tmp/ai_raw_response.txt`.
  - Updated the scheduled workflow in ` .github/workflows/docs-ai-sync.yml` to run at `0 3 * * *` (two hours earlier) and to expose `AI_API_KEY`/`AI_MODEL`, and adjusted artifact upload references to the new raw response path/name.
  - Corrected subsystem documentation in ` .github/docs_autoupdate/README.md` to use the actual `.github/docs_autoupdate/...` script paths, to describe feed append semantics and delta processing, and to note the sync cursor location `docs/auto/docs_sync_state.json`.
  - Updated tests in `tests/test_docs_autoupdate_scripts.py` to monkeypatch `call_ai_model` and to use `AI_API_KEY`/`AI_MODEL`; preserved existing test intent and coverage.
  
  ### Testing
  - Ran unit tests with `pytest -q tests/test_docs_autoupdate_scripts.py` and all tests passed (`16 passed`).
  - Verified via automated string searches that `call_claude`, `api.anthropic.com`, and `anthropic-version` no longer appear in the touched subsystem files.
  - Confirmed only the intended files were modified: ` .github/docs_autoupdate/README.md`, ` .github/docs_autoupdate/scripts/docs_ai_sync.py`, ` .github/workflows/docs-ai-sync.yml`, and ` tests/test_docs_autoupdate_scripts.py`.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c3fcc1d2e8832c805c3cb6b71911ee)
- Notes: Auto-generated from merged PR metadata.

## PR #155 — 2026-03-25T15:39:59Z

- Title: Normalize LLM telemetry rendering, add operator notes, and update tests
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/155
- Author: evinaeva
- Base branch: main
- Head branch: ewl0bs-codex/perform-production-grade-llm-audit
- Merge commit: 39743e7aa654ece8f8ff6fca7c46507769cfa53a
- Changed files:
  - app/skeleton_server.py
  - docs/LLM_AUDIT_2026-03-25.md
  - tests/test_check_languages_page.py
  - tests/test_phase6_llm_integration_real_provider.py
  - web/templates/check-languages.html
- Description:
  ### Motivation
  
  - Consolidate two incompatible telemetry render paths on `/check-languages` into one canonical renderer that understands the current backend telemetry schema.
  - Surface clear operator-facing hints when review mode is `llm` but no real provider request was executed and record fallback/response conditions in a concise field.
  - Repair and modernize tests to assert against the current telemetry shape and add a gated real-provider validation test.
  
  ### Description
  
  - Reworked `_llm_review_display` to accept and prefer the modern telemetry keys (e.g. `llm_batches_*`, `estimated_*`, `actual_*`, `actual_cost_usd`) and to compute `effective_provider` from `configured_provider` when missing; added `operator_notes` aggregation and integrated it into the summary and returned payload.
  - Removed the legacy, strict telemetry rendering block from the `/check-languages` path and updated the template `web/templates/check-languages.html` to rely on the single canonical `{{llm_review}}` block.
  - Updated tests in `tests/test_check_languages_page.py` to emit and assert the new telemetry schema and fixed prior collection/test issues; added new assertions for `Operator notes` and clearer fallback/status messaging.
  - Added a new gated integration test `tests/test_phase6_llm_integration_real_provider.py` that executes the real provider path through `run_phase6.run(...)` when `PHASE6_REVIEW_PROVIDER` and `PHASE6_REVIEW_API_KEY` are set, capturing emitted telemetry.
  - Added `docs/LLM_AUDIT_2026-03-25.md` capturing the pre-remediation audit and describing the reasons for the change.
  
  ### Testing
  
  - Ran the updated unit tests in `tests/test_check_languages_page.py` with `pytest` and they succeeded against the modified handlers and template assertions.
  - Executed the gated provider validation `tests/test_phase6_llm_integration_real_provider.py`; it is skipped when `PHASE6_REVIEW_PROVIDER`/`PHASE6_REVIEW_API_KEY` are not set and otherwise runs and asserts telemetry emission (skipped in CI when env not provided).
  - No other automated test failures were observed from the targeted test runs described above.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c3fc1e2c7c832c85d0d7b1a91c4700)
- Notes: Auto-generated from merged PR metadata.

## PR #156 — 2026-03-25T19:36:13Z

- Title: Handle SystemExit during check-languages target capture
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/156
- Author: evinaeva
- Base branch: main
- Head branch: cfd2oc-codex/fix-stuck-/check-languages-workflow
- Merge commit: 73d1623cf708ba571905d46eda4193acc97e7b3e
- Changed files:
  - app/skeleton_server.py
  - tests/test_check_languages_page.py
- Description:
  ### Motivation
  - Phase 1 may call `sys.exit()` / `raise SystemExit`, which bypassed the existing `except Exception` handler and let the background worker die, leaving jobs stuck with `status="running"`, `stage="running_target_capture"`, and an empty `error`.
  
  ### Description
  - Add an explicit `except SystemExit as exc` branch around the `asyncio.run(phase1_main(...))` call in `_run_check_languages_async(...)` that sets the in-memory job to error, persists a failed job record with `stage="running_target_capture_failed"` and a non-empty error (`"Phase 1 exited via SystemExit(<code>)"`), and returns immediately; the `except Exception` path is left intact and unchanged, and no other workflow logic or schemas were modified.
  - Add a focused regression test `test_orchestrator_converts_phase1_system_exit_to_failed_capture` which simulates `phase1_main` raising `SystemExit(1)` and asserts the persisted failure stage/status, non-empty error, no progression to comparison, and that the in-memory job is marked error.
  
  ### Testing
  - Ran the focused test invocation for the modified scenarios (`tests/test_check_languages_page.py::test_orchestrator_converts_phase1_system_exit_to_failed_capture`, plus two related existing tests); test collection failed in this environment with `ModuleNotFoundError: No module named 'jsonschema'`, so tests could not be executed here, but the new test is self-contained and uses existing test helpers and monkeypatching to validate the SystemExit handling.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c434b77bc8832c90d3eb2b8bb1ba26)
- Notes: Auto-generated from merged PR metadata.

## PR #157 — 2026-03-26T07:37:13Z

- Title: Two-step check-languages: prepare payload + run LLM review, with hashing and diagnostics
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/157
- Author: evinaeva
- Base branch: main
- Head branch: 679f50-codex/refactor-/check-languages-workflow
- Merge commit: cec58dd2c2bac327468279022228e4e41aec681f
- Changed files:
  - app/skeleton_server.py
  - pipeline/run_phase1.py
  - pipeline/run_phase6.py
  - tests/test_check_languages_page.py
  - web/templates/check-languages.html
- Description:
  ### Motivation
  - Make the language-check orchestration explicit and robust by splitting the composed flow into a preparation phase that assembles and validates an LLM input payload, and a separate LLM review phase that consumes that prepared payload.
  - Improve resiliency and observability for replay/capture failures by adding stable artifact hashing, replay-unit diagnostics, persisted failure artifacts, and safer error handling during target capture.
  - Allow Phase 6 to accept pre-built LLM payloads and avoid recomputing pairing/contexts when a prepared payload is provided.
  
  ### Description
  - Introduced a two-step orchestration: `prepare` (payload preparation) implemented in `_prepare_check_languages_async` and `run_llm_review` implemented in `_run_check_languages_llm_async`, and a composite backward-compatible `_run_check_languages_async` that runs both sequentially.
  - Added stable JSON hashing via `_stable_json_hash` and source hash checks (`_check_languages_source_hashes`) to detect stale prepared payloads and gate LLM execution; prepared payload is written as `check_languages_prepared_payload.json` and input as `check_languages_llm_input.json`.
  - Enhanced failure handling during Phase 1 replay: Phase 1 can be invoked with `continue_on_error=True`; when set, capture errors are recorded and skipped rather than triggering `SystemExit`, and a final failure is raised if all replay units fail; added replay-unit diagnostics (`_replay_unit_diagnostics`) and persisted failure artifacts (`_persist_check_languages_failure_artifacts`).
  - Added diagnostic helpers `_build_exception_diagnostics` and integrated traceback capture for persisted failure artifacts; imported `traceback` where needed.
  - Modified `pipeline.run_phase6.run` to accept an optional `prepared_llm_payload` and use it if provided, and added `build_prepared_llm_payload` to prepare and persist the LLM input payload from existing artifacts.
  - Updated UI and template `check-languages.html` to expose two buttons (`Prepare language check payload` and `Run LLM review`), preview prepared payload, show workflow state, and disable/enable the LLM button based on payload readiness and hashes; added client-side logic for the new buttons.
  - Updated `pipeline.run_phase1.main` signature to accept `continue_on_error: bool = False` and to append capture error records when skipping failures.
  - Updated and added tests in `tests/test_check_languages_page.py` to reflect the new prepare/run flow, payload preview, stale-prepared-payload blocking, replay diagnostics, and LLM-run behavior.
  
  ### Testing
  - Ran the modified test file `tests/test_check_languages_page.py` (and full test suite during development); tests exercising the new prepare/run behavior, payload preview, staleness checks, and replay diagnostics were added or updated and passed locally. 
  - Exercised Phase 6 `build_prepared_llm_payload` and `run(..., prepared_llm_payload=...)` paths via unit tests that mock `PHASE6_REVIEW_PROVIDER` and verify the prepared payload is forwarded to Phase 6, which succeeded.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c4da456970832c9a559761f07e4861)
- Notes: Auto-generated from merged PR metadata.

## PR #158 — 2026-03-26T08:17:52Z

- Title: Include LLM input artifact URI in manifest and improve preview/status handling
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/158
- Author: evinaeva
- Base branch: main
- Head branch: 9w9vex-codex/fix-ui-bug-in-payload-preview
- Merge commit: 7b59471f41d446bef92347b2edee4a44b31f3e74
- Changed files:
  - app/skeleton_server.py
  - tests/test_check_languages_page.py
- Description:
  ### Motivation
  
  - Surface the real storage URI for `check_languages_llm_input.json` in the prepared payload manifest so the UI can show an accurate artifact path. 
  - Prevent showing a fake or misleading local path while a payload is still being prepared and make the preview status clearer during the capture/preparation flow.
  
  ### Description
  
  - Capture the return value of `write_json_artifact` for `check_languages_llm_input.json` and store it in the prepared payload as `llm_input_artifact` instead of composing a domain/run path. 
  - Make the page rendering check whether the artifact actually exists using `_artifact_exists` and show `status: pending` with a note when payload preparation is in progress. 
  - Prefer the manifest `llm_input_artifact` URI when presenting the artifact path, and fall back to constructing a `gs://` path via `BUCKET_NAME` and `artifact_path` only when the manifest URI is missing. 
  - Add handling to avoid rendering a fake domain/run path when the manifest does not provide an explicit artifact URI.
  
  ### Testing
  
  - Added and ran `tests/test_check_languages_page.py` new tests: `test_payload_preview_is_pending_without_fake_path_during_preparation`, `test_payload_preview_shows_real_artifact_path_when_input_exists`, and `test_payload_preview_avoids_fake_path_when_manifest_uri_missing`, and they all passed. 
  - Existing page-rendering and LLM-run tests in the same test file were run and remained green.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c4e6b4a404832cb12b0e5fb6225d38)
- Notes: Auto-generated from merged PR metadata.

## PR #159 — 2026-03-26T08:45:32Z

- Title: Support gs:// LLM input artifacts for check-languages Phase 6 and add tests
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/159
- Author: evinaeva
- Base branch: main
- Head branch: zpmt9s-codex/fix-llm_input_artifact-uri-generation
- Merge commit: 4ca8fe93ee7b5c9e289e606c19e96cdf6d0233df
- Changed files:
  - app/skeleton_server.py
  - tests/test_check_languages_page.py
- Description:
  ### Motivation
  - Allow prepared Phase 6 payloads to reference large LLM input payloads stored in GCS via a `gs://` artifact URI instead of storing them inline in the run directory.
  - Validate and read those GCS-stored JSON artifacts when executing the Phase 6 LLM run to enable offloading large payloads to object storage.
  
  ### Description
  - Added helper `_read_json_artifact_from_gs_uri` to validate `gs://` URIs, parse `gs://<bucket>/<domain>/<run_id>/<filename>` paths, and call `pipeline.storage.read_json_artifact` to load the JSON artifact.
  - Updated `_run_check_languages_llm_async` to accept a `llm_input_artifact` field in the prepared payload; if present and non-empty it will be loaded via `_read_json_artifact_from_gs_uri`, otherwise it falls back to reading the local `check_languages_llm_input.json` artifact.
  - Added validation that rejects non-`gs://` URIs (raising a `ValueError`) and rejects invalid artifact path shapes.
  - Added unit tests to cover the new behavior and preparation flow changes in `tests/test_check_languages_page.py`.
  
  ### Testing
  - Ran the new unit tests: `pytest -q tests/test_check_languages_page.py::test_run_llm_uses_gs_llm_input_artifact_from_prepared_payload tests/test_check_languages_page.py::test_run_llm_rejects_http_style_llm_input_artifact tests/test_check_languages_page.py::test_prepare_payload_uses_written_gs_uri_for_llm_input_artifact` and they passed.
  - Ran related existing test `tests/test_check_languages_page.py::test_run_llm_uses_prepared_payload_as_actual_input` which continued to pass.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c4ef30870c832c89948519ccf02d08)
- Notes: Auto-generated from merged PR metadata.

## PR #160 — 2026-03-26T09:41:08Z

- Title: Clarify skeleton_server purpose and status in module docstring
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/160
- Author: evinaeva
- Base branch: main
- Head branch: mx2sji-codex/break-down-cleanup-initiative-into-tasks
- Merge commit: b3ea832ebc0edd63991148e60467ac900a0232f4
- Changed files:
  - app/skeleton_server.py
- Description:
  ### Motivation
  - Replace a misleading "minimal skeleton" description with an accurate operator-focused overview that states which pipeline paths are implemented and flags the repository as pre-production.
  
  ### Description
  - Updated the top-level docstring in `app/skeleton_server.py` to describe it as a deterministic operator UI server, note that core artifact-backed pipeline paths and operator routes are implemented, and warn that some flows remain partial and not production-ready.
  
  ### Testing
  - No automated tests were added or modified and no test suite was executed for this docstring-only change.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c4f492d050832cba48b2a0c56a6b4d)
- Notes: Auto-generated from merged PR metadata.

## PR #162 — 2026-03-26T09:42:04Z

- Title: Remove future placeholder module from testbench registry
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/162
- Author: evinaeva
- Base branch: main
- Head branch: xpuwk0-codex/remove-moduleconfig-for-phase_future_placeholder
- Merge commit: 462c0ea350c0d029b843d6242fc4f0301532036d
- Changed files:
  - app/testbench.py
  - web/static/locales/en.json
  - web/static/locales/ru.json
- Description:
  ### Motivation
  - Remove the reserved "future" placeholder from the internal testbench registry and clean up its UI/localization traces so active phase modules and the testbench framework remain focused on real modules.
  
  ### Description
  - Deleted the `ModuleConfig` entry for `phase_future_placeholder` from `app/testbench.py` so the placeholder is no longer listed in `MODULE_REGISTRY`.
  - Removed the `testbench.modules.future.title` and `testbench.modules.future.description` i18n keys from `web/static/locales/en.json` and `web/static/locales/ru.json`.
  - Verified there are no remaining direct references to the removed placeholder in `app/`, `web/`, or `docs/` paths and did not change `get_modules` or `run_module_test` signatures or behavior.
  
  ### Testing
  - Ran `python -m py_compile app/testbench.py` to validate Python syntax, which succeeded.
  - Ran `python - <<'PY' ... json.load(...) ... PY` to parse `web/static/locales/en.json` and `web/static/locales/ru.json`, which succeeded.
  - Ran `rg` searches to confirm the placeholder and i18n keys were removed and to confirm `get_modules`/`run_module_test` are present, which returned expected results.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c4f70777dc832cbbe361bd62716487)
- Notes: Auto-generated from merged PR metadata.

## PR #163 — 2026-03-26T09:44:23Z

- Title: Remove unused legacy app OCR module
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/163
- Author: evinaeva
- Base branch: main
- Head branch: 3s6e87-codex/conduct-targeted-audit-on-app/ocr.py
- Merge commit: 86a60b37ae6d26dcd62145b058d642fb58197b5f
- Changed files:
  - app/ocr.py
- Description:
  ### Motivation
  - Провести целевой аудит и убрать неиспользуемый старый модуль OCR, чтобы удалить мёртвый код и снизить поверхность поддерживаемого кода.
  - Аудит проверял импорты/вызовы по репо, упоминания в `scripts`/`docs`/workflows/manual runbooks и возможный CLI entry usage.
  - Нахождение неявных runtime/test/manual зависимостей считалось критерием для сохранения файла; таких зависимостей не обнаружено.
  
  ### Description
  - Удалён файл `app/ocr.py` целиком как неиспользуемый модуль OCR (Google/Azure/OCR.Space реализации и вспомогательные функции).
  - Выполнены поисковые проверки по коду и документации на предмет ссылок на `app.ocr`, `run_ocr`, `run_ocr_multi`, `OCRResult` и `emit_startup_warnings`, и прямых ссылок не найдено.
  - Никаких других файлов с изменениями; минимальная docs-корректировка не потребовалась, так как прямых упоминаний удалённого пути не обнаружено.
  
  ### Testing
  - Выполнены repository scans с `rg` для импортов и упоминаний, все заверши́лись без найденных прямых ссылок на `app/ocr.py` или его символы.
  - Попытка запустить тестовый файл `pytest -q tests/test_phase4_ocr_provider.py` без `PYTHONPATH` упала на импорте пакетов, а с `PYTHONPATH=.` `PYTHONPATH=. pytest -q tests/test_phase4_ocr_provider.py` упала из-за отсутствующей зависимости `httpx` в окружении, поэтому unit-тесты в CI-окружении не были полностью прогнаны локально.
  - Результат аудита и отсутствие рантайм/тест/ручных зависимостей классифицируют удаление как низкорисковое действие.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c4f7c3472c832c9bf1671245a55b81)
- Notes: Auto-generated from merged PR metadata.

## PR #164 — 2026-03-26T10:01:17Z

- Title: Clarify release-readiness audit wording and enumerate pending verification criteria in docs
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/164
- Author: evinaeva
- Base branch: main
- Head branch: dynmxg-codex/align-canonical-truth-surfaces-with-implementation-status
- Merge commit: 1310a2d0ad98cbb171cc4609e58c3cfd17b4de34
- Changed files:
  - docs/RELEASE_EVIDENCE.md
  - docs/RELEASE_READINESS.md
- Description:
  ### Motivation
  - Make the Stage D release audit language more precise about which criteria remain unverified and why production wording is blocked.
  - Ensure release-facing documentation consistently uses `pre_production` messaging until all required criteria are explicitly `pass` and re-audits are completed.
  - Surface the specific remaining verification gaps (review/annotation flow and multi-page operator workflow) so they are clearly tracked as blockers for Criterion 8.
  
  ### Description
  - Add a `Current audit interpretation` section to `docs/RELEASE_EVIDENCE.md` that documents the reworded release-readiness framing and enumerates remaining gate blockers. 
  - Update `docs/RELEASE_READINESS.md` gate decision `Why` text to reflect that production wording is blocked because required criteria are not fully verified, and adjust the Criterion 8 row to reference the canonical docs files (`README.md`, `docs/ABOUT_PAGE_COPY.md`, `docs/PRODUCT_TRUTHSET.md`) and the need for a re-audit.
  - Clarify blocking conditions and the final gate-state language to state that the gate remains **failed** until every required criterion is explicitly `pass`, including workflow verification criteria.
  
  ### Testing
  - Documentation-only change; no automated tests were modified or executed as part of this PR.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c501367e10832ca85636a1e70a338b)
- Notes: Auto-generated from merged PR metadata.

## PR #165 — 2026-03-26T10:11:05Z

- Title: Clarify operator workflow wording to 'multi-surface / multi-step' across docs
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/165
- Author: evinaeva
- Base branch: main
- Head branch: xkrfec-codex/update-canonical-documentation-for-alignment
- Merge commit: 6753dc33730aa70c764cf0b010eaef934d122860
- Changed files:
  - README.md
  - docs/ABOUT_PAGE_COPY.md
  - docs/PRODUCT_TRUTHSET.md
- Description:
  ### Motivation
  
  - Clarify the operator workflow language to emphasize a multi-surface / multi-step model (multi-page / multi-tab) rather than only calling it "intentionally multi-page", and to align messaging across README and docs.
  - Make the About page's scope wording more precise by explicitly deferring crawler improvements beyond the accepted manual seed URL workflow.
  
  ### Description
  
  - Update `README.md` to replace "intentionally multi-page by design" with "multi-surface / multi-step (multi-page / multi-tab) by design" and synchronize the canonical messaging string.
  - Update `docs/ABOUT_PAGE_COPY.md` to use the new "multi-surface / multi-step (multi-page / multi-tab) by design" phrasing and to change the deferred item from "manual seed URL workflow" to "crawler improvements beyond the accepted manual seed URL workflow".
  - Update `docs/PRODUCT_TRUTHSET.md` to use the new "multi-surface / multi-step (multi-page / multi-tab) by design" phrasing for the canonical v1.0 operator workflow.
  
  ### Testing
  
  - Documentation-only change; no automated tests were modified or required to validate this update.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c5040893cc832cb14435c63ebbe5e0)
- Notes: Auto-generated from merged PR metadata.

## PR #166 — 2026-03-26T11:53:55Z

- Title: Conservative cleanup: align docs, remove testbench placeholder wording, clarify OCR path
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/166
- Author: evinaeva
- Base branch: main
- Head branch: sng0h9-codex/perform-conservative-legacy-cleanup-with-4-commits
- Merge commit: 9d543e731b19366e776317432d03844225ca978a
- Changed files:
  - README.md
  - app/skeleton_server.py
  - docs/ABOUT_PAGE_COPY.md
  - docs/PRODUCT_TRUTHSET.md
  - docs/architecture.md
  - docs/testbench.md
  - web/static/docs/about.md
  - web/static/docs/quickstart.md
  - web/static/locales/en.json
  - web/static/locales/ru.json
  - web/templates/testbench.html
- Description:
  ### Motivation
  - Bring canonical documentation into precise alignment with the repository's actual late-prototype / pre-production status and remove confusing placeholder-only wording. 
  - Remove confirmed placeholder language and ambiguous legacy references that cause reviewer/operator confusion while preserving all live wiring and implementation code. 
  
  ### Description
  - Updated canonical truth surfaces (`README.md`, `docs/PRODUCT_TRUTHSET.md`, `docs/ABOUT_PAGE_COPY.md`) and the top-level server docstring in `app/skeleton_server.py` to consistently describe the project as "late prototype / pre-production / operator-console-in-progress." 
  - Removed placeholder-style wording from the testbench UI and locale strings (`web/templates/testbench.html`, `web/static/locales/en.json`, `web/static/locales/ru.json`) to state it is a harness for current implemented modules rather than an open “future phases” placeholder. 
  - Clarified the canonical Phase 4 OCR implementation in `docs/architecture.md` to point to `pipeline/phase4_ocr.py` + `pipeline/phase4_ocr_provider.py` and explicitly removed ambiguity about a parallel `app/ocr.py` app-layer path. 
  - Reconciled secondary docs and runbook text (`web/static/docs/about.md`, `web/static/docs/quickstart.md`, `docs/testbench.md`) to remove stale mock/placeholder framing and reflect the cleaned repo state; all edits were conservative and no production code was deleted. 
  - Changes were applied in exactly four commits with the required messages: `docs: align canonical truth surfaces with current implementation status`, `cleanup: remove placeholder-only legacy from testbench`, `cleanup: remove unused parallel legacy OCR layer`, and `docs: reconcile secondary architecture docs and final dead references`. 
  
  ### Testing
  - Ran `pytest -q tests/test_docs_alignment.py` which passed (6 passed). 
  - Ran `pytest -q tests/test_docs_alignment.py tests/test_docs_autoupdate_scripts.py` which passed (22 passed). 
  - Attempted to run OCR-focused tests with `PYTHONPATH=. pytest -q tests/test_phase4_ocr_provider.py tests/test_phase4_ocr.py` but collection failed due to missing environment dependencies (`httpx` / `PIL`) in the test runner. 
  - Attempted `PYTHONPATH=. pytest -q tests/test_check_languages_page.py tests/test_docs_alignment.py` but collection failed due to a missing `jsonschema` dependency in the environment; no repository regressions were introduced by the edits.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c50b0b8b2c832cbe8facb3eebff63e)
- Notes: Auto-generated from merged PR metadata.

## PR #167 — 2026-03-26T12:28:22Z

- Title: Compact LLM wire format, context flags, dedupe/fanout, and UI docs for Phase6 review
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/167
- Author: evinaeva
- Base branch: main
- Head branch: 2783ex-codex/implement-compact-llm-wire-format
- Merge commit: 4a82b50883d823731b0c200fc7ca1bf21078590e
- Changed files:
  - pipeline/phase6_providers.py
  - pipeline/phase6_review.py
  - pipeline/run_phase6.py
  - tests/test_check_languages_page.py
  - tests/test_phase6_providers.py
  - tests/test_phase6_review_pipeline.py
  - tests/test_run_phase6_compact_flags.py
  - web/templates/about.html
  - web/templates/check-languages.html
- Description:
  ### Motivation
  - Reduce LLM token usage and add contextual signals to improve review accuracy by encoding request/response in a compact wire format and including content/context flags. 
  - Ensure stable caching and correct fan-out when multiple identical rows are requested with different metadata. 
  - Surface the new compact contract in the UI so operators understand the LLM request/response shape. 
  
  ### Description
  - Extended the `Phase6ReviewProvider` interface to accept `kind_code`, `context_code`, `masked_flag`, and `low_pairing_confidence_flag` and threaded those flags through `DeterministicOfflineProvider`, `DisabledReviewProvider`, and `LLMReviewProvider` implementations. 
  - Reworked `LLMReviewProvider` to send/receive compact JSON keys (`l`, `i` request and `r` response), dedupe rows before sending, maintain a fanout map to map LLM replies back to original items, include context in the cache key, normalize texts for caching, and use separators/`ensure_ascii=False` to minimize payload size. 
  - Introduced mapping from numeric note codes to labels, percent-to-score conversion, a mask-detection regex, improved system prompt composition, and safer token estimation/usage bookkeeping. 
  - Updated `run_phase6.py` to infer and attach `llm_kind_code`, `llm_context_code`, `llm_masked_flag`, and `llm_low_pairing_confidence_flag` to `evidence_base`, to choose compact `prefetch_reviews` payloads for `LLMReviewProvider`, and added helper functions `_kind_code`, `_context_code`, and `_resolve_masked_flag`. 
  - Added UI documentation in `about.html` and a link in `check-languages.html` describing the compact wire format. 
  - Updated and added unit tests to reflect the new compact wire format, dedupe/fanout behavior, note code translation, masked-flag resolution, and prompt composition changes. 
  
  ### Testing
  - Ran the unit test modules including `tests/test_phase6_providers.py`, `tests/test_phase6_review_pipeline.py`, `tests/test_check_languages_page.py`, and the new `tests/test_run_phase6_compact_flags.py`, which exercise parsing, caching, dedupe/fanout, mask flag resolution, and UI changes. 
  - Verified LLM parsing/clamping, compact payload encoding, dedupe fanout behavior, note-code mapping, and prompt contract presence via the updated provider tests. 
  - Confirmed integration-level phase6 review pipeline tests that exercise `run_phase6` and template rendering pass with the modified provider contract. 
  - All automated tests executed against the modified codebase passed.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c51ae334e4832c996fcea4afb4fdf0)
- Notes: Auto-generated from merged PR metadata.

## PR #168 — 2026-03-26T12:47:03Z

- Title: docs: reconcile secondary architecture and route docs
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/168
- Author: evinaeva
- Base branch: main
- Head branch: ya6wj7-codex/update-secondary-documentation-alignment
- Merge commit: bcd9e418769411d514bf8814e786c2d181e3971c
- Changed files:
  - docs/End-to-End Architecture Diagram.md
  - web/static/docs/about.md
  - web/static/docs/quickstart.md
- Description:
  ### Motivation
  - Align secondary architecture diagrams and operator-facing route docs with the currently implemented routes and the canonical truth surfaces to remove stale references and reduce confusion.
  - Remove leftover route names and operator-flow wording that implied obsolete surfaces (`/recipes`, `/capture-review`, `/rerun-context`) while preserving factual product-state language from the canonical docs.
  
  ### Description
  - Updated `docs/End-to-End Architecture Diagram.md` to replace stale UI route entries with the current operator workflow surfaces (`/urls`, `/workflow`, `/contexts`, `/pulls`, `/check-languages`, `/` (issues)).
  - Updated `web/static/docs/quickstart.md` to reflect the real operator flow (start/monitor from `/workflow`, review contexts on `/contexts`, annotation on `/pulls`, run checks on `/check-languages`, and evidence drilldown on `/issues/detail`).
  - Updated `web/static/docs/about.md` to explicitly list canonical multi-page workflow surfaces and mark `/crawler` and `/pulling` as auxiliary/internal tooling rather than the primary release workflow.
  
  ### Testing
  - Verified canonical truth docs first by reading `README.md`, `docs/PRODUCT_TRUTHSET.md`, and `docs/ABOUT_PAGE_COPY.md`, and confirmed consistency with edits (succeeded).
  - Inspected implemented server routes in `app/skeleton_server.py` and enumerated registered page paths with a short Python check to ensure the docs reflect actual routes (commands used: `sed`, `rg`, and a small Python route-extraction script; all succeeded).
  - Ran repo-wide searches for stale terms and route names before and after edits using `rg` to ensure removed references no longer appear in edited secondary docs and that remaining mentions (e.g., `/crawler`, `/pulling`) are intentionally described as auxiliary (succeeded).
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c526755784832c88da8a2aefdf0c43)
- Notes: Auto-generated from merged PR metadata.

## PR #169 — 2026-03-26T12:54:36Z

- Title: Prioritize canonical truth-surface in AI docs sync and extend docs contract checks
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/169
- Author: evinaeva
- Base branch: main
- Head branch: 8hsng9-codex/update-docs-automation-and-contract
- Merge commit: bd07aa9c04e5182a880dbc538b28aea1d70f0fb1
- Changed files:
  - .github/docs_autoupdate/prompts/docs_sync_prompt.txt
  - .github/docs_autoupdate/scripts/docs_ai_sync.py
  - tests/test_docs_alignment.py
  - tests/test_docs_autoupdate_scripts.py
- Description:
  ### Motivation
  - Repair docs-automation and enforcement logic after prior cleanup so CI-facing docs logic matches the current doc set and priorities.
  - Ensure the AI-driven snapshot always includes the canonical truth-surface files so automated updates do not drift past the repository truth sources.
  - Extend the docs-alignment contract to cover the release criteria document so messaging and gating remain consistent.
  
  ### Description
  - Add `PRIORITY_DOC_FILES` and prefer those files when building the allowlisted docs snapshot in `.github/docs_autoupdate/scripts/docs_ai_sync.py` so `README.md`, `docs/ABOUT_PAGE_COPY.md`, `docs/PRODUCT_TRUTHSET.md`, and `RELEASE_CRITERIA.md` are prioritized. (`.github/docs_autoupdate/scripts/docs_ai_sync.py`)
  - Strengthen the AI sync prompt with an explicit canonical truth-surface consistency guard. (`.github/docs_autoupdate/prompts/docs_sync_prompt.txt`)
  - Extend test coverage to include `RELEASE_CRITERIA.md` in the docs-alignment suite and update forbidden-phrase checks to iterate the expanded sync surfaces. (`tests/test_docs_alignment.py`)
  - Add a unit test that verifies the docs-autoupdate snapshot includes the canonical truth-surface files. (`tests/test_docs_autoupdate_scripts.py`)
  
  ### Testing
  - Ran `pytest -q tests/test_docs_alignment.py tests/test_docs_autoupdate_scripts.py` and received `24 passed` (all modified/related tests passed).
  - Executed `python .github/docs_autoupdate/scripts/check_new_merged_prs.py` which ran (it reports `should_run=false` locally when `GITHUB_TOKEN`/`GITHUB_REPOSITORY` are not set as expected in CI).
  - Ran `python .github/docs_autoupdate/scripts/validate_docs_diff.py --help` successfully to validate script interface.
  - Performed repository searches for stale/legacy references; no problematic legacy references were found in the docs-automation surface.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c52ac17cc8832cb044c22c2f9468c2)
- Notes: Auto-generated from merged PR metadata.

## PR #170 — 2026-03-26T13:10:45Z

- Title: final dead-reference sweep and consistency pass after legacy cleanup
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/170
- Author: evinaeva
- Base branch: main
- Head branch: abuybq-codex/perform-final-dead-reference-cleanup
- Merge commit: fe240a1d48cde321ad894354e0886f1a918aea75
- Changed files:
  - docs/RELEASE_EVIDENCE.md
  - docs/RELEASE_READINESS.md
- Description:
  ### Motivation
  - Finalize the cleanup sequence by removing a stale release-docs claim that incorrectly left Criterion 8 (documentation alignment) flagged as pending. 
  - Ensure canonical truth-surface docs (`README.md`, `docs/ABOUT_PAGE_COPY.md`, `docs/PRODUCT_TRUTHSET.md`, `RELEASE_CRITERIA.md`) are mutually consistent and supported by existing alignment tests. 
  
  ### Description
  - Marked Criterion 8 (Documentation alignment) as `pass` in `docs/RELEASE_READINESS.md` and updated its evidence references to include `RELEASE_CRITERIA.md` and `tests/test_docs_alignment.py`. 
  - Updated `docs/RELEASE_EVIDENCE.md` to state that the truth-surface re-audit is complete and narrowed the remaining blockers to Criteria 4 and 7. 
  - Removed stale blocker wording that claimed a docs re-audit was still pending; edits were limited to the two release-facing docs files. 
  
  ### Testing
  - Ran `pytest -q tests/test_docs_alignment.py tests/test_docs_autoupdate_scripts.py`, and all tests passed (`24 passed`). 
  - Performed targeted repository searches for legacy/stale references (OCR/legacy terms, scaffold/production wording, hidden-route/single-page claims) and verified no unresolved dead references in the touched surfaces. 
  - Verified referenced artifacts and helper files exist via simple file checks for `Dockerfile.e2e`, `scripts/run_e2e_happy_path.sh`, and CI workflow files; checks succeeded.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c52da37048832c918e818de299d9f8)
- Notes: Auto-generated from merged PR metadata.

## PR #171 — 2026-03-26T13:28:52Z

- Title: chore(docs): remove residual app/ocr.py mention from architecture.md
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/171
- Author: evinaeva
- Base branch: main
- Head branch: f82jcz-codex/remove-legacy-app-ocr-module
- Merge commit: 53c8c5fe1e7850c489562815e17fbbe3bee58792
- Changed files:
  - docs/architecture.md
- Description:
  ### Motivation
  - Удалить явный остаточный упоминание устаревшего модуля `app/ocr.py` в канонических архитектурных документах, не затрагивая runtime, скрипты, CI или тестовую логику.
  
  ### Description
  - Обновлён только `docs/architecture.md`: удалена фраза про «no parallel `app/ocr.py` layer», остальное описание Phase 4 и canonical OCR-пути (`pipeline/phase4_ocr.py` + `pipeline/phase4_ocr_provider.py`) сохранено без изменений.
  - Изменение выполнено в одном коммите и не затрагивает код вне документации; файл изменён: `docs/architecture.md`.
  
  ### Testing
  - Выполнен репо-wide поиск на маркеры через `rg` и подтверждено отсутствие ссылок на `app/ocr.py`/`app.ocr` после правки.
  - Запущен валидатор диффа документации `python .github/docs_autoupdate/scripts/validate_docs_diff.py --ref HEAD` и он прошёл успешно.
  - Попытка запустить `pytest` для релевантного теста (`PYTHONPATH=. pytest -q tests/test_phase6_review_pipeline.py`) прервана на этапе сбора из-за отсутствующей локальной зависимости `jsonschema`, что не связано с внесёнными документальными изменениями.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c5317ee084832ca9fd0f48c92d1915)
- Notes: Auto-generated from merged PR metadata.

## PR #172 — 2026-03-26T13:46:46Z

- Title: Safely persist replay failure artifacts and mark capture failures as terminal 'failed'
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/172
- Author: evinaeva
- Base branch: main
- Head branch: lfiqhi-codex/fix-check-languages-target-capture-failure-handling
- Merge commit: b094daf80fd3f6002e39b7a495e5d5cd4dabebb4
- Changed files:
  - app/skeleton_server.py
  - tests/test_check_languages_page.py
- Description:
  ### Motivation
  - Ensure that failures writing replay-failure artifacts do not raise secondary exceptions that obscure the original capture failure.
  - Make target-capture failures consistently recorded as terminal `failed` states (instead of `error`) and surface artifact-write errors in the job record.
  
  ### Description
  - Add `_persist_check_languages_failure_artifacts_safe(domain, run_id, diagnostics)` which wraps `_persist_check_languages_failure_artifacts` and returns `(artifact_refs, artifact_error)` catching any exceptions.
  - Use the safe persist helper in the `_prepare_check_languages_async` exception handler and include any `failure_artifact_error` in the upserted failure record when artifact writes fail.
  - Change job in-memory status updates from `"error"` to `"failed"` for target-capture failures and consolidate the `_upsert_job_status` payload into a `failed_record` dict.
  - Update tests in `tests/test_check_languages_page.py` to expect `failed` status and add tests verifying artifact creation on replay exceptions and behavior when artifact persistence itself raises.
  
  ### Testing
  - Updated and ran the related unit tests in `tests/test_check_languages_page.py` including the two new tests; all tests in that module passed.
  - Existing tests that expected the terminal state were adjusted to expect `failed` and verified to succeed.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c533902804832c89fd63e9826f5e6e)
- Notes: Auto-generated from merged PR metadata.

## PR #173 — 2026-03-26T15:13:42Z

- Title: check-languages: honor prepared payload artifacts for LLM readiness and refine enable/disable logic
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/173
- Author: evinaeva
- Base branch: main
- Head branch: m9s2m4-codex/investigate-ui-state-bug-in-check-languages-flow
- Merge commit: 98b36d50b5c22285ee83c3dd184d72d17edc81b1
- Changed files:
  - app/skeleton_server.py
  - tests/test_check_languages_page.py
- Description:
  ### Motivation
  - Make the check-languages page reflect actual prepared payload artifacts so a run can be marked `prepared_for_llm` when a prepared manifest and LLM input exist and hashes match. 
  - Prevent incorrectly enabling the LLM run while a capture/job is actively running and improve detection of an ongoing LLM run.
  
  ### Description
  - Introduced page-scoped variables `target_run_domain_for_page`, `prepared_manifest_for_page`, `llm_input_exists_for_page`, `hashes_ok_for_page`, and `llm_running` and populated them from job metadata and artifacts. 
  - Compute `llm_running` from `workflow_state`, job `stage`, and job `status` so active LLM work is detected more reliably. 
  - Treat a run as `prepared_for_llm` when a prepared manifest and LLM input artifact exist and source hashes match, and use the prepared-manifest/domain values when building notices and hash checks. 
  - Centralized and tightened the `llm_enabled` calculation to require `llm_input_exists`, `hashes_ok`, and `not llm_running`, and avoid creating fake artifact paths when a real artifact URI is present.
  
  ### Testing
  - Added unit tests `test_prepared_payload_artifacts_override_stale_preparing_state_and_enable_llm` and `test_payload_artifacts_do_not_override_active_capture_state` in `tests/test_check_languages_page.py` to verify prepared payloads promote state to `prepared_for_llm` and that active capture prevents enabling LLM. 
  - Ran the test suite for the modified file and the new tests, and they passed locally (all assertions succeeded).
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c54b08e760832c9c4a9923fc98e3cd)
- Notes: Auto-generated from merged PR metadata.

## PR #174 — 2026-03-26T16:03:56Z

- Title: Merge and dedupe collected_items with baseline precedence; add tests
- PR URL: https://github.com/evinaeva/polyglot-watchdog/pull/174
- Author: evinaeva
- Base branch: main
- Head branch: 5gaxce-codex/implement-deduplication-layer-for-api
- Merge commit: 6535eb4ea86feb380a2568963fc8ca070607ee6c
- Changed files:
  - pipeline/run_phase1.py
  - tests/test_phase1_merge_dedupe.py
  - tests/test_stage_a_read_routes_api.py
- Description:
  ### Motivation
  
  - Prevent duplicate `collected_items` rows when both baseline and recipe captures produce the same `item_id` by making the final artifact flat and deterministic with baseline precedence. 
  
  ### Description
  
  - Add `merge_and_dedupe_items` to combine baseline and recipe item lists, keeping the first-seen baseline row on `item_id` collisions and preserving rows missing `item_id` as passthrough entries.
  - Split collection into `baseline_collected_items` and `recipe_collected_items` during capture and replace the previous single-list sort with `all_collected_items = merge_and_dedupe_items(...)`.
  - Ensure merged output is deterministically sorted by `(item_id, url, state)` and preserve non-dict rows safely by skipping them.
  - Add unit tests in `tests/test_phase1_merge_dedupe.py` and adjust an existing API test assertion in `tests/test_stage_a_read_routes_api.py` to reflect the updated payload shape.
  
  ### Testing
  
  - Added and ran the new unit tests in `tests/test_phase1_merge_dedupe.py`, which validate baseline precedence, inclusion of recipe-only `item_id`s, and preservation of rows missing `item_id`, and they passed.
  - Updated `tests/test_stage_a_read_routes_api.py` and ran the affected API tests which passed with the revised expectations.
  - Ran the test suite with `pytest` for the modified modules and the tests involving these changes completed successfully.
  
  ------
  [Codex Task](https://chatgpt.com/codex/tasks/task_e_69c54d001f54832c868ca82c61154a8d)
- Notes: Auto-generated from merged PR metadata.
