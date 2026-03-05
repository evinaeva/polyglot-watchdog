# Polyglot Watchdog Contract v1.0

## 0. Authority and Precedence
1. This Contract is the **normative source of truth** for required system behavior.
2. Descriptive files (`docs/overview.md`, `docs/architecture.md`) are non-normative and MUST NOT override this Contract.
3. If descriptive content conflicts with this Contract, this Contract prevails.

## 1. Determinism Requirements
For identical inputs and configuration, each implemented phase MUST produce deterministic outputs.

Mandatory rules:
- Stable ordering of arrays/records.
- Stable IDs for equivalent entities.
- Reproducible serialization and field presence.

Failure rule:
- If determinism cannot be guaranteed for a required artifact, execution MUST stop with explicit error state.

## 2. Phase Model (Normative)
The system phase model is fixed and MUST use exactly:
1. Phase 0 — URL Discovery
2. Phase 1 — Data Collection
3. Phase 2 — Annotation UI
4. Phase 3 — Filtered Rescan
5. Phase 4 — OCR Extraction
6. Phase 5 — Text Normalization
7. Phase 6 — Localization QA

No additional phases are permitted in Contract v1.0.

## 3. Screenshot and Grouping Contract (Normative)
### 3.1 Core Rules
1. **1 URL = 1 screenshot**.
2. Screenshots are URL-level artifacts.
3. Elements MUST be grouped by URL (or page_id mapped to URL).
4. Elements MUST NOT reference individual screenshots.
5. No schema may require per-element screenshot ownership.

### 3.2 Phase 1 Required Artifacts
Phase 1 MUST emit:
- `page_screenshots` (URL-level screenshot inventory)
- `collected_items` (element/image records grouped by URL/page context)

`collected_items` records may reference:
- `url` and/or `page_id`

`collected_items` records MUST NOT contain per-element screenshot fields including:
- `screenshotId`
- `element_screenshot`
- any equivalent field implying element-specific screenshot linkage

## 4. Artifact Contracts by Phase

### Phase 0 — URL Discovery
- **Output artifact:** `url_inventory`
- **Schema:** `contract/schemas/url_inventory.schema.json`
- **Rules:**
  - URLs MUST be canonicalized.
  - Duplicates MUST be removed.
  - Ordering MUST be deterministic.

### Phase 1 — Data Collection
- **Output artifacts:** `page_screenshots`, `collected_items`
- **Schemas:**
  - `contract/schemas/page_screenshots.schema.json` (for `page_screenshots`)
  - `contract/schemas/collected_items.schema.json` (for `collected_items`)
- **Rules:**
  - `page_screenshots` MUST be a JSON object whose property names are URLs (`format=uri`), mapped to screenshot records that include `screenshot_id`, `storage_uri`, and `captured_at`.
  - `collected_items` records MUST include required keys: `item_id`, `url`, `language`, `element_type`, `text`, `visible`.
  - `collected_items` records MAY include URL grouping context via `page_id`.
  - `collected_items` records MUST NOT include per-element screenshot linkage (`screenshotId`, `element_screenshot`, or equivalent).
  - Text MAY be empty for non-textual/image-associated items.

### Phase 2 — Annotation UI
- **Output artifact:** `template_rules`
- **Schema:** `contract/schemas/template_rules.schema.json`
- **Rules:**
  - Rule semantics MUST be deterministic.
  - Each rule MUST include: `rule_id`, `scope`, `url_pattern`, `selector`, `rule_type`.
  - `scope` MUST be one of: `GLOBAL`, `DOMAIN`, `PATH`, `PAGE`.
  - Rules SHOULD be language-agnostic unless explicitly scoped.

### Phase 3 — Filtered Rescan
- **Output artifact:** `eligible_dataset`
- **Schema:** `contract/schemas/eligible_dataset.schema.json`
- **Rules:**
  - Derived deterministically from collected items and template rules.
  - Eligible records MUST include: `item_id`, `url`, `language`, `text`.
  - Excluded/ignored items MUST be removed from eligible outputs.

### PHASE 4 — OCR EXTRACTION
**STATUS: OPEN / DEFERRED**

Normative constraints for v1.0:
- Phase 4 OCR behavior is intentionally unspecified.
- Engine selection, output schema, and consensus logic will be defined after repository audit and reuse analysis.
- Do not define OCR engines, result schemas, or processing logic at this stage.
- Only phase boundary and artifact handoff intent are defined in v1.0.

