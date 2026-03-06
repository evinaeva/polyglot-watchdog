# Polyglot Watchdog Contract v1.0

## 0. Authority and Precedence
1. This Contract is the **normative source of truth** for required system behavior.
2. Descriptive files (`docs/overview.md`, `docs/architecture.md`) are **non-normative** and MUST NOT override this Contract.
3. If descriptive content conflicts with this Contract, this Contract prevails.

## 1. Determinism Requirements
For identical inputs and configuration, each implemented phase MUST produce deterministic outputs.

Mandatory rules:
- Stable ordering of arrays/records (explicit sort keys).
- Stable IDs for equivalent entities.
- Reproducible serialization and field presence.

Failure rule:
- If determinism cannot be guaranteed for a required artifact, execution MUST stop with an explicit error state.

## 2. Phase Model (Normative)
The system phase model is fixed and MUST use exactly:
1. Phase 0 — URL Discovery (EN)
2. Phase 1 — Data Collection (EN + target languages)
3. Phase 2 — Annotation UI (EN manual labeling)
4. Phase 3 — Filtered Rescan / EN Reference Build
5. Phase 4 — OCR Extraction (OPEN / DEFERRED)
6. Phase 5 — Text Normalization
7. Phase 6 — Localization QA (Issues)

No additional phases are permitted in Contract v1.0.

## 3. Core Data Modeling Rules (Normative)

### 3.1 Screenshot rule (URL-level, not element-level)
1. **No per-element screenshots** are permitted.
2. For each capture context, **one full-page screenshot** MUST be produced:
   - capture context = (`url`, `viewport_kind`, `state`, `user_tier`)
3. Elements MUST reference the capture context via `page_id`.
4. Elements MUST NOT reference screenshots directly.

### 3.2 Viewports
The architecture MUST support three viewport kinds:
- `desktop`
- `mobile`
- `responsive`

### 3.3 User states / tiers
Captures MAY be performed for:
- `guest`
- `user` with tier in: `Free`, `Gold`, `Platinum`, `Unlimited`, `Sapphire`, `Titan`, `Diamond`, `Exclusive`, `VIP`

(Exact authentication mechanics are out of scope for this contract version, but data model MUST support distinguishing these contexts.)

### 3.4 Stable ID policy (normative)
`item_id` MUST be stable and deterministic.

Required definition:

```
item_id = sha1(
  domain +
  url +
  css_selector +
  bbox(x,y,width,height) +
  element_type
)
```

Notes:
- `text` MUST NOT be part of `item_id`.
- `domain` is the EN base domain being processed (e.g., `example.com`).

### 3.5 Rescan fallback when element cannot be located
On re-pull / re-scan, if a previously annotated element cannot be located:
- The system MUST surface a non-fatal error record in UI:
  - `URL | item_id | last_known_text | NOT FOUND`
- The system MUST continue scanning other elements/URLs.

## 4. Canonicalization and URL Rules (Normative)

### 4.1 Canonicalization minimum rules (Phase 0)
Canonicalization MUST apply:
1. Remove URL fragments (`#...`).
2. Normalize scheme to **https** (http/https MUST be merged to https).

Canonicalization MUST NOT (in v1.0):
- globally strip all query parameters
- globally alter trailing slashes
- globally alter `www.` handling
unless explicitly added later as a separate contract version.

### 4.2 UI-managed URL rules (pagination drops)
The system MUST support UI-managed URL drop rules to avoid crawling/pulling unwanted pagination URLs for **specific path patterns**.

- Output artifact: `url_rules`
- Schema: `contract/schemas/url_rules.schema.json`

Rule application:
- If a `url_rules` rule matches an URL and action is `DROP_URL`, the URL MUST be excluded from crawling/pulling inventories.

Example intent:
- allow: `/all-models/n`
- drop: `/all-models/n?page=2` (only for configured rules)

## 5. Universal Sections Collapsing (EN) (Normative)
After Phase 1 EN collection, repeating sections with identical element sets and identical content (e.g., header/footer) MUST be collapsible into a shared “universal section” dataset.

- Output artifact: `universal_sections` (EN only)
- Schema: `contract/schemas/universal_sections.schema.json`

