# Polyglot Watchdog — Architecture (Descriptive)

## Document Status
- **Type:** Architecture description
- **Normativity:** Non-normative
- **Authority:** Contract-first. This document MUST NOT override `contract/watchdog_contract_v1.0.md`.

## Component View
- **URL Discovery component:** produces canonical URL inventory.
- **Collection component:** extracts page-level element records and URL-level screenshot artifacts.
- **Annotation UI component:** captures reusable include/exclude/masking templates.
- **Filtered Rescan component:** applies template rules to produce eligible dataset.
- **OCR boundary component (deferred internals):** consumes image/page context and emits OCR-related outputs once defined.
- **Normalization component:** canonicalizes text form.
- **Localization QA component:** runs checks and generates issue artifacts.

## Artifact Flow (Conceptual)
1. URL inventory is generated.
2. Data collection produces two artifacts:
   - `page_screenshots`
   - `collected_items`
3. Annotation rules are created.
4. Filtered rescan creates eligible dataset.
5. OCR phase boundary receives eligible data (internals intentionally deferred).
6. Normalization processes text.
7. QA emits issues.

## Deterministic Principles
- Stable ordering of records.
- Stable IDs for equivalent inputs.
- Reproducible outputs for identical inputs.

## Modeling Constraint
Architecture assumes URL-level screenshot ownership:
- Screenshot belongs to URL/page context.
- Element-level records reference URL/page context only.
- No per-element screenshot model is part of architecture intent.
