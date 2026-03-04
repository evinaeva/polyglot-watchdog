"""Command-line pipeline runner for polyglot-watchdog.

This script performs deterministic multi-page crawling within the same domain
and produces a JSON dataset of localization issues. The pipeline stages are:
1. Crawl starting from a base URL, discover same-domain links, and visit each.
2. Extract visible DOM text and capture a full-page screenshot via Playwright.
3. Run OCR using the reused ai_ocr app.ocr module to obtain raw text and
   confidence scores. Prefer OCR.Space for determinism when available.
4. Normalize both DOM and OCR text using utils.normalizer.normalize_strict.
5. Flag lines missing from OCR output as "missing_in_ocr" issues.
6. Export a deterministic list of issues to output/issues.json.

Run:
    python pipeline/pipeline_runner.py --url <base_url> --output output
or set TARGET_URL in the environment.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse, urljoin

# Ensure the project root is on sys.path before importing local modules. When
# this script is executed directly (``python pipeline/pipeline_runner.py``),
# Python resolves imports relative to the working directory and may not find
# the ``utils`` or ``app`` packages. Inserting the parent of this file
# (the repository root) into ``sys.path`` allows absolute imports to resolve.
project_root = str(Path(__file__).resolve().parents[1])
if project_root not in sys.path:
    sys.path.append(project_root)

from utils.normalizer import normalize_strict

try:
    from app.ocr import run_ocr_multi, ALL_ENGINES
except Exception:
    run_ocr_multi = None  # type: ignore
    ALL_ENGINES = []  # type: ignore

from playwright.async_api import async_playwright


async def _fetch_page(context, url: str) -> tuple[str, bytes, list[str]]:
    """Fetch a webpage and return its text, screenshot bytes and discovered links."""
    page = await context.new_page()
    await page.goto(url)
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    dom_text = await page.evaluate("document.body.innerText")
    screenshot_bytes = await page.screenshot(full_page=True)
    links = await page.evaluate(
        "Array.from(document.querySelectorAll('a[href]')).map(a => a.href)"
    )
    await page.close()
    return dom_text, screenshot_bytes, links


def _detect_issues(page_url: str, dom_text: str, ocr_text: str, avg_conf: float) -> list[dict]:
    """Return a list of issue dicts for lines not present in OCR text."""
    normalized_ocr = normalize_strict(ocr_text)
    issues: list[dict] = []
    for idx, line in enumerate(dom_text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        norm_line = normalize_strict(line)
        if norm_line and norm_line not in normalized_ocr:
            issues.append(
                {
                    "url": page_url,
                    "category": "missing_in_ocr",
                    "confidence": avg_conf,
                    "text": line,
                    "normalized_text": norm_line,
                    "line_number": idx,
                    "evidence": "text missing in OCR",
                }
            )
    return issues


async def run_pipeline(base_url: str, output_dir: str) -> None:
    """Perform multi-page crawl and issue detection."""
    if not callable(run_ocr_multi):
        raise RuntimeError(
            "OCR integration is unavailable; ensure ai_ocr/app/ocr.py is copied"
        )
    domain = urlparse(base_url).netloc
    visited: set[str] = set()
    pending: list[str] = [base_url]
    all_issues: list[dict] = []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="polyglot-watchdog/1.0",
            locale="en-US",
        )
        while pending:
            pending = sorted(pending)
            url = pending.pop(0)
            if url in visited:
                continue
            visited.add(url)
            try:
                dom_text, screenshot_bytes, links = await _fetch_page(context, url)
            except Exception:
                continue
            engines = [e for e in ["ocrspace"] if e in ALL_ENGINES] or ALL_ENGINES
            ocr_results = run_ocr_multi(screenshot_bytes, engines)
            ocr_text = "\n".join(res.text for res in ocr_results.values())
            confidences = [res.confidence or 0.0 for res in ocr_results.values()]
            avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
            issues = _detect_issues(url, dom_text, ocr_text, avg_conf)
            all_issues.extend(issues)
            # Discover same-domain links deterministically
            for link in links:
                if not link:
                    continue
                parsed = urlparse(link)
                if not parsed.netloc:
                    link = urljoin(url, link)
                    parsed = urlparse(link)
                if parsed.scheme not in ("http", "https"):
                    continue
                if parsed.netloc != domain:
                    continue
                link_no_frag = parsed._replace(fragment="").geturl()
                if link_no_frag not in visited and link_no_frag not in pending:
                    pending.append(link_no_frag)
        await browser.close()
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    out_path = Path(output_dir) / "issues.json"
    # Sort issues by URL and line number for deterministic output
    all_issues.sort(key=lambda item: (item["url"], item["line_number"]))
    with out_path.open("w", encoding="utf-8") as f:
        json.dump({"issues": all_issues}, f, ensure_ascii=False, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the localization QA pipeline")
    parser.add_argument("--url", help="Base URL to crawl")
    parser.add_argument("--output", default="output", help="Directory to write results")
    args = parser.parse_args()
    base_url = args.url or os.environ.get("TARGET_URL")
    if not base_url:
        print("Error: please specify --url or set TARGET_URL", file=sys.stderr)
        sys.exit(1)
    asyncio.run(run_pipeline(base_url, args.output))


if __name__ == "__main__":
    main()
