# SPEC LOCK + EXECUTION PROTOCOL (STRICT MODE)

## 0. Authority
- This protocol governs AI implementation behavior.
- `contract/watchdog_contract_v1.0.md` defines normative system behavior guarantees.
- Implementations MUST conform to Contract v1.0 and MUST NOT change contract semantics without an explicit contract revision.

## 1. Non-negotiable execution rules
An Implementer AI MUST:
1. Treat Contract v1.0 + JSON Schemas in `contract/schemas/` as the only normative source of truth.
2. Implement phases in numeric order (0 → 6), preserving artifact handoffs.
3. Prove schema compatibility for every emitted artifact against the authoritative schema.
4. Preserve determinism requirements (stable sorting + stable IDs).

## 2. Forbidden behavior (hard STOP)
STOP immediately if any of the following occurs:
- Any required artifact schema is missing or ambiguous.
- Any artifact output shape is assumed without evidence.
- Per-element screenshot linkage is introduced (forbidden by Contract §3.1).
- Global query stripping is introduced without contract revision (Contract §4.1).
- Template rule scopes beyond per-element-per-URL are introduced (Contract Phase 2).

STOP format (single line):
`STOP: <reason>`

## 3. Required artifacts checklist (Contract v1.0)
Before implementation of each phase, confirm the artifact(s) and schemas:

- Phase 0: `url_inventory` + `url_rules`
  - `url_inventory.schema.json`
  - `url_rules.schema.json`
- Phase 1: `page_screenshots` + `collected_items` (+ `universal_sections` for EN only)
  - `page_screenshots.schema.json`
  - `collected_items.schema.json`
  - `universal_sections.schema.json`
- Phase 2: `template_rules`
  - `template_rules.schema.json`
- Phase 3: `eligible_dataset`
  - `eligible_dataset.schema.json`
- Phase 4: OPEN/DEFERRED (do not invent normative OCR schema)
- Phase 5: deterministic normalization (no double-space normalization)
- Phase 6: `issues`
  - `issues.schema.json`

## 4. Evidence-first rule
Whenever referencing existing code or behavior, the Implementer AI MUST cite:
- exact file paths
- exact function names
- exact emitted artifact filenames/locations

If evidence cannot be produced from the repository state, STOP.

## 5. Minimal-change discipline
- Do not refactor or reorganize.
- Do not add dependencies.
- Make the smallest diff that achieves contract compliance.
