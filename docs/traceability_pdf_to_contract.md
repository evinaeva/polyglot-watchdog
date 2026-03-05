# Traceability Matrix — Sources to Contract v1.0

This matrix maps high-level requirement statements to normative clauses and schemas.

## Source Authority
Normative authority is:
- `contract/watchdog_contract_v1.0.md`
- `contract/schemas/*.json`

Sources used for requirement intent:
- **CHAT AGREEMENTS 2026-03-05** (this conversation)
- **SYSTEM DESIGN PDF** (`Системный дизайн_ Многопоточный QA-пайплайн для мультиязычной локализации UI.pdf`) (high-level architecture intent)

## Requirement Mapping

| Requirement ID | Source Doc | Source Section/Page | Source Statement | Contract Clause | Schema(s) |
|---|---|---|---|---|---|
| R-001 | CHAT AGREEMENTS 2026-03-05 | Flow | EN crawl → EN pull → manual EN labeling → EN reference → pull target subdomain(s) → pairing → translator cascade → issues | Contract §2, §6 | (phase artifacts) |
| R-002 | CHAT AGREEMENTS 2026-03-05 | UI | UI pages: /crawler, /pulling, / (issues on demand), /about glossary | Overview.md + Architecture.md (non-normative) | — |
| R-003 | CHAT AGREEMENTS 2026-03-05 | Screenshots | 1 URL = 1 full-page screenshot (no per-element screenshots) | Contract §3.1 | page_screenshots, collected_items |
| R-004 | CHAT AGREEMENTS 2026-03-05 | Viewports | Must support desktop/mobile/responsive | Contract §3.2 | page_screenshots, collected_items |
| R-005 | CHAT AGREEMENTS 2026-03-05 | State | Must support guest and user tiers | Contract §3.3 | page_screenshots, collected_items |
| R-006 | CHAT AGREEMENTS 2026-03-05 | IDs | Stable item_id based on domain+url+selector+bbox+type, not text; rescan shows NOT FOUND and continues | Contract §3.4–§3.5 | collected_items, template_rules |
| R-007 | CHAT AGREEMENTS 2026-03-05 | URL rules | Ignore pagination only for specified URL patterns (e.g., /all-models/*?page=) and manage rules via UI | Contract §4.2 | url_rules, url_inventory |
| R-008 | CHAT AGREEMENTS 2026-03-05 | Canon | Merge http/https to https; remove fragments; do not globally strip query | Contract §4.1 | url_inventory |
| R-009 | CHAT AGREEMENTS 2026-03-05 | Annotation | No global precedence: manual labels are per element per URL | Contract §6 Phase 2 | template_rules |
| R-010 | CHAT AGREEMENTS 2026-03-05 | Universal | Collapse identical header/footer across URLs into universal sections | Contract §5 | universal_sections |
| R-011 | CHAT AGREEMENTS 2026-03-05 | Numbers | Do not blanket-exclude numbers/prices; may affect grammar/pluralization | Contract §6 Phase 1 | collected_items |
| R-012 | CHAT AGREEMENTS 2026-03-05 | Spaces | Do not normalize double spaces away | Contract §6 Phase 1, Phase 5 | — |
| R-013 | CHAT AGREEMENTS 2026-03-05 | Issues | Issues by categories with evidence (url + screenshot reference + bbox) | Contract §6 Phase 6 | issues |
| R-014 | SYSTEM DESIGN PDF | High-level | Multi-phase pipeline with persistent storage and UI for review | Contract §2, Overview.md | (phase artifacts) |

