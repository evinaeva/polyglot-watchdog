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

## 3. Comparison model

The primary comparison is:

`EN reference ↔ localized target text`

This is true for both DOM-backed text and image-backed text.

OCR remains **supporting input overall** and is **not** a separate main comparison model.
For approved image-backed items only, usable OCR may become the canonical target-side comparison text inside the same EN ↔ target flow; when OCR quality is not usable, Phase 6 falls back to normalized DOM text.

Phase 6 operates on **curated inputs only**:

- EN reference created after manual annotation/cleanup;
- target-language items captured for the same URLs, states, viewports, and tiers;
- pairing metadata that aligns EN and target items deterministically;
- OCR text only for approved image-based items;
- screenshots and bounding boxes needed for evidence.

Phase 6 must not run over a raw unfiltered site dump.

## 3.1 Two-layer classification model (canonical)

Phase 6 intentionally uses two classification layers:

- `issue.category` is the stable persisted contract category used by downstream consumers.
- `issue.evidence.review_class` is a richer internal Phase 6 QA classification used to explain why the issue was emitted.
- Multiple review classes may map into the same persisted contract category.

This means detailed QA classes (for example `SPELLING`, `GRAMMAR`, `MEANING`, `PLACEHOLDER`, `OCR_NOISE`) must remain evidence-level metadata, while persisted top-level categories stay backward-compatible.

## 4. OCR scope for Phase 6

Phase 6 assumes a **DOM-first pipeline with a narrow OCR exception for approved image-backed items**.

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
OCR output is an input to localization QA, not the final result by itself, and not a standalone issue-type generator. This OCR slice does not change the broader Phase 6 model, does not run whole-page OCR, does not OCR DOM text, and does not add multi-engine orchestration.

OCR should supply:

- extracted text
- engine metadata
- any quality/ambiguity signals available from the OCR pass

If OCR output is visibly weak or noisy, Phase 6 should lower trust in that pair and preserve the uncertainty in evidence rather than creating an overconfident translation claim.


### 4.5 Phase 4 OCR artifact contract (`phase4_ocr.json`)

Phase 4 emits `phase4_ocr.json` as an array of OCR rows for approved image-backed items only.

Current narrow contract:

- primary provider: `ocr.space` (engine `3`)
- fallback provider: `google_vision` (when OCR.Space is unavailable or returns empty/malformed results)
- statuses: `ok`, `skipped`, `failed`

Status semantics:

- `ok`: OCR completed and produced usable normalized text (`ocr_text`).
- `skipped`: OCR intentionally not attempted for a non-error reason (for example missing API key).
- `failed`: OCR attempted or expected but no valid result was produced (input/provider/processing failure).

OCR rows also include deterministic SVG text extraction fields:

- `asset_hash`: SHA-1 hash of the image asset
- `src`: image source URL or data URI
- `alt`: alt text
- `is_svg`: boolean indicating SVG format
- `svg_text`: extracted text from inline SVG (when deterministic extraction succeeds)

SVG text extraction is a deterministic pre-step before raster OCR; when SVG text is successfully extracted, raster OCR is skipped.

Phase 6 may consume this artifact when present, but must continue safely when it is absent. OCR text from this artifact is supporting input for approved image-backed items in EN ↔ target review; when quality is usable it may be used as canonical comparison text for that pair, and otherwise Phase 6 falls back to normalized DOM text. This does not create standalone issue categories or alter top-level contract taxonomy.

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

## 12. Phase 6 deterministic translation QA pipeline

Phase 6 has been refactored into a modular deterministic translation QA pipeline with the following structure:

### 12.0 Batched LLM review and prefetch support

Phase 6 now supports batched LLM review requests to improve efficiency and enable prefetching of review results before per-item review calls.

- `LLMReviewProvider` implements `prefetch_reviews` to batch items into size-aware requests and populate an internal cache (`_pair_reviews`). To reduce token usage and improve review accuracy, the provider uses a compact wire format for requests/responses, includes contextual flags in the payload, and de-duplicates identical items before sending (fanning out results upon receipt).
- Batching is controlled by configurable token budgeting parameters: `hard_context_tokens`, `token_reserve_ratio`, `fixed_token_margin`, `estimated_output_tokens_per_item`.
- The default LLM endpoint and model have been switched to OpenRouter-compatible configuration: `openrouter/free` model at `https://openrouter.ai/api/v1/chat/completions`.
- System prompt and token budgeting are now configurable via environment variables (`PHASE6_REVIEW_*` prefix).
- JSON response contract has been expanded to expect a `results` array with `item_id` keys for batched responses.
- Fallback handling is hardened with `_llm_result` and `_fallback_result` helper methods for deterministic offline fallback when the API is unavailable or response is malformed.
- Telemetry for AI-assisted reviews now includes detailed batch outcomes, token usage, costs, and fallback reasons, with `llm_review_stats.json` always persisted in a unified shape across `LLMReviewProvider`, `DeterministicOfflineProvider`, and `DisabledReviewProvider`.
- Error classification for LLM requests is improved to distinguish transport, parse, and provider failures, and to explicitly mark fallback usage.

