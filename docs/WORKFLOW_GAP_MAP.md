# Workflow Gap Map (Workstream A)

| Workflow Step | UI Route | API | Backend Handler | Real/Mock | Reads | Writes | Next Step | Gap/Blocker |
|---|---|---|---|---|---|---|---|---|
| Workflow entry + run scoping | `/workflow` | `GET /api/workflow/status`, `GET /api/domains`, `GET /api/capture/runs` | `SkeletonHandler.do_GET`, `_workflow_status_payload` | real & complete | `seed_urls.json`, run/job artifacts | none | Start capture | **Closed:** previously missing UI-first orchestration hub |
| Manage seed URLs | `/urls` | `GET/POST /api/seed-urls*` | `SkeletonHandler.do_GET/do_POST` | real & complete | `seed_urls.json` | `seed_urls.json` | Start capture | closed |
| Start run / capture | `/workflow` | `POST /api/workflow/start-capture` | `SkeletonHandler.do_POST`, `_run_phase1_async` | real & complete | seed URLs + runtime config | phase1 artifacts + run job records | Observe run | **Closed:** UI action now available |
| Observe run progress/completion | `/workflow` | `GET /api/workflow/status`, `GET /api/job` | `SkeletonHandler.do_GET` | real & complete | `capture_runs.json`, artifacts | none | Review | **Closed:** visible state rendering + refresh loop |
| Inspect capture outputs + review decisions | `/contexts` | `GET /api/capture/contexts`, `POST /api/capture/reviews` | `SkeletonHandler.do_GET/do_POST`, `_persist_capture_review` | real & complete | `page_screenshots.json`, review records | review status records | Annotation/rules | **Closed:** review save actions now visible in UI |
| Annotation/template-rule decisions | `/pulls` | `GET /api/pulls`, `POST /api/rules` | `SkeletonHandler.do_GET/do_POST`, `_upsert_phase2_decision` | real & complete | `collected_items.json`, `template_rules.json` | `template_rules.json` | Generate eligible dataset | **Closed:** decision save actions now visible in UI |
| Generate eligible dataset | `/workflow` | `POST /api/workflow/generate-eligible-dataset` | `_run_phase3_async` | real & complete | collected/review/rules artifacts | `eligible_dataset.json` | Generate issues | closed |
| Generate issues/comparison | `/workflow` | `POST /api/workflow/generate-issues` | `_run_phase6_async` | real & complete | `eligible_dataset.json`, capture artifacts | `issues.json` | Explore issues | closed |
| Explore issues | `/` | `GET /api/issues` | `SkeletonHandler.do_GET` | real & complete | `issues.json` | none | Issue detail | closed |
| Issue → evidence drilldown | `/issues/detail` | `GET /api/issues/detail` | `SkeletonHandler.do_GET` | real & complete | `issues.json`, optional capture artifacts | none | Continue review/annotation | closed |

## Summary

Closed blocking gaps:
- Added UI-first workflow hub with visible operator actions (no curl needed for required steps).
- Added run-scoped links from hub to contexts/pulls/issues/detail.
- Added visible review + annotation persistence actions on required pages.
- Updated workflow status contract to expose standardized state values used by UI rendering.
- Acceptance now enforces truthful failure when capture runner prerequisites are unavailable and blocks downstream workflow progression.


## Current blocker note

- If capture runner prerequisites (Playwright browser runtime) are unavailable, workflow must surface **failed** capture state and must not generate synthetic artifacts. In this state Workstream A remains blocked for true clean-env full happy-path completion until runner prerequisites are satisfied.
