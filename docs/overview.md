# Polyglot Watchdog — System Overview (Descriptive)

## Document Status
- **Type:** Descriptive
- **Normativity:** Non-normative
- **Authority:** This document MUST NOT override `contract/watchdog_contract_v1.0.md`.

## Purpose
Polyglot Watchdog is a localization QA pipeline intended to identify translation quality problems in website UI text and text extracted from page imagery. The system supports deterministic re-runs and staged artifact handoffs.

## System Goals
- Discover canonical website URLs for analysis.
- Collect user-visible UI content grouped by page URL.
- Support manual annotation to separate relevant and irrelevant data.
- Rescan with rule-based filtering for cleaner QA inputs.
- Prepare OCR phase boundaries for image text extraction.
- Normalize text for robust automated quality checks.
- Emit localization issue records for QA review.

## Phase Model (Descriptive)
- **Phase 0 — URL Discovery**
- **Phase 1 — Data Collection**
- **Phase 2 — Annotation UI**
- **Phase 3 — Filtered Rescan**
- **Phase 4 — OCR Extraction**
- **Phase 5 — Text Normalization**
- **Phase 6 — Localization QA**

## Screenshot Model (High-Level)
The system uses URL-level screenshots as page artifacts:
- 1 URL = 1 screenshot artifact.
- Elements are grouped under a URL/page context.
- Elements do not carry individual screenshot ownership.

## Notes
This overview explains intent and vocabulary only. All enforceable requirements, schema constraints, and testable rules are defined in the Contract.
