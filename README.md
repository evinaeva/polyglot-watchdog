# Polyglot Watchdog

Polyglot Watchdog is a contract-first localization QA pipeline and operator console.

This repository already contains real pipeline and storage code. It is not a blank scaffold and not a UI-only mock project.

Current stage: late prototype / pre-production / operator-console-in-progress.

The project is not yet production-ready.

## What exists today

The repository already includes:

- canonical artifact storage paths and artifact readers/writers
- deterministic run-level artifact handling
- implemented phase runners for Phase 1, Phase 3, Phase 4, and Phase 6
- a `/urls` operator page for seed URL management
- persisted domain selection and last-used first-run domain memory on `/urls`
- a `/check-languages` operator page for Phase 6 language checks
- two-step Phase 6 orchestration: payload preparation, then LLM review
- target-language selection and job orchestration
- support for GitHub Pages project site paths in language checks
- persisted issue artifacts and operator-facing issue exploration
- visible navigation between operator workflow pages
- image-text review coverage tracking through `coverage_gaps.json`
- explicit Phase 6 review mode: `test-heuristic`, `disabled`, or `llm`
- fail-fast behavior when review mode is missing
- Europe/Tallinn timestamp display with DST awareness

## What is not complete

Some operator-facing flows are still being hardened.

Not all v1.0 screens are fully release-ready.

Because of that, the repository must not be described as production-ready.

## v1.0 scope

For v1.0, the required product scope is:

- seed URL management through the operator UI
- deterministic baseline and scripted capture planning
- canonical persisted capture artifacts
- review and annotation support
- deterministic eligible dataset generation
- target-language comparison and issue generation through Phase 6
- issue exploration backed by persisted artifacts

## What does not block v1.0

The following may remain incomplete without blocking v1.0:

- OCR and Phase 4 hardening work
- crawler improvements beyond the accepted manual seed URL workflow
- additional UI polish outside the core operator workflow
- keeping the workflow split across multiple pages instead of one screen

## Operator workflow model

The v1.0 workflow is multi-page by design.

It does not need to live on a single route or screen.

A valid operator flow may span separate pages for:

- URL management
- capture or run review
- annotation or review work
- issue exploration

This is an official product workflow, not a workaround.

For v1.0, the important requirement is that the operator can complete the workflow through official UI pages with clear navigation and persisted state.

The workflow must not depend on hidden routes, developer-only actions, or manual steps outside the product interface.

## Contributor guidance

When updating product docs or UI copy, keep these points true:

- the repository contains real artifact-backed pipeline components
- the project is pre-production
- the workflow may be intentionally split across multiple pages
- manual seed URL workflow is valid for v1.0
- production-ready wording is not allowed until release criteria are met

Do not reintroduce outdated claims such as:

- no phases are implemented
- the repository is only a UI scaffold
- a multi-page workflow means the product is not integrated
- the project is already production-ready

## Phase 6 notes

Phase 6 uses persisted issue artifacts.

Phase 6 review mode is explicit and required.

Image-text review coverage is tracked separately from issues in `coverage_gaps.json`.

OCR remains additive and non-blocking for v1.0. Approved image-backed OCR handoff may be used where available, but OCR does not expand the top-level contract scope for v1.0.

## Important files

Read these files when working on product status or release messaging:

- `contract/watchdog_contract_v1.0.md`
- `docs/Interactive Capture Architecture.md`
- `docs/Implementation Playbook.md`
- `docs/PHASE6_TRANSLATION_QA.md`
- `docs/operator-read-routes.md`
- `RELEASE_CRITERIA.md`
- `docs/PRODUCT_TRUTHSET.md`

## Main repo areas

- `app/` operator server and route handlers
- `pipeline/` phase runners, storage, runtime config, artifact logic
- `web/` templates and static UI assets
- `tests/` contract, pipeline, route, and review-related tests
- `contract/` normative contract documents
- `docs/` architecture and implementation guidance

## Documentation sync rule

If product status or release messaging changes, update these together:

- `README.md`
- `RELEASE_CRITERIA.md`
- `docs/PRODUCT_TRUTHSET.md`

If these documents disagree, the documentation is out of sync.
