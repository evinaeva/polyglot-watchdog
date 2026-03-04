# Polyglot Watchdog CLI Pipeline

This repository provides a minimal, deterministic command‑line pipeline for
detecting localization issues on websites. The pipeline reuses proven OCR
integrations and normalization logic from the `ai_ocr` project without
introducing any web server or database components.

## Overview

The pipeline performs the following steps for a given starting URL:

1. **Crawl**: Recursively visits the starting page and any same‑domain
   links discovered on each page. The URL queue is sorted to ensure
   deterministic ordering.
2. **Extract**: Retrieves visible text from each page’s DOM and captures
   a full‑page screenshot at a fixed viewport (1920×1080), user‑agent
   (`polyglot-watchdog/1.0`) and locale (`en‑US`).
3. **OCR**: Runs one or more OCR engines (Google Vision, Azure Computer
   Vision and OCR.Space) via the reused `app.ocr` module to extract
   text from screenshots.
4. **Normalize**: Normalizes both the DOM text and OCR output using
   functions from `utils.normalizer` to remove punctuation, unify case
   and collapse whitespace.
5. **Detect Issues**: Flags any line of DOM text whose normalized form
   does not appear in the normalized OCR output. Each issue records
   the page URL, line number, original text and normalized text.
6. **Export**: Writes a deterministic JSON report to
   `output/issues.json`. Issues and page URLs are sorted for repeatable
   results.

## Usage

Install the requirements in a clean Python environment:

```bash
pip install -r requirements.txt
playwright install --with-deps
