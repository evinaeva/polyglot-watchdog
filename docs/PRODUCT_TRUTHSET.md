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
- the full visible product workflow is not yet fully integrated and release-ready.

## What is already true

The following statements are allowed and should be treated as true:

- the repository contains real pipeline/storage implementation;
- the repository is not just a UI mock scaffold;
- some operator routes are backed by persisted artifacts;
- the product is not yet production-ready.

## What is no longer allowed

The following statements are considered outdated and should not be reintroduced:

- “No pipeline phases are implemented.”
- “All data returned by the API is mock/static.”
- “This repo is only a front-end scaffold.”
- “The product is production-ready.”

## v1.0 source-of-truth scope

For messaging and planning, v1.0 includes:

- seed URL management;
- deterministic baseline/scripted capture;
- persisted artifacts for capture output;
- review and annotation support;
- eligible dataset generation;
- target-language issue generation and exploration.

Deferred and still acceptable for v1.0:

- OCR / Phase 4 work;
- crawler improvements beyond manual seed URL flow.

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

This file exists because implementation status and public-facing messaging drifted. Future edits should preserve a single coherent story:

- real backend/artifact implementation exists;
- visible workflow integration is still incomplete;
- production-ready claims are blocked until release criteria are met.
