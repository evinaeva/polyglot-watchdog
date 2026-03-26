# Polyglot Watchdog

Polyglot Watchdog is a contract-first operator console and pipeline for localization QA across baseline and target-language web experiences.

This repository is **not** a blank scaffold. It already contains a real artifact model, canonical storage paths, multiple implemented phase runners, and operator-facing UI surfaces backed in part by persisted artifacts.

At the same time, it is **not yet production-ready**. Some operator flows are still incomplete or partially mock-backed, and release-facing documentation must remain aligned with the actual state of the codebase.

This README is the product truth-set entry point for contributors.

For v1.0 scope and release readiness, also read:

- `contract/watchdog_contract_v1.0.md`
- `docs/Interactive Capture Architecture.md`
- `docs/Implementation Playbook.md`
- `docs/PHASE6_TRANSLATION_QA.md`
- `docs/operator-read-routes.md`
- `RELEASE_CRITERIA.md`
- `docs/PRODUCT_TRUTHSET.md`

## Current product status

Current stage: **late prototype / pre-production / operator-console-in-progress**

What is already real in the repository:

- canonical artifact storage paths and JSON artifact writers/readers;
- deterministic pipeline/storage conventions for run-level artifacts;
- implemented phase runners for key contract-aligned flows, including Phase 1, Phase 3, Phase 4, and Phase 6;
- a `/urls` operator surface for managing seed URLs with persisted domain selection and last-used first-run domain memory;
- a `/check-languages` operator surface for running phase-six language checks with a two-step orchestration (payload preparation and LLM review), target-language selection, GitHub Pages project site support, and job orchestration;
- operator-facing issue exploration backed by persisted issue artifacts;
- operator workflow pages are now visibly linked via global navigation;
- Phase 6 image-text review coverage tracking via `coverage_gaps.json` with statuses (`image_text_reviewed`, `image_text_not_reviewed`, `image_text_review_blocked`);
- SVG deterministic text extraction and Google Vision fallback for OCR when OCR.Space is unavailable;
- explicit Phase 6 review mode requirement (`test-heuristic`, `disabled`, `llm`) with fail-fast when missing;
- Tallinn timezone (Europe/Tallinn) display formatting with DST awareness for all timestamps.

What is not yet complete:

- some operator-visible flows are still incomplete or partially mock-backed;
- not all required v1.0 screens are fully release-ready;
- release-facing messaging must stay aligned with actual implementation status.

## v1.0 scope

v1.0 is defined by the contract and implementation docs.

In practical terms, v1.0 means:

- seed URL management through the operator UI;
- deterministic baseline and scripted-state capture planning;
- canonical persisted artifacts for capture outputs;
- annotation/review support for baseline, scripted, and universal items;
- deterministic eligible dataset generation;
- target-language comparison and issue generation through Phase 6.

The following are explicitly **deferred** from blocking v1.0:

- OCR / Phase 4 work;
- crawler improvements beyond the accepted manual seed URL workflow.

## Operator workflow model

The v1.0 operator workflow is **intentionally multi-page by design**.

This means the operator may complete the workflow across multiple dedicated pages or tabs, for example:

- URL management on one page;
- run/capture review on another page;
- annotation/review on another page;
- issue exploration on another page.

This is the **canonical product flow**, not a workaround.

v1.0 does **not** require a single-screen or single-route experience.  
It **does** require that all mandatory steps be available through the official product UI, with:

- clear navigation between the required pages;
- persisted state across steps;
- no dependence on hidden routes;
- no dependence on developer-only actions;
- no required manual intervention outside the product interface.

## What contributors should assume

When changing the product:

- do not describe the repository as entirely mock-backed or claim that no phases are implemented;
- do not describe the product as production-ready unless the release criteria are met;
- do not treat a multi-page operator workflow as a defect by itself;
- treat the contract as normative for artifact semantics and phase boundaries;
- treat `RELEASE_CRITERIA.md` as the release-ready checklist;
- treat `docs/PRODUCT_TRUTHSET.md` as the status and messaging alignment document.

## Canonical messaging rules

Use these statements consistently:

- "Polyglot Watchdog is a contract-first localization QA pipeline and operator console."
- "The repository contains real artifact-backed pipeline components and partial operator UI integration."
- "The project is pre-production and not yet production-ready."
- "The operator workflow is multi-page by design."
- "OCR beyond the current narrow approved image-backed handoff scope is deferred from v1.0."
- "OCR remains non-blocking/additive for v1.0 scope; when OCR handoff exists, Phase 6 may use usable OCR text as canonical comparison text for approved image-backed items and otherwise falls back to normalized DOM text."
- "Manual seed URL workflow is valid for v1.0."
- "Phase 6 uses a two-layer taxonomy: persisted `issue.category` (coarse contract) and evidence-level `review_class` (detailed QA)."
- "Phase 6 compares curated EN reference content against curated target-language content; OCR text is consumed only for approved `<img>` elements, is supporting input overall, and does not introduce new top-level contract categories."
- "Phase 6 review mode is explicit (`test-heuristic`, `disabled`, `llm`); missing mode is a hard error."
- "Image-text review coverage is tracked separately from issues via `coverage_gaps.json` with statuses: `image_text_reviewed`, `image_text_not_reviewed`, `image_text_review_blocked`."

Avoid these outdated statements:

- "No pipeline phases are implemented."
- "The repository is only a UI scaffold."
- "The full operator workflow must exist on a single page to count as integrated."
- "The current product is production-ready."

## Repo areas

- `app/` — operator server and route handlers
- `pipeline/` — phase runners, storage, runtime config, artifact logic
- `web/` — templates and static UI assets
- `tests/` — contract, pipeline, route, and review-related tests
- `contract/` — normative contract documents
- `docs/` — architecture and implementation guidance

## Working agreement for future updates

Any change to public-facing product positioning must keep these in sync:

1. `README.md`
2. About page copy
3. `RELEASE_CRITERIA.md`
4. `docs/PRODUCT_TRUTHSET.md`

If implementation status changes and any of the above are not updated, the documentation is considered out of sync.
