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

from app.recipes import load_recipes_for_planner
from pipeline.phase1_puller import capture_current_page, execute_recipe_step, pull_page, detect_universal_sections
from pipeline.interactive_capture import CaptureContext, CapturePoint, CaptureJob, DeterministicPlanner, GCSArtifactWriter, Recipe, RunContext, capture_state
from pipeline.runtime_config import Phase1RuntimeConfig, load_phase1_runtime_config, validate_seed_urls_payload
from pipeline.storage import BUCKET_NAME, write_json_artifact, read_json_artifact, write_phase_manifest
from pipeline.schema_validator import validate, SchemaValidationError


def load_planning_rows(domain: str, run_id: str) -> list[dict]:
    """Load planning rows with seed_urls as primary input for v1.0."""
    try:
        seed_payload = read_json_artifact(domain, "manual", "seed_urls.json")
        validate_seed_urls_payload(seed_payload)
        rows = [
            {"url": str(row.get("url")), "recipe_ids": sorted({str(rid) for rid in row.get("recipe_ids", []) if str(rid)})}
            for row in seed_payload.get("urls", [])
            if isinstance(row, dict) and isinstance(row.get("url"), str)
        ]
        rows.sort(key=lambda r: r["url"])
        if rows:
            print(f"[Phase 1] Planning input: seed_urls ({len(rows)} URLs)")
            return rows
    except Exception as exc:
        print(f"[Phase 1] seed_urls unavailable or invalid: {exc}")
    raise RuntimeError("No planning input available: valid seed_urls are required")


def load_planning_urls(domain: str, run_id: str) -> list[str]:
    return [row["url"] for row in load_planning_rows(domain, run_id)]


def build_planned_jobs(domain: str, planning_rows: list[dict], language: str, viewport_kind: str, user_tier: str | None, recipes: dict[str, Recipe]) -> list[CaptureJob]:
    planner = DeterministicPlanner()
    seed_payload = {"domain": domain, "urls": planning_rows}
    return planner.expand_jobs(
        seed_urls=seed_payload,
        recipes=recipes,
        languages=[language],
        viewports=[viewport_kind],
        user_tiers=[user_tier or ""],
    )


def build_exact_context_job(domain: str, url: str, language: str, viewport_kind: str, state: str, user_tier: str | None) -> CaptureJob:
    recipes = load_recipes_for_planner(domain)
    recipe_ids: list[str] = []
    if state != "baseline":
        matching_recipe_ids = sorted(
            recipe_id
            for recipe_id, recipe in recipes.items()
            if any(point.state == state for point in recipe.capture_points)
        )
        if not matching_recipe_ids:
            raise RuntimeError(f"No recipe defines capture point state={state!r} for exact-context rerun")
        recipe_ids = [matching_recipe_ids[0]]

    jobs = build_planned_jobs(
        domain=domain,
        planning_rows=[{"url": url, "recipe_ids": recipe_ids}],
        language=language,
        viewport_kind=viewport_kind,
        user_tier=user_tier,
        recipes=recipes,
    )
    matching = [
        job for job in jobs
        if job.context.url == url
        and job.context.viewport_kind == viewport_kind
        and job.context.state == state
        and (job.context.user_tier or None) == (user_tier or None)
        and job.context.language == language
        and (state == "baseline" or job.recipe_id == recipe_ids[0])
    ]
    if len(matching) != 1:
        raise RuntimeError(f"Exact-context rerun resolution failed: expected 1 job, got {len(matching)}")
    return matching[0]


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


def _capture_marker_state(step: RecipeStep) -> str | None:
    if step.action.strip().lower() != "capture_state":
        return None
    marker = (step.wait_for or step.selector or "").strip()
    return marker or None