Rules:
- Each universal section MUST have a stable `fingerprint`.
- Each universal section MUST store one representative URL/page capture:
  - `representative_url`
  - `representative_page_id`
- The representative URL/page MUST be the first observed occurrence (deterministic by URL ordering) unless a different deterministic rule is specified later.

## 6. Artifact Contracts by Phase

### Phase 0 — URL Discovery (EN)
- Output artifact: `url_inventory`
- Schema: `contract/schemas/url_inventory.schema.json`

Rules:
- Must use canonicalization rules in §4.1.
- Must apply UI-managed drops in §4.2.
- Must remove duplicates.
- Ordering MUST be deterministic.

---

### Phase 1 — Data Collection

**Output artifacts**
- `page_screenshots`
- `collected_items`
- `universal_sections` (EN only; see §5)

**Schemas**
- `contract/schemas/page_screenshots.schema.json`
- `contract/schemas/collected_items.schema.json`
- `contract/schemas/universal_sections.schema.json` (EN only)

Rules:
- `page_screenshots` MUST be a list of page capture records.
- Each `page_screenshots` record MUST correspond to exactly one full-page screenshot for a capture context.
- Each `collected_items` record MUST reference `page_id` and MUST NOT embed screenshot identifiers.
- Double spaces MUST NOT be normalized at collection time (they may be used as an error signal later).
- Numeric/price strings MUST NOT be blanket-excluded automatically; they may be relevant for pluralization/grammar.

---

### Phase 2 — Annotation UI (EN manual labeling)

**Output artifact**
- `template_rules`

**Schema**
- `contract/schemas/template_rules.schema.json`

Rules:
- Rules are **per element per URL** (no GLOBAL/DOMAIN/PATH scopes in v1.0).
- Rule semantics MUST be deterministic and reproducible.
- Bulk actions (mass labeling) are permitted only if:
  - UI shows a dry-run preview (count + examples) before apply
  - UI records operations such that the last operation can be undone

---

### Phase 3 — Filtered Rescan / EN Reference Build

**Output artifact**
- `eligible_dataset`

**Schema**
- `contract/schemas/eligible_dataset.schema.json`

Rules:
- Derived deterministically from `collected_items` + `template_rules` (Filter-only mode),
  OR produced by re-pulling pages (Re-pull mode) using the same URL inventory.
- EN reference creation time MUST be recorded and surfaced in UI (`created_at` concept).

---

### Phase 4 — OCR EXTRACTION

**STATUS: OPEN / DEFERRED**

Normative constraints for v1.0:
- Phase 4 OCR behavior is intentionally unspecified at the contract level.
- Engine selection, output schema, and consensus logic will be defined after repository audit and reuse analysis.
- Do not define OCR engines, result schemas, or processing logic as normative requirements in Contract v1.0.
- Only phase boundary and handoff intent are defined in v1.0.

---

### Phase 5 — Text Normalization
Rules:
- Normalization MUST be deterministic and reproducible.
- Double spaces MUST NOT be normalized away.
- Additional normalization rules will be defined after audit based on real extracted content.

---

### Phase 6 — Localization QA

**Output artifact**
- `issues`

**Schema**
- `contract/schemas/issues.schema.json`

Rules:
- Each issue MUST contain:
  - `id`
  - `category`
  - `confidence`
  - `message`
  - `evidence`
- Allowed categories are defined by the enum in `contract/schemas/issues.schema.json`.
- Evidence MUST include at least:
  - `url`
  - `bbox`
  - screenshot storage reference (e.g., `storage_uri` from `page_screenshots`)

## 7. Schema Authority
The following JSON Schemas are normative for Contract v1.0:
- `contract/schemas/url_inventory.schema.json`
- `contract/schemas/url_rules.schema.json`
- `contract/schemas/page_screenshots.schema.json`
- `contract/schemas/collected_items.schema.json`
- `contract/schemas/universal_sections.schema.json`
- `contract/schemas/template_rules.schema.json`
- `contract/schemas/eligible_dataset.schema.json`
- `contract/schemas/issues.schema.json`
