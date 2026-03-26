# Polyglot Watchdog — Architecture (Non‑normative)

**Normative behavior is defined only in** `contract/watchdog_contract_v1.0.md`.

## Core components (conceptual)
- **Crawler**: discovers EN URLs and writes URL inventory.
- **Puller (Playwright)**: visits pages to extract visible text elements and `<img>` elements, and captures full-page screenshots.
- **Annotation UI**: lets a human label EN collected items (ignore / mask variable / always collect) with bulk actions + undo.
- **Reference builder**: creates EN reference dataset (filter-only mode or re-pull mode).
- **Pairing + Checks**: pairs curated EN items with curated target-language items, consumes OCR text for approved `<img>` elements, and produces AI-assisted translation QA issues.
- **Storage**: persistent GCP storage for all artifacts (URL inventories, pulls, annotations, references, issues, screenshots).

## Artifact flow (phases 0–6)
- Phase 0: `url_inventory` (canonical EN URLs) + `url_rules` (UI-managed drops)
- Phase 1: `page_screenshots`, `collected_items`, `universal_sections` (EN only)
- Phase 2: `template_rules` (manual labels)
- Phase 3: `eligible_dataset` (EN reference build)
- Phase 4: `phase4_ocr.json` OCR extraction artifact for approved `<img>` elements only. Canonical implementation path is `pipeline/phase4_ocr.py` + `pipeline/phase4_ocr_provider.py` (OCR.Space with Google Vision fallback and SVG deterministic prepass). Status contract: `ok` (usable normalized OCR text), `skipped` (intentionally not attempted for non-error reason), `failed` (attempted/expected but no valid OCR result). Phase 6 may consume this artifact when present and must continue safely when absent.
- Phase 5: normalization (deterministic; no double-space normalization)
- Phase 6: `issues` (AI-assisted translation QA findings + evidence for suspicious EN ↔ target pairs). Compares curated EN reference against curated target-language content; OCR text is consumed only for approved `<img>` elements and participates in the same EN ↔ target comparison flow. `category` stays the stable persisted contract enum; detailed QA classes are carried in evidence (for example `review_class`).

## Universal sections (header/footer)
After EN pull, repeating identical sections across many URLs (e.g., header/footer) can be collapsed into `universal_sections` to reduce redundancy and annotation load.

## Pagination avoidance
Pagination URL drops are not global canonicalization. They are controlled by UI-managed rules (e.g., drop `?page=` only under `/all-models/`).

## Viewports and states
Architecture supports multiple viewport kinds (desktop/mobile/responsive) and user states (guest/user tiers). Each page capture context has one screenshot.
