"""Phase 1 runner — Data Collection.

Usage:
    python pipeline/run_phase1.py --domain example.com --run-id <run_id> --language en

Reads url_inventory from GCS (written by Phase 0).
Outputs to GCS:
    gs://{ARTIFACTS_BUCKET}/{domain}/{run_id}/page_screenshots.json
    gs://{ARTIFACTS_BUCKET}/{domain}/{run_id}/collected_items.json
    gs://{ARTIFACTS_BUCKET}/{domain}/{run_id}/universal_sections.json
    gs://{ARTIFACTS_BUCKET}/{domain}/{run_id}/screenshots/{page_id}.png
"""

from __future__ import annotations

import argparse
import asyncio
import datetime
import sys
from pathlib import Path

project_root = str(Path(__file__).resolve().parents[1])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from pipeline.phase1_puller import pull_page, detect_universal_sections, compute_page_id
from pipeline.storage import write_json_artifact, write_screenshot, screenshot_uri, read_json_artifact
from pipeline.schema_validator import validate, SchemaValidationError


async def main(
    domain: str,
    run_id: str,
    language: str,
    viewport_kind: str,
    state: str,
    user_tier: str | None,
) -> None:
    print(f"[Phase 1] Starting data collection domain={domain} run_id={run_id} lang={language}")

    # Load url_inventory from GCS (Phase 0 output)
    try:
        url_inventory = read_json_artifact(domain, run_id, "url_inventory.json")
    except Exception as e:
        print(f"[Phase 1] STOP: Cannot read url_inventory — {e}", file=sys.stderr)
        sys.exit(1)

    if not url_inventory:
        print("[Phase 1] STOP: url_inventory is empty", file=sys.stderr)
        sys.exit(1)

    print(f"[Phase 1] Processing {len(url_inventory)} URLs")

    from playwright.async_api import async_playwright

    all_page_screenshots: list[dict] = []
    all_collected_items: list[dict] = []
    all_items_by_url: dict[str, list[dict]] = {}
    representative_page_ids: dict[str, str] = {}

    # Set viewport dimensions
    viewport_dims = {
        "desktop": {"width": 1280, "height": 800},
        "mobile": {"width": 390, "height": 844},
        "responsive": {"width": 1024, "height": 768},
    }.get(viewport_kind, {"width": 1280, "height": 800})

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(
            viewport=viewport_dims,
            user_agent="polyglot-watchdog/1.0",
        )

        for url in url_inventory:  # url_inventory is already sorted (Phase 0)
            print(f"[Phase 1] Pulling {url}")
            try:
                page = await context.new_page()
                page_screenshot, items, screenshot_bytes = await pull_page(
                    page=page,
                    url=url,
                    domain=domain,
                    viewport_kind=viewport_kind,
                    state=state,
                    user_tier=user_tier,
                    language=language,
                )
                await page.close()
            except Exception as exc:
                print(f"[Phase 1] WARNING: Failed to pull {url}: {exc}")
                continue

            # Upload screenshot — Contract §3.1 (one per capture context)
            page_id = page_screenshot["page_id"]
            storage_uri = write_screenshot(domain, run_id, page_id, screenshot_bytes)
            page_screenshot["storage_uri"] = storage_uri

            all_page_screenshots.append(page_screenshot)
            all_collected_items.extend(items)
            all_items_by_url[url] = items
            representative_page_ids[url] = page_id

        await browser.close()

    # Sort for determinism — Contract §1
    all_page_screenshots.sort(key=lambda r: (r["url"], r["viewport_kind"], r["state"], r["user_tier"] or ""))
    all_collected_items.sort(key=lambda i: (i["item_id"],))

    # Detect universal sections (EN only) — Contract §5
    created_at = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    universal_sections: list[dict] = []
    if language == "en":
        universal_sections = detect_universal_sections(
            all_items_by_url, representative_page_ids, created_at
        )

    # Schema validation gate — SPEC_LOCK §3 / Contract §8
    try:
        validate("page_screenshots", all_page_screenshots)
        print("[Phase 1] page_screenshots schema validation: PASSED")
    except SchemaValidationError as e:
        print(f"[Phase 1] STOP: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        validate("collected_items", all_collected_items)
        print("[Phase 1] collected_items schema validation: PASSED")
    except SchemaValidationError as e:
        print(f"[Phase 1] STOP: {e}", file=sys.stderr)
        sys.exit(1)

    if language == "en" and universal_sections:
        try:
            validate("universal_sections", universal_sections)
            print("[Phase 1] universal_sections schema validation: PASSED")
        except SchemaValidationError as e:
            print(f"[Phase 1] STOP: {e}", file=sys.stderr)
            sys.exit(1)

    # Write artifacts to GCS
    uri = write_json_artifact(domain, run_id, "page_screenshots.json", all_page_screenshots)
    print(f"[Phase 1] Wrote page_screenshots -> {uri}")

    uri = write_json_artifact(domain, run_id, "collected_items.json", all_collected_items)
    print(f"[Phase 1] Wrote collected_items -> {uri}")

    if language == "en":
        uri = write_json_artifact(domain, run_id, "universal_sections.json", universal_sections)
        print(f"[Phase 1] Wrote universal_sections -> {uri}")

    print(f"[Phase 1] Complete. {len(all_page_screenshots)} pages, {len(all_collected_items)} items.")


def run(
    domain: str,
    run_id: str,
    language: str = "en",
    viewport_kind: str = "desktop",
    state: str = "guest",
    user_tier: str | None = None,
):
    return asyncio.run(main(domain, run_id, language, viewport_kind, state, user_tier))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 1 — Data Collection")
    parser.add_argument("--domain", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--language", default="en")
    parser.add_argument("--viewport", default="desktop", choices=["desktop", "mobile", "responsive"])
    parser.add_argument("--state", default="guest", choices=["guest", "user"])
    parser.add_argument("--user-tier", default=None)
    args = parser.parse_args()
    run(args.domain, args.run_id, args.language, args.viewport, args.state, args.user_tier)