async def _execute_recipe_until_state(page, recipe: Recipe, target_state: str) -> None:
    defined_states = [point.state for point in recipe.capture_points]
    if target_state not in defined_states:
        raise RuntimeError(f"Recipe {recipe.recipe_id} does not define capture state {target_state!r}")

    marker_states = [state for state in (_capture_marker_state(step) for step in recipe.steps) if state is not None]
    if marker_states:
        if marker_states != defined_states:
            raise RuntimeError(
                f"Recipe {recipe.recipe_id} capture_state markers must match capture_points order"
            )
        reached = False
        for step in recipe.steps:
            marker_state = _capture_marker_state(step)
            if marker_state is not None:
                if marker_state == target_state:
                    reached = True
                    break
                continue
            await execute_recipe_step(page, step.action, step.selector, step.wait_for)
        if not reached:
            raise RuntimeError(
                f"Recipe {recipe.recipe_id} did not reach capture marker for state={target_state!r}"
            )
        return

    if len(defined_states) != 1:
        raise RuntimeError(
            f"Recipe {recipe.recipe_id} has multiple capture_points and requires capture_state step markers"
        )
    if defined_states[0] != target_state:
        raise RuntimeError(f"Recipe {recipe.recipe_id} cannot produce state={target_state!r}")
    for step in recipe.steps:
        await execute_recipe_step(page, step.action, step.selector, step.wait_for)


def _is_non_fatal_not_found_error(exc: Exception) -> bool:
    message = str(exc).lower()
    not_found_markers = (
        "not found",
        "no node found",
        "failed to find element",
        "waiting for selector",
        "selector",
    )
    fatal_markers = (
        "net::",
        "navigation",
        "browser has been closed",
        "target page, context or browser has been closed",
        "protocol error",
        "timeout 30000ms exceeded while navigating",
    )
    if any(marker in message for marker in fatal_markers):
        return False
    return any(marker in message for marker in not_found_markers)


