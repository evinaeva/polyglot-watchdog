# Phase 6 — Translation QA and Issue Generation (Non-normative)

This document captures the intended Phase 6 behavior for localization QA on **CHECK LANGUAGES** and the persisted issue flow shown on **SEE ERRORS**.

Normative artifact constraints still come from `contract/watchdog_contract_v1.0.md` and `contract/schemas/issues.schema.json`.  
This file defines the intended **Phase 6 review logic**, **OCR scope**, and **AI-assisted checks** without changing code or schemas.

## 1. Purpose

Phase 6 is not a generic diff step and not a UI-only listing page.

Its purpose is to:

- compare the curated English reference against the curated target-language dataset;
- include text extracted from approved images when relevant;
- run deterministic and AI-assisted translation checks;
- produce only **suspicious cases** for human review;
- persist those cases as issues with reproducible evidence.

The operator should not have to manually read every pair.  
Phase 6 exists to narrow review down to likely localization problems.

## 2. Inputs to Phase 6

Phase 6 operates on curated inputs only:

- **EN reference** created after manual annotation/cleanup;
- **target-language items** captured for the same URLs, states, viewports, and tiers;
- **pairing metadata** that aligns EN and target items deterministically;
- **OCR text** only for approved image-based items;
- screenshots and bounding boxes needed for evidence.

Phase 6 must not run over a raw unfiltered site dump.

## 3. Comparison model

The primary comparison is:

`EN reference ↔ localized target text`

This is true for both DOM-backed text and image-backed text.

OCR is **not** the main comparison target.  
OCR is only a way to supply text for image-based content so that those items can also participate in the EN ↔ target comparison flow.

## 4. OCR scope for Phase 6

Phase 6 assumes a strict **DOM-first** model.

### 4.1 What gets OCR
OCR is applied **only** to `<img>` elements.

No broader OCR-on-screenshot strategy is part of this design.

### 4.2 Which `<img>` elements are allowed
Only `<img>` items that were explicitly kept for checking are expected to flow into OCR-backed review.

This keeps OCR limited to image content that matters for localization QA, such as:

- banners
- promotional artwork
- image-based CTA text
- other text embedded directly inside approved `<img>` assets

### 4.3 OCR engine choice
The baseline OCR choice for this Phase 6 design is:

- **OCR.Space**
- using **engine 3**

This is the default OCR path that Phase 6 expects when OCR text is present for approved `<img>` items.

### 4.4 OCR role in Phase 6
OCR output is an input to localization QA, not the final result by itself.

OCR should supply:

- extracted text
- engine metadata
- any quality/ambiguity signals available from the OCR pass

If OCR output is visibly weak or noisy, Phase 6 should lower trust in that pair and preserve the uncertainty in evidence rather than creating an overconfident translation claim.

## 5. Checks that Phase 6 must perform

Phase 6 is expected to run a combined review layer with both deterministic checks and AI-assisted checks.

The intended review classes are:

- `SPELLING`
- `GRAMMAR`
- `MEANING`
- `PLACEHOLDER`
- `OCR_NOISE`
- `OTHER`

Typical examples:

- spelling mistakes in localized UI text;
- grammar problems in the target language;
- meaning drift versus the EN reference;
- placeholder removal/addition/format damage;
- suspicious OCR output that makes an image-text comparison unreliable;
- unusual cases that do not fit a narrower class.

This layer is meant to identify suspicious pairs, not to auto-correct them.

## 6. AI-assisted review on CHECK LANGUAGES

The CHECK LANGUAGES experience is expected to be backed by an AI-assisted translation QA layer.

That layer should:

- inspect the paired EN and target texts;
- flag likely spelling and grammar problems in the target language;
- flag likely meaning mismatches versus the EN reference;
- preserve uncertainty rather than forcing a binary pass/fail;
- surface suspicious cases for human review.

The AI layer should operate on the curated dataset only.  
It should not be asked to reason over irrelevant, ignored, or unfiltered raw capture noise.

## 7. Placeholder and formatting safety

Placeholder consistency is part of Phase 6, not an afterthought.

Phase 6 should detect at least:

- placeholder removed;
- placeholder added;
- placeholder format changed;
- masked-variable handling that changes the semantic structure of the text.

The review logic should not over-normalize source text in a way that hides real formatting or translation problems.

In particular:

- double spaces must not be normalized away by default;
- numbers and prices must not be blanket-ignored inside Phase 6.

## 8. Confidence handling

A Phase 6 issue should expose one final top-level `confidence` value for operator use.

Supporting signals should remain visible in evidence, for example:

- AI/translation-review confidence;
- OCR quality or OCR ambiguity notes;
- similarity or mismatch signals;
- placeholder rule triggers;
- any rule-based reasons that contributed to the issue.

This keeps the operator-facing artifact simple while preserving enough detail for manual verification.

## 9. Evidence requirements for persisted issues

At minimum, Phase 6 evidence should preserve enough context for a reviewer to reproduce the finding.

Recommended evidence fields include:

- `url`
- `screenshot_uri`
- `bbox`
- `page_id`
- `item_id`
- `text_en`
- `text_target`
- `ocr_text` when the item came from an approved `<img>`
- `ocr_engine`
- `reason`
- supporting scores or notes used to derive confidence

## 10. Relationship to the current `issues` schema

The current repository schema for `issues` remains the persisted artifact contract.

That schema is still the authority for the top-level issue object shape and the currently allowed `category` enum.

At the same time, the detailed Phase 6 review classes in this document are more specific than the existing coarse issue buckets.

Until the schema is revised, the intended detailed review class should be preserved in evidence-level metadata or message content rather than lost entirely.

## 11. UI expectations

### CHECK LANGUAGES
CHECK LANGUAGES is expected to show suspicious EN ↔ target pairs produced by Phase 6 review logic.

It should help the operator inspect likely problems such as:

- spelling
- grammar
- meaning mismatch
- placeholder damage
- OCR-related uncertainty

### SEE ERRORS
SEE ERRORS is expected to read persisted Phase 6 issue artifacts and their evidence.

The page should not depend on re-running OCR or AI checks during page rendering.  
It should display what Phase 6 already generated and stored.

## 12. Non-goals

Phase 6 does **not** exist to:

- replace human translation review entirely;
- run OCR over the whole page or over arbitrary screenshots;
- auto-fix text in the persisted source artifacts;
- treat every OCR result as trustworthy;
- treat every mismatch as equally certain.

The correct outcome is a smaller, evidence-backed review queue for a human operator.
