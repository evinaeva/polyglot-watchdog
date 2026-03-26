# PRODUCT_TRUTHSET.md

## Purpose

This document keeps product messaging synchronized across repository docs and operator-facing copy.

It answers three questions:

1. What is the product?
2. What is its current stage?
3. What is in scope for v1.0?

## Canonical product description

Polyglot Watchdog is a **contract-first localization QA pipeline and operator console**.

It combines:

- canonical persisted artifacts for capture and comparison;
- deterministic phase-oriented processing;
- operator-facing flows for URL management, review, annotation, and issue exploration.

## Current stage

The canonical current-stage description is:

**late prototype / pre-production / operator-console-in-progress**

This means:

- the codebase contains real pipeline and artifact-backed implementation;
- some operator surfaces are already backed by persisted data;
- some operator-facing flows are still being hardened for pre-production;
- the product is not yet production-ready.

It does **not** mean that the product must expose a single-page workflow to be considered coherent.

## Operator workflow model

The canonical v1.0 operator workflow is **multi-surface / multi-step (multi-page / multi-tab) by design**.

This means:

- URL management may live on one page;
- capture/run/context review may live on another page;
- annotation/review may live on another page;
- issue exploration may live on another page.

This is an **official product workflow**, not a workaround and not a developer-only path.

A multi-page workflow is acceptable for v1.0 as long as:

- the required steps are available through official UI surfaces;
- navigation between those surfaces is clear;
- state is persisted across the workflow;
- the operator does not need hidden routes or manual actions outside the product interface.

The product should therefore be evaluated on **workflow completeness across official pages**, not on whether all steps are collapsed into a single screen.

## What is already true

The following statements are allowed and should be treated as true:

- the repository contains real pipeline/storage implementation;
- the repository is not just a UI mock scaffold;
- some operator routes are backed by persisted artifacts;
- the operator workflow is intentionally distributed across multiple pages/tabs;
- the product includes a new `/check-languages` page for running phase-six language checks comparing a target run against an English reference, with a two-step orchestration (payload preparation and LLM review), support for GitHub Pages project language paths and site-family run discovery, and stable JSON hashing with source hash checks to detect stale prepared payloads;
- the `/urls` page now uses persisted domains and remembers the last-used first-run domain across reloads;
- phase-six runtime mode selection is explicit (`test-heuristic`, `disabled`, `llm`) and missing mode is a hard error;
- image-backed review coverage is tracked separately from issues via `coverage_gaps.json` statuses (`image_text_reviewed`, `image_text_not_reviewed`, `image_text_review_blocked`);
- SVG deterministic text extraction and Google Vision fallback are available for OCR when OCR.Space is unavailable;
- timestamps are displayed in Europe/Tallinn timezone with DST awareness;
- the product is not yet production-ready.

## What is no longer allowed

The following statements are considered outdated and should not be reintroduced:

- “No meaningful pipeline implementation exists.”
- “All data returned by the API is mock/static.”
- “This repo is only a front-end scaffold.”
- “A multi-page operator workflow is automatically evidence of broken integration.”
- “The product is production-ready.”

## v1.0 source-of-truth scope

For messaging and planning, v1.0 includes:

- seed URL management;
- deterministic baseline/scripted capture;
- persisted artifacts for capture output;
- review and annotation support;
- eligible dataset generation;
- target-language issue generation and exploration;
- interactive check-languages page for running phase-six language checks with target-language selection and job orchestration.

Deferred and still acceptable for v1.0:

- OCR / Phase 4 work;
- crawler improvements beyond manual seed URL workflow;
- keeping the operator workflow distributed across multiple pages/tabs instead of consolidating it into one screen.

## Stage D gate state

Current release-gate state is **pre_production**.

- Deterministic rule: `GATE_PASSED = all(required_v1_0_criteria == pass)`
- Current result: gate failed if required blockers remain
- Audit source: `docs/RELEASE_READINESS.md`
- Evidence package: `docs/RELEASE_EVIDENCE.md`

Because the gate is failed, this repository must not use production-ready wording.

## Precedence order

If documents conflict, the intended precedence is:

1. `contract/watchdog_contract_v1.0.md`
2. architecture / implementation docs in `docs/`
3. `RELEASE_CRITERIA.md`
4. `README.md`
5. About page copy

The lower-priority document must be updated to match the higher-priority one.

## Update rules

Whenever implementation status changes, update all of the following together:

- `README.md`
- About page text
- `RELEASE_CRITERIA.md`
- this file

## Maintainer note

This file exists because implementation status and public-facing messaging drifted.

Future edits should preserve a single coherent story:

- real backend/artifact implementation exists;
- the operator workflow may be intentionally split across multiple pages/tabs;
- that multi-page structure is acceptable when it is the official product flow;
- production-ready claims remain blocked until release criteria are met.
