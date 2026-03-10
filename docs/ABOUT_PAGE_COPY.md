# ABOUT_PAGE_COPY.md

Use the following as the replacement or source text for the `/about` page.

---

## About Polyglot Watchdog

Polyglot Watchdog is a contract-first localization QA pipeline and operator console for comparing baseline and target-language web experiences.

The project already includes real persisted artifacts and multiple implemented pipeline flows. It is not just a UI mock or static prototype. At the same time, it is still **pre-production**: some operator surfaces are already artifact-backed, while parts of the visible workflow are still being aligned with the full documented v1.0 flow.

### What the product already does

Polyglot Watchdog already includes:

- canonical artifact storage for run outputs;
- deterministic pipeline-oriented processing for key documented phases;
- operator-facing URL management;
- persisted issue exploration backed by Phase 6 artifacts.

### What is still in progress

The full visible operator workflow is still being finished. Some routes or interactions remain incomplete or mock-backed in the current UI, and some backend details are not yet surfaced through dedicated operator screens.

### What v1.0 means here

For the documented v1.0 scope, the goal is:

- manage seed URLs through the operator UI;
- run deterministic baseline and scripted capture;
- review and annotate canonical artifacts;
- build an eligible dataset;
- compare target-language outputs and generate issues.

### Deferred scope

The following are intentionally not required to declare the documented v1.0 scope complete:

- OCR / Phase 4 work
- crawler improvements beyond the accepted manual seed URL workflow

### Current stage

Current stage: **late prototype / pre-production / operator-console-in-progress**

The product should not yet be described as production-ready until the visible operator workflow and repository documentation are fully aligned with the release criteria.

### Stage D release-gate outcome

Release gate decision: **pre_production** (failed gate).

Production-ready wording is currently disallowed because required release criteria still contain blockers in the Stage D audit (`docs/RELEASE_READINESS.md`).

What remains:

- complete required criterion 4 (review/annotation flow coherence in visible required workflow);
- complete required criterion 7 (visible operator workflow coherence);
- keep About/README/criteria/truth-set wording synchronized.

---
