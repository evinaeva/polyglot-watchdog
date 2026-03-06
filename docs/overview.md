# Polyglot Watchdog — Overview (Non‑normative)

This document describes the intended product at a high level.  
**Normative behavior is defined only in** `contract/watchdog_contract_v1.0.md`.

## Goal
Continuously detect suspicious localization issues by comparing a saved **EN reference** against language subdomains (e.g., `fr.example.com`) using:
- URL discovery (EN)
- page pulling/extraction (text + images)
- manual EN curation (ignore / always collect / mask variable)
- EN reference build (filter-only or re-pull)
- pairing EN ↔ target content
- translator cascade + QA checks
- issue review UI with evidence (screenshot + bbox)

## Target end-to-end flow (summary)
1. Crawl URLs from EN base domain.
2. Pull all EN URLs (extract visible text elements + `<img>` elements; capture full-page screenshots).
3. Manual review/annotation of EN collected items.
4. Build EN reference (filtered dataset or re-pull).
5. Pull target language subdomain(s).
6. Pair EN reference items with target items.
7. Run translator cascade.
8. Present suspicious pairs grouped by issue categories (query-driven; empty by default).

## UI pages
- `/crawler`: collect URLs for a base domain and persist them.
- `/pulling`: pull content for EN/target subdomains, persist per-URL results incrementally, provide cross-filtering and annotation tools.
- `/`: issues explorer (shows results only after user query).
- `/about`: glossary of product terms (filled after implementation once term set is complete).

## Persistence
All artifacts must be stored in persistent GCP storage so they remain available across rebuilds and support rescans months later.

## Key product constraints
- One full-page screenshot per URL capture context (not per element).
- Avoid crawling pagination URLs only for explicitly configured patterns (UI-managed rules).
- Double spaces are not normalized away (may indicate errors).
- Numeric/price strings are not automatically excluded (may affect pluralization/grammar).
