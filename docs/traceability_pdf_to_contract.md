# Traceability Matrix — INPUT DOCUMENTS to Contract v1.0

## Source Authority Statement
- **Source of requirements:** provided System Design text (INPUT DOCUMENTS in task prompt).
- Repository implementation artifacts do not override these requirements; they only implement and constrain them.

## Requirement Mapping

| Requirement ID | Source Doc | Source Section/Page | Source Statement (INPUT DOCUMENTS) | Contract Section | Schema Reference |
|---|---|---|---|---|---|
| R-001 | SystemDesignPDF | Architecture Overview / p.1 | Separate descriptive overview, normative contract, and strict AI protocol | §0 Authority and Precedence | N/A |
| R-002 | ContractExample | Authority section / p.1 | Contract is normative source of truth; overview cannot override | §0 Authority and Precedence | N/A |
| R-003 | Alignment | Determinism alignment / p.2 | Deterministic terminology and structure; explicit testable rules | §1 Determinism Requirements; §4 Artifact Contracts | All schemas under `contract/schemas/` |
| R-004 | SystemDesignPDF | Phase model / p.2 | Phase model fixed (0..6) | §2 Phase Model (Normative) | N/A |
| R-005 | Alignment | OCR status note / p.3 | Phase 4 OCR must remain explicitly incomplete/open | §4 PHASE 4 — OCR EXTRACTION (STATUS: OPEN / DEFERRED) | N/A |
| R-006 | SystemDesignPDF | Data collection model / p.3 | Screenshot model: 1 URL = 1 screenshot | §3.1 Core Rules; §4 Phase 1 | `contract/schemas/page_screenshots.schema.json` |
| R-007 | SystemDesignPDF | Data grouping / p.3 | Elements grouped by URL | §3.1 Core Rules; §4 Phase 1 rules | `contract/schemas/collected_items.schema.json` |
| R-008 | Alignment | Screenshot constraints / p.3 | Elements must NOT reference individual screenshots | §3.1 Core Rules; §3.2 Phase 1 Required Artifacts | `contract/schemas/collected_items.schema.json` |
| R-009 | Alignment | Artifact requirements / p.3 | Phase 1 must define separate page_screenshots artifact | §3.2 Phase 1 Required Artifacts; §4 Phase 1 | `contract/schemas/page_screenshots.schema.json` |
| R-010 | Alignment | Schema constraints / p.3 | No schema may assume per-element screenshots | §3.1 Core Rules; §3.2 prohibited fields | `contract/schemas/collected_items.schema.json` (`not` constraints) |
| R-011 | SystemDesignPDF | URL discovery / p.2 | URL inventory contract required | §4 Phase 0 — URL Discovery | `contract/schemas/url_inventory.schema.json` |
| R-012 | SystemDesignPDF | Annotation / p.2 | Template rule contract required | §4 Phase 2 — Annotation UI | `contract/schemas/template_rules.schema.json` |
| R-013 | SystemDesignPDF | Rescan / p.2 | Eligible dataset contract required | §4 Phase 3 — Filtered Rescan | `contract/schemas/eligible_dataset.schema.json` |
| R-014 | SystemDesignPDF | QA output / p.4 | Issues contract required | §4 Phase 6 — Localization QA | `contract/schemas/issues.schema.json` |
| R-015 | SpecLockExample | Strict mode / p.1 | AI execution must be strict and contract-locked | `spec/SPEC_LOCK_EXECUTION_PROTOCOL.md` §§0-4 | N/A |
| R-016 | Alignment | Scope semantics / p.3 | Template rule scope semantics must be explicit and testable | §4 Phase 2 — Annotation UI | `contract/schemas/template_rules.schema.json` (`scope` enum) |

## Coverage Conclusion
All mandatory requirements from the provided INPUT DOCUMENTS are mapped to a contract clause and, where applicable, a schema artifact.
