# About Polyglot Watchdog

## Overview

Polyglot Watchdog is a pipeline and operator interface for building an English reference dataset and detecting localization issues across languages.

The system captures pages from an English source site, captures corresponding pages in target languages, and compares structured page elements to identify potential translation or localization problems.

It combines automated page capture, structured extraction, operator review and annotation, deterministic pairing, and issue generation.

The interface in this repository is best understood as an operator and development console for parts of that pipeline.

## The problem it addresses

Localization QA is hard to automate because pages contain dynamic content, layout differences, repeated template regions, and elements that should not always be compared.

Polyglot Watchdog addresses this by:

1. Capturing pages under explicit runtime contexts.
2. Extracting elements with stable identifiers.
3. Allowing operators to annotate what should be ignored, masked, or always kept.
4. Building a filtered English reference dataset.
5. Comparing target-language captures against that dataset.

<div class="doc-note"><strong>Note on current UI:</strong> The backend generates structured issue artifacts (for example <code>issues.json</code>), while some UI surfaces remain operator-console-in-progress and are still being hardened.</div>

## System pipeline

### Phase 0 — URL discovery

Discovers URLs for a domain and builds inventory artifacts used by later capture phases.

### Phase 1 — Page capture

Captures each page context and records structured data such as screenshots, metadata, and extracted elements (text, images, buttons, inputs). English runs also write universal sections.

### Phase 2 — Element annotation

Stores operator decisions that influence dataset construction:

- `IGNORE_ENTIRE_ELEMENT`
- `MASK_VARIABLE`
- `ALWAYS_COLLECT`

### Phase 3 — English reference dataset

Builds the eligible English dataset from captured items, review status, and rules. Contexts blocked during review are excluded.

### Phase 6 — Localization comparison

Compares target-language captures to the English reference dataset and writes issue records with contextual evidence (IDs, bounding boxes, screenshots).

<div class="doc-note"><strong>Accuracy note:</strong> Pairing and issue generation are implemented, but exact issue detection criteria are broader than what this UI currently visualizes directly.</div>

## Capture context

A capture context describes runtime conditions for capture. It includes URL, viewport type, state, and optional user tier (with language in runtime config).

Language is intentionally excluded from capture-context identity.

## Deterministic identity and pairing

### Page identity

Derived from URL, viewport type, state, and user tier.

### Element identity

Derived from domain, URL, CSS selector, element bounding box, and element type.

Text content is intentionally excluded so translated content does not break matching.

## Review and rerun

Review records are stored by capture context and language and influence Phase 3 filtering.

Operators can also request exact-context reruns using the same runtime dimensions.

## Artifacts

Common artifacts include:

- `url_inventory.json`
- `page_screenshots.json`
- `collected_items.json`
- `universal_sections.json`
- `template_rules.json`
- `eligible_dataset.json`
- `issues.json`

Artifacts are organized per domain and run.

## Current UI state

The UI includes useful operator tooling, but some screens are still exploratory or not fully release-hardened.

- Canonical multi-page operator workflow surfaces include `/urls`, `/workflow`, `/contexts`, `/pulls`, `/check-languages`, and `/` (issues).
- `/crawler` and `/pulling` still exist as auxiliary/internal-oriented tooling and are not the canonical release workflow path.
- The operator console is artifact-backed but remains pre-production overall.

Treat the interface as an operator/development console during pre-production, not a production-ready dashboard.
