# ABOUT_PAGE_COPY.md

Use the following as the replacement or source text for the `/about` page.

## About Polyglot Watchdog

Polyglot Watchdog is a contract-first localization QA pipeline and operator console for comparing baseline and target-language web experiences.

The project already includes real persisted artifacts and multiple implemented pipeline flows. It is not just a UI mock or static prototype. At the same time, it is still **pre-production**: some operator surfaces are already artifact-backed, while release readiness remains gated by documented criteria and documentation alignment.

### What the product already does

Polyglot Watchdog already includes:

- canonical artifact storage and JSON-backed run outputs;
- deterministic capture and comparison-oriented pipeline behavior;
- multiple implemented phase-aligned flows;
- operator-facing URL management;
- persisted issue exploration backed by Phase 6 artifacts.

### How the operator workflow works

The operator workflow is intentionally distributed across multiple dedicated pages/tabs.

For example, an operator may:
- add and manage URLs on one page;
- review runs, contexts, or pulls on other pages;
- perform review/annotation on another page;
- inspect issues and related evidence on another page.

This multi-page structure is the canonical product flow for v1.0, not a workaround.

### What v1.0 means here

For the documented v1.0 scope, the required product flow includes:

- operator-managed seed URLs;
- deterministic capture planning and persisted capture artifacts;
- review / annotation support through canonical data flows;
- deterministic eligible dataset generation;
- target-language issue generation and issue exploration.

The following are intentionally not required to declare the documented v1.0 scope complete:

- OCR / Phase 4 work;
- manual seed URL workflow;
- UX polish beyond the core documented operator workflow.

### Current stage

Current stage: **late prototype / pre-production / operator-console-in-progress**

The product should not yet be described as production-ready until all required release criteria are met and repository documentation is fully aligned with those criteria.

### Stage D release-gate outcome

Release gate decision: **pre_production**

What remains:
- keep criterion 4 focused on real persisted review/annotation behavior through the canonical flow;
- define criterion 7 in terms of a coherent official multi-page workflow rather than a single-screen expectation;
- keep About/README/criteria/truth-set wording synchronized.