### Phase 5 — Text Normalization
- **Output artifact:** normalized text dataset (project-defined name).
- **Rules:**
  - Unicode normalization approach MUST be deterministic.
  - Whitespace and placeholder normalization MUST be deterministic and reproducible.

### Phase 6 — Localization QA
- **Output artifact:** `issues`
- **Schema:** `contract/schemas/issues.schema.json`
- **Rules:**
  - Each issue MUST include: `id`, `category`, `confidence`, `message`, `evidence`.
  - `suggestion` MAY be `string` or `null`.
  - Allowed categories are defined by the enum in `contract/schemas/issues.schema.json`.
  - Each issue MUST include machine-readable evidence metadata.

## 5. Schema Authority
The following schemas are normative for their artifacts:
- `contract/schemas/url_inventory.schema.json`
- `contract/schemas/page_screenshots.schema.json`
- `contract/schemas/collected_items.schema.json`
- `contract/schemas/template_rules.schema.json`
- `contract/schemas/eligible_dataset.schema.json`
- `contract/schemas/issues.schema.json`

If implementation behavior conflicts with these schemas and this Contract text, implementation is non-compliant.

## 6. Logging and Time Format Constraints
- Logs SHOULD be structured and machine-parseable.
- Sensitive values (secrets/tokens/raw private data) MUST NOT be emitted.
- Datetime values, when present in contract artifacts, MUST use UTC ISO-8601 (`YYYY-MM-DDTHH:MM:SSZ`).
Это нормативный документ.

Он аналогичен Project Contract v1.3 из ai_ocr. 

Project_Contract_v1.3

Polyglot Watchdog Contract v1.0
0. Authority

This Contract is the normative source of truth for system behavior.

Overview and architecture documents are descriptive and MUST NOT override the Contract.

1. Determinism Requirements

All pipeline stages MUST produce deterministic outputs given identical inputs.

Requirements:

stable ordering of collections

stable identifiers

reproducible outputs

If determinism cannot be guaranteed, the pipeline MUST stop with explicit error.

2. Phase Contracts

Each phase has:

input artifact

output artifact

deterministic rules

Phase 0 — URL Inventory
Input

Crawler configuration

Output

url_inventory.json

Schema:

array[string]

Rules:

URLs MUST be canonicalized

duplicates MUST be removed

ordering MUST be deterministic (lexicographic)

Phase 1 — Collected Items

Output file:

collected_items.json

Schema defined in:

schemas/collected_items.schema.json

Record format:

{
"url": string,
"language": string,
"state": "guest" | "auth",
"userTier": string | null,
"pageTitle": string,
"elementType": string,
"text": string,
"elementIdentity": object,
"cssSelector": string,
"visible": boolean,
"screenshotId": string
}

Rules:

every collected element MUST reference a page screenshot

text MAY be empty for images

elementIdentity fields MAY be null

Phase 2 — Template Rules

Output artifact:

template_rules.json

Schema:

{
"scope": string,
"userTier": string,
"urlPattern": string,
"selector": string,
"ruleType": string
}

Allowed rule types:

IGNORE_ENTIRE_ELEMENT

MASK_VARIABLE

ALWAYS_COLLECT

Rules MUST be language-agnostic.

Phase 3 — Eligible Dataset

Output:

eligible_dataset.json

Derived from:

collected_items.json
template_rules.json

Rules:

ignored elements MUST be excluded

masked variables MUST be replaced with placeholder

Phase 4 — OCR Results

Output:

ocr_results.json

Each record MUST contain:

{
"element_id": string,
"text": string,
"confidence": number,
"engine": string
}

Rules:

OCR engines MAY run sequentially

fallback engine allowed if first engine fails

Phase 5 — Normalized Text

Output:

normalized_text.json

Normalization rules:

Unicode NFC

whitespace normalization

placeholder canonicalization

Phase 6 — Localization Issues

Output:

issues.json

Schema:

{
"id": string,
"category": string,
"confidence": number,
"message": string,
"suggestion": string | null,
"evidence": object
}

Categories:

SPELLING

GRAMMAR

MEANING

PLACEHOLDER

OCR_NOISE

OTHER

3. Logging

All logs MUST be structured JSON.

Logs MUST NOT include:

raw user text

secrets

OCR image bytes

4. API Date Format

Datetime values MUST follow:

YYYY-MM-DDTHH:MM:SSZ

UTC only.