### 12.1 Pipeline architecture

The Phase 6 pipeline consists of:

- **Provider layer** (`phase6_providers.py`): supplies curated EN and target-language items, pairing metadata, and evidence sources. Includes `LLMReviewProvider` with batched review support and configurable token budgeting.
- **Review layer** (`phase6_review.py`): runs deterministic and AI-assisted checks over paired items to identify suspicious localization cases. Includes `PreparedReviewInputs` dataclass and `prepare_review_inputs` function to centralize normalization, OCR selection/quality assessment, and dynamic counter normalization.
- **Runner** (`run_phase6.py`): orchestrates the pipeline, manages artifact I/O, and persists issues. It can now accept an optional `prepared_llm_payload` to avoid recomputing pairing/contexts, and precomputes `prepare_review_inputs` for finalized item pairs and calls `provider.prefetch_reviews` when available to warm a single batched request before per-item review calls.

### 12.2 Dynamic counter normalization

Phase 6 normalizes dynamic counters (e.g., "1 item", "2 items") to a canonical form before comparison.

This prevents false positives when the same content appears with different numeric values across languages.

### 12.2a Interaction trace hashing

When a screenshot is captured as part of a scripted recipe execution, the executed recipe steps are hashed to produce an `interaction_trace_hash` (SHA-1). This hash is persisted in the `page_screenshots` artifact and allows reruns to be correlated with the original scripted interactions.

### 12.3 Prepared review inputs and OCR selection

Phase 6 centralizes DOM/OCR text preparation through `prepare_review_inputs`, which:

- normalizes and validates EN and target-language text;
- selects the best available OCR text for approved image-backed items (preferring usable OCR over DOM text when quality is acceptable);
- performs dynamic counter normalization to prevent false positives when numeric values differ across languages;
- returns a `PreparedReviewInputs` dataclass with canonical comparison inputs ready for AI-assisted and deterministic checks.

This ensures that the review pipeline reuses canonical comparison inputs and enables prefetching of finalized pairs.

### 12.4 Missing-target evidence sourcing

When a target-language item is missing (not captured or not found in the pairing), Phase 6 generates evidence that includes:

- the EN reference item details;
- the expected capture context (URL, state, viewport, tier);
- a clear indication that the target was not found.

This allows operators to understand why an issue was generated and to investigate missing captures.

### 12.5 Evidence signals

Phase 6 evidence includes deterministic signals that contributed to issue generation:

- text comparison results (EN vs. target);
- placeholder consistency checks;
- OCR quality signals when applicable;
- AI-assisted review signals (spelling, grammar, meaning);
- batched prefetch metadata indicating which items were reviewed in a single batch request.

These signals are preserved in the persisted issue artifact so that operators can understand the reasoning behind each issue.

## 13. Non-goals

Phase 6 does **not** exist to:

- replace human translation review entirely;
- run OCR over the whole page or over arbitrary screenshots;
- auto-fix text in the persisted source artifacts;
- treat every OCR result as trustworthy;
- treat every mismatch as equally certain.

The correct outcome is a smaller, evidence-backed review queue for a human operator.


## 14. Review mode and image coverage reporting

- Phase 6 runtime requires an explicit review mode (`test-heuristic`, `disabled`, or `llm`) via CLI flag or `PHASE6_REVIEW_PROVIDER`. Missing mode is a hard error.
- Phase 6 emits `coverage_gaps.json` for image-backed target items that were not actually image-text-reviewed.
- Coverage status is tracked independently from `issues.json` and uses:
  - `image_text_reviewed`
  - `image_text_not_reviewed`
  - `image_text_review_blocked`
- Coverage rows include `asset_hash`, `src`, `alt`, `is_svg`, and `svg_text` (when deterministic SVG text extraction succeeds).
- SVG text extraction is a deterministic pre-step before OCR for inline SVG data URIs.
- Stale background jobs are normalized to failed state when reading latest status and when checking for duplicate in-progress jobs.
- Explicit artifact gates ensure missing outputs terminalize the job at the correct stage: `page_screenshots.json` and `collected_items.json` after Phase 1, `eligible_dataset.json` after Phase 3, and `issues.json` after Phase 6.
