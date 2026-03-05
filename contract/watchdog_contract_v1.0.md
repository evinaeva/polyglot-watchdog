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
3. Elements MUST be grouped by URL (or `page_id` mapped to URL).
4. Elements MUST NOT reference individual screenshots.
5. No schema may require per-element screenshot ownership.

### 3.2 Phase 1 Required Artifacts
Phase 1 MUST emit:
- `page_screenshots` (URL-level screenshot inventory)
- `collected_items` (element/image records grouped by URL/page context)

`collected_items` records may reference:
- `url`
- `page_id`

`collected_items` records MUST NOT contain per-element screenshot fields including:

- `screenshotId`
- `element_screenshot`
- any equivalent field implying element-specific screenshot linkage

## 4. Artifact Contracts by Phase

### Phase 0 — URL Discovery
- **Output artifact:** `url_inventory`
- **Schema:** `contract/schemas/url_inventory.schema.json`

Rules:

- URLs MUST be canonicalized.
- Duplicates MUST be removed.
- Ordering MUST be deterministic.

---

### Phase 1 — Data Collection

**Output artifacts**

- `page_screenshots`
- `collected_items`

**Schemas**

- `contract/schemas/page_screenshots.schema.json`
- `contract/schemas/collected_items.schema.json`

Rules:

- `page_screenshots` MUST be a JSON object whose property names are URLs (`format=uri`).
- Each screenshot record MUST contain:

  - `screenshot_id`
  - `storage_uri`
  - `captured_at`

- `collected_items` records MUST contain:

  - `item_id`
  - `url`
  - `language`
  - `element_type`
  - `text`
  - `visible`

- `collected_items` MAY include:

  - `page_id`

- `collected_items` MUST NOT contain per-element screenshot linkage (`screenshotId`, `element_screenshot`, or equivalent).

- Text MAY be empty for non-textual or image-associated items.

---

### Phase 2 — Annotation UI

**Output artifact**

`template_rules`

**Schema**

`contract/schemas/template_rules.schema.json`

Rules:

- Rule semantics MUST be deterministic.
- Each rule MUST contain:

  - `rule_id`
  - `scope`
  - `url_pattern`
  - `selector`
  - `rule_type`

- `scope` MUST be one of:

  - `GLOBAL`
  - `DOMAIN`
  - `PATH`
  - `PAGE`

- Rules SHOULD be language-agnostic unless explicitly scoped.

---

### Phase 3 — Filtered Rescan

**Output artifact**

`eligible_dataset`

**Schema**

`contract/schemas/eligible_dataset.schema.json`

Rules:

- Derived deterministically from:

  - `collected_items`
  - `template_rules`

- Eligible records MUST contain:

  - `item_id`
  - `url`
  - `language`
  - `text`

- Excluded/ignored items MUST be removed from eligible outputs.

---

### PHASE 4 — OCR EXTRACTION

**STATUS: OPEN / DEFERRED**

Normative constraints for v1.0:

- Phase 4 OCR behavior is intentionally unspecified.
- Engine selection, output schema, and consensus logic will be defined after repository audit and reuse analysis.
- Do not define OCR engines, result schemas, or processing logic at this stage.
- Only phase boundary and artifact handoff intent are defined in v1.0.

---

### Phase 5 — Text Normalization

**Output artifact**

Normalized text dataset (project-defined name).

Rules:

- Unicode normalization MUST be deterministic.
- Whitespace normalization MUST be deterministic.
- Placeholder normalization MUST be deterministic and reproducible.

---

### Phase 6 — Localization QA

**Output artifact**

`issues`

**Schema**

`contract/schemas/issues.schema.json`

Rules:

- Each issue MUST contain:

  - `id`
  - `category`
  - `confidence`
  - `message`
  - `evidence`

- `suggestion` MAY be `string` or `null`.

- Allowed categories are defined by the enum in:
