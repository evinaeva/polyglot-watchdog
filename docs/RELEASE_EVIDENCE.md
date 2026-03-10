# RELEASE_EVIDENCE.md

## Purpose

This file packages Stage D release evidence in one place and links it to release criteria and messaging state.

- Gate authority: `RELEASE_CRITERIA.md`
- Gate decision artifact: `docs/RELEASE_READINESS.md`
- Messaging model: `docs/MESSAGING_STATE.md`

## Evidence index by required capability

### 1) /urls persistence evidence

- API + behavior coverage: `tests/test_seed_urls.py`
- Workflow coverage including operator flow references: `tests/test_stage_c_operator_workflow.py`
- Persistence implementation path: `app/seed_urls.py`

### 2) Reproducible capture flow evidence

- Deterministic planning checks: `tests/test_phase1_planning_input.py`
- Execution path checks: `tests/test_phase1_recipe_execution.py`
- Interactive capture support path: `tests/test_interactive_capture_acceptance.py`

### 3) Review/annotation persistence evidence

- Review + rerun behavior tests: `tests/test_review_and_rerun.py`
- Phase 3 review linkage checks: `tests/test_phase3_review_integration.py`
- Current gap for gate: visible required operator flow is still documented as incomplete (see criteria 4/7 in `docs/RELEASE_READINESS.md`).

### 4) Deterministic eligible dataset generation evidence

- Phase 3 linkage checks: `tests/test_stage_b_phase3_linkage.py`
- Contract/pipeline compatibility checks: `tests/test_contract_pipeline.py`

### 5) Issue artifact generation + explorer visibility evidence

- Phase 6 artifact/schema checks: `tests/test_phase6_schema_compliance.py`
- Explorer API checks: `tests/test_issues_explorer_api.py`
- Explorer drill-down template path: `web/templates/issues/detail.html`

### 6) Documentation synchronization evidence

- Truth surfaces synchronized to `pre_production` state:
  - `README.md`
  - `docs/ABOUT_PAGE_COPY.md`
  - `RELEASE_CRITERIA.md`
  - `docs/PRODUCT_TRUTHSET.md`
- Drift prevention checks: `tests/test_docs_alignment.py`

## Stage D conclusion

Current gate state is **failed**; production wording is therefore disallowed.

Use `pre_production` messaging until criteria 4 and 7 are no longer blockers and all required criteria are `pass`.
