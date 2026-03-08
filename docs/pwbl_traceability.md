# PW-BL Traceability Matrix

This document maps PW-BL remediation tasks to concrete implementation evidence in the repository.

| Task | Status | Primary files/modules | Primary tests | Notes / follow-up |
|---|---|---|---|---|
| PW-BL-001 | IMPLEMENTED | `pipeline/run_phase0.py`, `pipeline/run_phase1.py`, `pipeline/run_phase2.py`, `pipeline/run_phase3.py`, `pipeline/run_phase6.py` | `tests/test_contract_pipeline.py` | Canonical phase entrypoints are the supported execution path. |
| PW-BL-002 | IMPLEMENTED | `pipeline/run_phase1.py`, `app/seed_urls.py` | `tests/test_phase1_planning_input.py`, `tests/test_seed_urls.py` | `seed_urls` is required; legacy fallback paths removed. |
| PW-BL-003 | IMPLEMENTED | `pipeline/interactive_capture.py` | `tests/test_interactive_capture_acceptance.py` | Deterministic planner expansion and ordering preserved. |
| PW-BL-004A | IMPLEMENTED | `pipeline/interactive_capture.py`, `pipeline/runtime_config.py` | `tests/test_interactive_capture_acceptance.py`, `tests/test_runtime_config.py` | Contract identity and state validation enforced. |
| PW-BL-004 | IMPLEMENTED | `pipeline/run_phase1.py`, `pipeline/phase1_puller.py`, `app/recipes.py` | `tests/test_phase1_recipe_execution.py`, `tests/test_interactive_capture_acceptance.py` | Scripted states now require recipe-step execution before capture. |
| PW-BL-005 | IMPLEMENTED | `pipeline/phase1_puller.py`, `pipeline/interactive_capture.py` | `tests/test_interactive_capture_acceptance.py` | One screenshot per capture context maintained. |
| PW-BL-007 | IMPLEMENTED | `app/skeleton_server.py`, `pipeline/run_phase3.py`, `pipeline/run_phase6.py` | `tests/test_phase3_review_integration.py`, `tests/test_phase6_schema_compliance.py` | Review status is persisted and consumed downstream. |
| PW-BL-006 | IMPLEMENTED | `pipeline/interactive_capture.py`, `pipeline/phase1_puller.py` | `tests/test_interactive_capture_acceptance.py`, `tests/test_contract_pipeline.py` | `item_id` contract formula unchanged. |
| PW-BL-010 | IMPLEMENTED | `pipeline/run_phase1.py`, `pipeline/interactive_capture.py` | `tests/test_interactive_capture_acceptance.py` | Universal sections remain EN baseline only. |
| PW-BL-011 | IMPLEMENTED | `pipeline/interactive_capture.py`, `app/skeleton_server.py`, `pipeline/run_phase1.py` | `tests/test_interactive_capture_acceptance.py`, `tests/test_review_and_rerun.py` | Contract identity vs storage/rerun identity remains separated. |
| PW-BL-013 | IMPLEMENTED | `pipeline/run_phase6.py` | `tests/test_phase6_schema_compliance.py` | Phase 6 remains schema-valid and now includes overlay-blocked propagation. |
| PW-BL-017 | IMPLEMENTED | `pipeline/run_phase1.py`, `app/seed_urls.py` | `tests/test_phase1_planning_input.py`, `tests/test_seed_urls.py` | Migration-era compatibility branches removed from active path. |

## Deferred or not evidenced in this pass

Tasks not listed above were not part of this final convergence pass and should be audited against backlog acceptance criteria separately.
