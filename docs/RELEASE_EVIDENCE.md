# RELEASE_EVIDENCE.md

This file packages Stage D release evidence in one place and links it to release-facing readiness decisions.

### 1) /urls persistence evidence

- `/urls` route and related tests
- persisted seed URL storage behavior
- operator-managed URL flow through official UI surfaces

### 2) Reproducible capture flow evidence

- phase1 puller
- storage layer
- rerun paths
- deterministic planning and context reproduction behavior

### 3) Review/annotation persistence evidence

- Review + rerun behavior tests: `tests/test_review_and_rerun.py`
- Phase 3 review linkage checks: `tests/test_phase3_review_integration.py`
- Remaining gate task: confirm that the required visible review/annotation path is represented through official product pages and canonical persistence, without treating the multi-page workflow model itself as a blocker.

### 4) Deterministic eligible dataset generation evidence

- phase 3 linkage and contract-aligned dataset generation tests
- persisted eligible dataset outputs
- universal-sections handling aligned with documented v1.0 behavior

### 5) Issue artifact generation + explorer visibility evidence

- phase 6 code/tests
- issues explorer routes
- issue detail templates
- persisted issue artifacts and drill-down evidence paths

### 6) Documentation synchronization evidence

- `README.md`
- `RELEASE_CRITERIA.md`
- `docs/PRODUCT_TRUTHSET.md`
- `docs/ABOUT_PAGE_COPY.md`
- `docs/RELEASE_READINESS.md`

These documents must describe the same product state:
- pre-production rather than production-ready;
- real artifact-backed implementation rather than all-mock behavior;
- multi-page operator workflow as an acceptable official v1.0 model.

Current audit interpretation:
- release-readiness wording has been updated to the same pre-production framing used elsewhere;
- canonical truth-surface alignment still requires explicit re-audit before Criterion 8 can move to `pass`;
- remaining gate blockers include the still-unknown required criteria (review/annotation canonical visible flow verification, official workflow coherence verification, and final docs-alignment re-audit).

## Stage D conclusion

Current gate state remains **failed** because not all required criteria are verified as `pass`.
Use `pre_production` messaging until every required criterion is explicitly `pass`, including the still-pending workflow verification criteria.
