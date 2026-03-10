# RELEASE_READINESS.md

## Stage D release-readiness audit

This audit is the Stage D single-source release decision artifact.

Authority: `RELEASE_CRITERIA.md`.

Decision rule:

`GATE_PASSED = all(required_v1_0_criteria_status == pass)`

Allowed statuses: `pass`, `fail`, `unknown`.

## Gate decision

- Result: **FAILED**
- Messaging state: **pre_production**
- Why: required criteria 4 and 7 are `fail`, so production wording is blocked.

## Criteria audit table

| # | Criterion (from RELEASE_CRITERIA.md) | Required state for pass | Current status | Evidence pointers | Release impact | Messaging impact |
|---|---|---|---|---|---|---|
| 1 | Seed URL management | `/urls` is operator-managed and persisted through canonical storage model | pass | `tests/test_seed_urls.py`; `tests/test_stage_c_operator_workflow.py`; `app/seed_urls.py` | blocker if not met | blocks production wording if fail/unknown |
| 2 | Deterministic capture planning | Baseline/scripted jobs and explicit contexts are reproducible; exact-context rerun path exists | pass | `tests/test_phase1_planning_input.py`; `tests/test_phase1_recipe_execution.py`; `tests/test_review_and_rerun.py` | blocker if not met | blocks production wording if fail/unknown |
| 3 | Canonical capture artifacts | Runs persist full/page/element artifacts with canonical structure and naming | pass | `tests/test_contract_pipeline.py`; `tests/test_interactive_capture_acceptance.py`; `pipeline/storage.py` | blocker if not met | blocks production wording if fail/unknown |
| 4 | Review and annotation flow | Decisions/annotations persist through canonical flow; no mock fallback for required flow | **fail** | Current product messaging still states visible workflow pieces remain incomplete/mock-backed in required flow surfaces (`README.md`, `docs/PRODUCT_TRUTHSET.md`) | **active blocker** | **production wording forbidden** |
| 5 | Eligible dataset generation | Phase 3 deterministically writes `eligible_dataset.json` with documented universal-section behavior | pass | `tests/test_stage_b_phase3_linkage.py`; `tests/test_phase3_review_integration.py` | blocker if not met | blocks production wording if fail/unknown |
| 6 | Target-language comparison and issue generation | Phase 6 persists issues, explorer reads persisted artifacts, drill-down is available | pass | `tests/test_phase6_schema_compliance.py`; `tests/test_issues_explorer_api.py`; `web/templates/issues/detail.html` | blocker if not met | blocks production wording if fail/unknown |
| 7 | Visible operator workflow coherence | Operator can complete core visible v1.0 workflow without hidden/manual developer-only paths | **fail** | Public docs still acknowledge incomplete visible workflow integration for v1.0 (`README.md`, `docs/ABOUT_PAGE_COPY.md`, `docs/PRODUCT_TRUTHSET.md`) | **active blocker** | **production wording forbidden** |
| 8 | Documentation alignment | README/About/criteria/truth-set are synchronized and explicit about deferred scope | pass | `tests/test_docs_alignment.py`; `docs/MESSAGING_STATE.md` | blocker if not met | blocks production wording if fail/unknown |

## Blockers that keep gate failed

- Criterion 4: Review and annotation flow is not yet represented as fully complete in the visible required operator flow.
- Criterion 7: Visible end-to-end operator workflow is still explicitly described as incomplete.

## Deferred scope (non-blocking)

Deferred and non-blocking for v1.0 messaging:

- OCR / Phase 4
- crawler improvements beyond manual seed URLs
- extra UX polish beyond core v1.0 flow
