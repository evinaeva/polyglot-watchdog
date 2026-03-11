# RELEASE_READINESS.md

This file records the current Stage D release-readiness audit for the documented v1.0 scope.

Allowed statuses: `pass`, `fail`, `unknown`.

## Gate decision

- Result: **FAILED**
- Messaging state: **pre_production**
- Why: repository messaging and gate language still need to be updated to reflect that the official operator workflow is multi-page by design; until the criteria and release-facing docs are synchronized, production wording remains blocked.

## Criteria audit table

| # | Criterion | Requirement | Status | Evidence | Notes | Gate impact |
|---|-----------|-------------|--------|----------|-------|-------------|
| 1 | Seed URL management | `/urls` is operator-managed and persisted through canonical storage model | pass | `tests/test_seed_urls.py`; `tests/test_stage_c_operator_workflow.py`; `app/seed_urls.py` | blocker if not met | blocks production wording if fail/unknown |
| 2 | Deterministic capture planning | Baseline/scripted jobs and explicit contexts are reproducible; exact-context rerun path exists | pass | `tests/test_phase1_planning_input.py`; `tests/test_phase1_recipe_execution.py`; `tests/test_review_and_rerun.py` | blocker if not met | blocks production wording if fail/unknown |
| 3 | Canonical capture artifacts | Runs persist full/page/element artifacts with canonical structure and naming | pass | `tests/test_contract_pipeline.py`; `tests/test_interactive_capture_acceptance.py`; `pipeline/storage.py` | blocker if not met | blocks production wording if fail/unknown |
| 4 | Review and annotation flow | Decisions/annotations persist through canonical flow; no mock fallback for required flow | unknown | `tests/test_review_and_rerun.py`; `tests/test_phase3_review_integration.py`; verify current visible review surfaces against canonical persisted flow | blocker until explicitly re-verified | production wording remains blocked until verified |
| 5 | Eligible dataset generation | Phase 3 deterministically writes `eligible_dataset.json` with documented universal-sections behavior | pass | `tests/test_stage_b_phase3_linkage.py`; `tests/test_contract_pipeline.py` | blocker if not met | blocks production wording if fail/unknown |
| 6 | Target-language comparison and issue generation | Phase 6 persists issues and explorer reads them; evidence drill-down exists | pass | `tests/test_phase6_schema_compliance.py`; `tests/test_issues_explorer_api.py`; `web/templates/issues/detail.html` | blocker if not met | blocks production wording if fail/unknown |
| 7 | Official operator workflow coherence | Operator can complete core documented v1.0 workflow across official UI pages/tabs without hidden/manual developer-only paths | unknown | `docs/LOCAL_DEMO_RUNBOOK.md`; `tests/test_stage_c_operator_workflow.py`; release-facing docs must be synchronized to the multi-page workflow model | blocker until explicitly re-verified | production wording remains blocked until verified |
| 8 | Documentation alignment | README/About/truth-set docs aligned to implementation state | unknown | compare README, About, truth-set, criteria, and readiness docs after messaging changes | blocker until re-audited after synchronization | production wording remains blocked until verified |

## Blocking conditions that currently prevent gate pass

- Criterion 4: review/annotation persistence may already be partially implemented, but release audit wording must verify the visible canonical flow directly rather than infer failure from older documentation language.
- Criterion 7: the operator workflow must be evaluated as an official multi-page flow; release docs and criteria must be synchronized before a pass/fail conclusion is finalized.
- Criterion 8: release-facing documentation must be re-audited after synchronization so that no old single-flow assumptions remain.