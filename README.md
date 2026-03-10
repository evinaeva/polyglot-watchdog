# Polyglot Watchdog

Polyglot Watchdog is a contract-first operator console and pipeline for localization QA across baseline and target-language web experiences.

This repository is **not** a blank scaffold. It already contains a real artifact model, canonical storage paths, multiple implemented phase runners, and an operator UI that is partially backed by persisted artifacts. At the same time, it is **not yet production-ready**: some visible operator screens are still mock-backed or incomplete, and the documentation has drifted from the actual state of the codebase.

This README is the product truth-set entry point for contributors. For v1.0 scope and release readiness, also read:

- `contract/watchdog_contract_v1.0.md`
- `docs/Interactive Capture Architecture.md`
- `docs/Implementation Playbook.md`
- `docs/operator-read-routes.md`
- `RELEASE_CRITERIA.md`
- `docs/PRODUCT_TRUTHSET.md`

## Current product status

Current stage: **late prototype / pre-production / operator-console-in-progress**

What is already real in the repository:

- canonical artifact storage paths and JSON artifact writers/readers;
- deterministic pipeline/storage conventions for run-level artifacts;
- implemented phase runners for key contract-aligned flows, including Phase 1, Phase 3, and Phase 6;
- a `/urls` operator surface for managing seed URLs;
- an issues explorer surface backed by persisted issue artifacts.

What is not yet complete:

- the full visible operator workflow is not fully integrated end-to-end;
- some UI routes still rely on mock-backed or incomplete flows;
- README, About text, and implementation status previously drifted and must stay aligned going forward.

## v1.0 scope

v1.0 is defined by the contract and implementation docs. In practical terms, v1.0 means:

- seed URL management through the operator UI;
- deterministic baseline and scripted-state capture planning;
- canonical persisted artifacts for capture outputs;
- annotation/review support for baseline, scripted, and universal items;
- deterministic eligible dataset generation;
- target-language comparison and issue generation through Phase 6.

The following are explicitly **deferred** from blocking v1.0:

- OCR / Phase 4 work;
- crawler improvements beyond the accepted manual seed URL workflow.

## What contributors should assume

When changing the product:

- do not describe the repository as “all mock” or “no phases implemented”;
- do not describe the product as production-ready unless the release criteria are met;
- treat the contract as normative for artifact semantics and phase boundaries;
- treat `RELEASE_CRITERIA.md` as the release-ready checklist;
- treat `docs/PRODUCT_TRUTHSET.md` as the status and messaging alignment document.

## Canonical messaging rules

Use these statements consistently:

- “Polyglot Watchdog is a contract-first localization QA pipeline and operator console.”
- “The repository contains real artifact-backed pipeline components and partial operator UI integration.”
- “The project is pre-production and not yet production-ready.”
- “OCR is deferred from v1.0.”
- “Manual seed URL workflow is valid for v1.0.”

Avoid these outdated statements:

- “No pipeline phases are implemented.”
- “All API responses are mock/static.”
- “The repository is only a UI scaffold.”
- “The current product is production-ready.”

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
