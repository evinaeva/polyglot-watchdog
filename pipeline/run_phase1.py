"""Phase 1 runner — Data Collection.

Usage:
    python pipeline/run_phase1.py --domain example.com --run-id <run_id> --language en

Reads seed_urls from GCS manual namespace (primary planning input for v1.0).
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
import json
import os
import sys
from pathlib import Path

project_root = str(Path(__file__).resolve().parents[1])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from pipeline.phase1_puller import pull_page, detect_universal_sections
from pipeline.interactive_capture import CaptureContext, GCSArtifactWriter, RunContext, capture_state
from pipeline.runtime_config import Phase1RuntimeConfig, load_phase1_runtime_config, validate_seed_urls_payload
from pipeline.storage import BUCKET_NAME, write_json_artifact, read_json_artifact
from pipeline.schema_validator import validate, SchemaValidationError


def load_planning_urls(domain: str, run_id: str) -> list[str]:
    """Load planning URLs with seed_urls as primary input for v1.0."""
    try:
        seed_payload = read_json_artifact(domain, "manual", "seed_urls.json")
        validate_seed_urls_payload({"domain": seed_payload.get("domain", domain), "urls": seed_payload.get("urls", [])})
        rows = seed_payload.get("urls", [])
        urls = sorted({str(row["url"]) for row in rows if isinstance(row, dict) and isinstance(row.get("url"), str)})
        if urls:
            print(f"[Phase 1] Planning input: seed_urls ({len(urls)} URLs)")
            return urls
    except Exception as exc:
        print(f"[Phase 1] seed_urls unavailable or invalid: {exc}")

    # TEMP_COMPAT: allow url_inventory fallback only while migrating callers to seed_urls.
    # Removal condition: delete fallback in PW-BL-017 once seed_urls is required everywhere.
    url_inventory = read_json_artifact(domain, run_id, "url_inventory.json")
    if isinstance(url_inventory, list) and url_inventory:
        print(f"[Phase 1] TEMP_COMPAT planning input: url_inventory ({len(url_inventory)} URLs)")
        return sorted({str(url) for url in url_inventory})
    raise RuntimeError("No planning input available: seed_urls required (url_inventory TEMP_COMPAT also missing)")


class _GCSConfigStore:
    """Minimal storage adapter for the canonical artifact writer path."""

    def _client(self):
        from google.cloud import storage  # type: ignore

        return storage.Client()

    def write_json(self, bucket: str, key: str, value: object) -> str:
        client = self._client()
        blob = client.bucket(bucket).blob(key)
        content = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        blob.upload_from_string(content, content_type="application/json; charset=utf-8")
        return f"gs://{bucket}/{key}"

    def write_bytes(self, bucket: str, key: str, value: bytes, content_type: str) -> str:
        client = self._client()
        blob = client.bucket(bucket).blob(key)
        blob.upload_from_string(value, content_type=content_type)
        return f"gs://{bucket}/{key}"

    def read_json(self, bucket: str, key: str) -> object:
        client = self._client()
        blob = client.bucket(bucket).blob(key)
        return json.loads(blob.download_as_text(encoding="utf-8"))


async def main(
    domain: str,
    run_id: str,
    language: str,
    viewport_kind: str,
    state: str,
    user_tier: str | None,
    jobs_override: list[CaptureJob] | None = None,
) -> None:
    print(f"[Phase 1] Starting data collection domain={domain} run_id={run_id} lang={language}")

    # Load planning URLs (seed_urls primary input for v1.0).
    try:
        planning_urls = load_planning_urls(domain, run_id)
    except Exception as e:
        print(f"[Phase 1] STOP: Cannot load planning URLs — {e}", file=sys.stderr)
        sys.exit(1)

    if not planning_urls:
        print("[Phase 1] STOP: planning URL list is empty", file=sys.stderr)
        sys.exit(1)

    print(f"[Phase 1] Processing {len(planning_urls)} URLs")

    from playwright.async_api import async_playwright

    all_page_screenshots: list[dict] = []
    all_collected_items: list[dict] = []
    all_items_by_url: dict[str, list[dict]] = {}
    representative_page_ids: dict[str, str] = {}
    run_context = RunContext(run_id=run_id, run_started_at=datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"))
    review_bucket = os.environ.get("REVIEW_BUCKET", BUCKET_NAME)
    artifact_writer = GCSArtifactWriter(_GCSConfigStore(), BUCKET_NAME, review_bucket)

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

        for url in planning_urls:
            print(f"[Phase 1] Pulling {url}")
            try:
                page = await context.new_page()
                page_screenshot, items, screenshot_bytes = await pull_page(
                    page=page,
                    url=url,
                    domain=domain,
                    viewport_kind=viewport_kind,
                    state=job.context.state,
                    user_tier=job.context.user_tier or None,
                    language=job.context.language,
                )
                await page.close()
            except Exception as exc:
                print(f"[Phase 1] WARNING: Failed to pull {url}: {exc}")
                continue

            capture_result = capture_state(
                context=CaptureContext(
                    domain=domain,
                    url=url,
                    language=language,
                    viewport_kind=viewport_kind,
                    state=state,
                    user_tier=user_tier,
                ),
                page_payload=(
                    {"viewport": page_screenshot["viewport"], "screenshot_bytes": screenshot_bytes},
                    [
                        {
                            "css_selector": item["css_selector"],
                            "bbox": item["bbox"],
                            "element_type": item["element_type"],
                            "text": item["text"],
                            "visible": item["visible"],
                            "tag": item.get("tag"),
                            "attributes": item.get("attributes"),
                        }
                        for item in items
                    ],
                ),
                writer=artifact_writer,
                run_context=run_context,
            )

            all_page_screenshots.append(capture_result["page"])
            all_collected_items.extend(capture_result["elements"])
            all_items_by_url[url] = capture_result["elements"]
            representative_page_ids[url] = capture_result["page"]["page_id"]

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
    config = load_phase1_runtime_config({
        "domain": domain,
        "run_id": run_id,
        "language": language,
        "viewport_kind": viewport_kind,
        "state": state,
        "user_tier": user_tier,
    })
    return run_with_config(config)


def run_with_config(config: Phase1RuntimeConfig):
    return asyncio.run(main(config.domain, config.run_id, config.language, config.viewport_kind, config.state, config.user_tier))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 1 — Data Collection")
    parser.add_argument("--domain", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--language", default="en")
    parser.add_argument("--viewport", default="desktop", choices=["desktop", "mobile", "responsive"])
    parser.add_argument("--state", default="guest")
    parser.add_argument("--user-tier", default=None)
    args = parser.parse_args()
    config = load_phase1_runtime_config(vars(args))
    run_with_config(config)
