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