async def main(
    domain: str,
    run_id: str,
    language: str,
    viewport_kind: str,
    state: str,
    user_tier: str | None,
    jobs_override: list[CaptureJob] | None = None,
    rerun_provenance: dict | None = None,
) -> None:
    print(f"[Phase 1] Starting data collection domain={domain} run_id={run_id} lang={language}")

    if jobs_override is None:
        # Load planning URLs (seed_urls primary input for v1.0).
        try:
            planning_rows = load_planning_rows(domain, run_id)
        except Exception as e:
            print(f"[Phase 1] STOP: Cannot load planning URLs — {e}", file=sys.stderr)
            sys.exit(1)

        if not planning_rows:
            print("[Phase 1] STOP: planning URL list is empty", file=sys.stderr)
            sys.exit(1)

        recipes = load_recipes_for_planner(domain)
        jobs = build_planned_jobs(domain, planning_rows, language, viewport_kind, user_tier, recipes)
    else:
        jobs = list(jobs_override)
        recipes = load_recipes_for_planner(domain)
    print(f"[Phase 1] Processing {len(jobs)} capture jobs")

    from playwright.async_api import async_playwright

    all_page_screenshots: list[dict] = []
    all_collected_items: list[dict] = []
    all_items_by_url: dict[str, list[dict]] = {}
    representative_page_ids: dict[str, str] = {}
    error_records: list[dict] = []
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
        browser = await p.chromium.launch(args=["--no-sandbox"])
        context = await browser.new_context(
            viewport=viewport_dims,
            user_agent="polyglot-watchdog/1.0",
        )

        for job in jobs:
            url = job.context.url
            print(f"[Phase 1] Pulling {url} state={job.context.state}")
            try:
                page = await context.new_page()
                if job.mode == "baseline":
                    page_screenshot, items, screenshot_bytes = await pull_page(
                        page=page,
                        url=url,
                        domain=domain,
                        viewport_kind=viewport_kind,
                        state=job.context.state,
                        user_tier=job.context.user_tier or None,
                        language=job.context.language,
                    )
                else:
                    if not job.recipe_id or job.recipe_id not in recipes:
                        raise RuntimeError(f"Missing recipe for scripted capture: recipe_id={job.recipe_id!r}")
                    recipe = recipes[job.recipe_id]
                    await page.goto(url, timeout=30000)
                    await _execute_recipe_until_state(page, recipe, job.context.state)
                    page_screenshot, items, screenshot_bytes = await capture_current_page(
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
                if rerun_provenance is not None and _is_non_fatal_not_found_error(exc):
                    error_records.append({
                        "type": "NOT_FOUND",
                        "url": url,
                        "viewport_kind": job.context.viewport_kind,
                        "state": job.context.state,
                        "user_tier": job.context.user_tier,
                        "message": str(exc),
                        "non_fatal": True,
                    })
                    print(f"[Phase 1] WARN: exact-context capture NOT FOUND for {url}: {exc}")
                    continue
                print(f"[Phase 1] STOP: Failed to pull {url}: {exc}", file=sys.stderr)
                raise SystemExit(1) from exc

            capture_result = capture_state(
                context=CaptureContext(
                    domain=domain,
                    url=url,
                    language=job.context.language,
                    viewport_kind=job.context.viewport_kind,
                    state=job.context.state,
                    user_tier=job.context.user_tier or None,
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
                            "page_canonical_key": item.get("page_canonical_key"),
                            "logical_match_key": item.get("logical_match_key"),
                            "role_hint": item.get("role_hint"),
                            "semantic_attrs": item.get("semantic_attrs"),
                            "local_path_signature": item.get("local_path_signature"),
                            "container_signature": item.get("container_signature"),
                            "stable_ordinal": item.get("stable_ordinal"),
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
    created_at = run_context.run_started_at
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
    page_screenshots_uri = write_json_artifact(domain, run_id, "page_screenshots.json", all_page_screenshots)
    print(f"[Phase 1] Wrote page_screenshots -> {page_screenshots_uri}")

    collected_items_uri = write_json_artifact(domain, run_id, "collected_items.json", all_collected_items)
    print(f"[Phase 1] Wrote collected_items -> {collected_items_uri}")

    universal_uri = None
    if language == "en":
        universal_uri = write_json_artifact(domain, run_id, "universal_sections.json", universal_sections)
        print(f"[Phase 1] Wrote universal_sections -> {universal_uri}")

    manifest = {
        "schema_version": "v1.0",
        "phase": "phase1",
        "run_id": run_id,
        "domain": domain,
        "artifact_uris": sorted([u for u in [
            page_screenshots_uri,
            collected_items_uri,
            universal_uri,
        ] if u]),
        "summary_counters": {
            "pages": len(all_page_screenshots),
            "items": len(all_collected_items),
            "universal_sections": len(universal_sections),
        },
        "provenance": {
            "language": language,
            "viewport_kind": viewport_kind,
            "state": state,
            "user_tier": user_tier,
            "run_started_at": run_context.run_started_at,
            "rerun": rerun_provenance or {},
        },
        "error_records": sorted(error_records, key=lambda r: (r.get("url", ""), r.get("state", ""))),
    }
    manifest_uri = write_phase_manifest(domain, run_id, "phase1", manifest)
    print(f"[Phase 1] Wrote manifest -> {manifest_uri}")

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


def run_exact_context(domain: str, run_id: str, url: str, viewport_kind: str, state: str, user_tier: str | None, language: str, original_context_id: str | None = None):
    job = build_exact_context_job(domain, url, language, viewport_kind, state, user_tier)
    provenance = {
        "url": url,
        "viewport_kind": viewport_kind,
        "state": state,
        "user_tier": user_tier,
        "original_capture_context_id": original_context_id,
        "recipe_id": job.recipe_id,
    }
    return asyncio.run(main(domain, run_id, language, viewport_kind, state, user_tier, jobs_override=[job], rerun_provenance=provenance))


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
