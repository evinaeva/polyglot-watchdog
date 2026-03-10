# RELEASE_CRITERIA.md

## Purpose

This document defines what counts as **v1.0-ready** for Polyglot Watchdog and what must be true before the project may be described as production-ready in repository or operator-facing documentation.

The contract is normative for artifact semantics and phase boundaries. This file translates that into a release checklist.

## Product stage language

Until all required criteria below are satisfied, the project must be described as:

**late prototype / pre-production / operator-console-in-progress**

It must **not** be described as production-ready.

## v1.0 required scope

A v1.0-ready release must provide all of the following:

### 1. Seed URL management
- Seed URLs can be managed through the operator UI.
- Seed URL persistence is real, not mock-backed.
- URL configuration remains compatible with the pipeline's canonical storage model.

### 2. Deterministic capture planning
- Baseline and scripted-state capture jobs are derived deterministically from the configured inputs.
- Capture contexts are explicit and reproducible.
- Exact-context rerun is supported by the implementation path.

### 3. Canonical capture artifacts
- Capture runs persist canonical artifacts through the existing storage layer.
- Full-page screenshots, page-level artifacts, and element-level artifacts are written in the expected canonical structure.
- Artifact naming and serialization stay compatible with the contract and storage layer.

### 4. Review and annotation flow
- Review decisions are persisted through the canonical application flow.
- Annotation / pulling decisions are backed by real artifact data.
- Missing or not-ready states are represented explicitly rather than by mock fallbacks.

### 5. Eligible dataset generation
- Phase 3 produces deterministic `eligible_dataset.json` outputs from the expected inputs.
- Universal sections handling remains compatible with documented v1.0 behavior.

### 6. Target-language comparison and issue generation
- Phase 6 consumes canonical artifacts and produces persisted issues.
- The issues explorer reads real issue artifacts.
- Drill-down to the related capture evidence is available at the operator level.

### 7. Visible operator workflow coherence
- Core operator pages required for the v1.0 flow are not mock-backed.
- The operator can move through the intended workflow without using hidden developer-only paths.

### 8. Documentation alignment
- README, About text, and truth-set docs do not contradict the actual implementation state.
- Deferred scope is explicitly called out as deferred, not forgotten.

## Deferred scope that does NOT block v1.0

The following items may remain unfinished without blocking a v1.0 release:

- OCR / Phase 4 work
- crawler improvements beyond the accepted manual seed URL workflow
- additional operator UX polish beyond the core v1.0 flow
- optional dedicated screens for backend internals that are not required for the operator workflow

## Release blockers

The product must not be declared production-ready if any of the following are true:

- README still claims that all phases are unimplemented or all API data is mock/static;
- a core operator route required for v1.0 remains mock-backed;
- review, rerun, or annotation decisions are disconnected from canonical artifact flows;
- issues explorer is not backed by persisted Phase 6 artifacts;
- release-facing docs disagree about whether the product is real vs mock-backed;
- the visible workflow depends on hidden/manual developer steps not acknowledged in docs.

## Required release evidence

Before calling the project production-ready, maintainers should be able to point to:

- a functioning `/urls` flow backed by real persistence;
- a reproducible capture flow;
- real review/annotation storage behavior;
- deterministic eligible dataset generation;
- real issue artifact generation and explorer visibility;
- synchronized README/About/truth-set docs.

## Required wording once criteria are met

Once all required criteria are satisfied, maintainers may describe the project as:

- “production-ready for the documented v1.0 scope”
- “contract-aligned for the documented v1.0 flow”

Until then, use only the current pre-production stage language.
