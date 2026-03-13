"""Phase 6 runner — Localization QA issues generation.

Contract semantics:
- `issue.category` is the stable persisted external contract field.
- `issue.evidence.review_class` is richer internal review metadata from
  `phase6_review` that explains why an issue was emitted.

Inputs:
- EN run artifacts: eligible_dataset.json, collected_items.json, page_screenshots.json
- Target run artifacts: eligible_dataset.json, collected_items.json, page_screenshots.json

Output:
- issues.json (schema: contract/schemas/issues.schema.json)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

project_root = str(Path(__file__).resolve().parents[1])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from pipeline.phase6_providers import build_provider
from pipeline.phase6_review import ReviewContext, overlay_blocked_issue, review_pair
from pipeline.interactive_capture import CaptureContext, build_capture_context_id
from pipeline.schema_validator import SchemaValidationError, validate
from pipeline.storage import BUCKET_NAME, read_json_artifact, write_json_artifact, write_phase_manifest

_IMAGE_TAGS = {"img", "image"}


def _is_image_item(item: dict) -> bool:
    tag = str(item.get("tag", "")).strip().lower()
    element_type = str(item.get("element_type", "")).strip().lower()
    return tag in _IMAGE_TAGS or element_type in _IMAGE_TAGS


def _load_phase4_ocr_by_item(domain: str, run_id: str) -> dict[str, dict]:
    # Optional additive handoff: Phase 6 consumes Phase 4 OCR rows when present,
    # but must remain safe and fully functional when phase4_ocr.json is absent.
    try:
        rows = read_json_artifact(domain, run_id, "phase4_ocr.json")
    except FileNotFoundError:
        return {}
    except Exception as exc:
        # Missing optional artifacts can surface as provider-specific "NotFound"
        # errors depending on storage backend wiring; treat only those as absent.
        if exc.__class__.__name__ == "NotFound":
            return {}
        raise

    validate("phase4_ocr", rows)

    out: dict[str, dict] = {}
    for row in rows:
        item_id = str(row.get("item_id", ""))
        if not item_id:
            continue
        out[item_id] = row
    return out


def _index_collected(items: list[dict]) -> dict[str, dict]:
    return {i["item_id"]: i for i in items}


def _index_screenshots(rows: list[dict]) -> dict[str, dict]:
    return {r["page_id"]: r for r in rows}


def _build_evidence(target_item: dict, target_collected_by_item: dict[str, dict], target_screens_by_page: dict[str, dict]) -> dict:
    collected = target_collected_by_item.get(target_item["item_id"], {})
    page_id = collected.get("page_id")
    screenshot = target_screens_by_page.get(page_id, {}) if page_id else {}
    return {
        "url": target_item["url"],
        "bbox": collected.get("bbox", {"x": 0, "y": 0, "width": 0, "height": 0}),
        "storage_uri": screenshot.get("storage_uri", ""),
        "page_id": page_id,
        "item_id": target_item["item_id"],
    }


def _build_missing_target_evidence(en_item: dict, en_collected_by_item: dict[str, dict], en_screens_by_page: dict[str, dict]) -> dict:
    item_id = en_item.get("item_id", "")
    collected = en_collected_by_item.get(item_id, {})
    page_id = collected.get("page_id") or en_item.get("page_id", "")
    return {
        "url": en_item.get("url", ""),
        "bbox": collected.get("bbox", {"x": 0, "y": 0, "width": 0, "height": 0}),
        "storage_uri": en_screens_by_page.get(page_id, {}).get("storage_uri", ""),
        "item_id": item_id,
        "page_id": page_id,
    }


def _load_blocked_overlay_pages(domain: str, language: str, target_screens: list[dict]) -> list[dict]:
    from google.cloud import storage  # type: ignore
    from pipeline.storage import BUCKET_NAME

    review_bucket = os.environ.get("REVIEW_BUCKET", BUCKET_NAME)
    client = storage.Client()
    bucket = client.bucket(review_bucket)

    blocked_pages: list[dict] = []
    for page in sorted(target_screens, key=lambda row: row["page_id"]):
        capture_context_id = build_capture_context_id(
            CaptureContext(
                domain=domain,
                url=page["url"],
                language=language,
                viewport_kind=page["viewport_kind"],
                state=page["state"],
                user_tier=page.get("user_tier"),
            )
        )
        key = f"{domain}/capture_status/{capture_context_id}__{language}.json"
        blob = bucket.blob(key)
        if not blob.exists(client=client):
            continue
        review = json.loads(blob.download_as_text(encoding="utf-8"))
        if review.get("status") != "blocked_by_overlay":
            continue
        blocked_pages.append({
            "capture_context_id": capture_context_id,
            "url": page.get("url", ""),
            "storage_uri": page.get("storage_uri", ""),
        })
    blocked_pages.sort(key=lambda row: row["capture_context_id"])
    return blocked_pages


def run(domain: str, en_run_id: str, target_run_id: str) -> list[dict]:
    en_eligible = read_json_artifact(domain, en_run_id, "eligible_dataset.json")
    target_eligible = read_json_artifact(domain, target_run_id, "eligible_dataset.json")

    en_collected = read_json_artifact(domain, en_run_id, "collected_items.json")
    target_collected = read_json_artifact(domain, target_run_id, "collected_items.json")

    en_screens = read_json_artifact(domain, en_run_id, "page_screenshots.json")
    target_screens = read_json_artifact(domain, target_run_id, "page_screenshots.json")

    en_by_item = {i["item_id"]: i for i in en_eligible if i.get("language") == "en"}
    target_by_item = {i["item_id"]: dict(i) for i in target_eligible if i.get("language") != "en"}
    ocr_by_item = _load_phase4_ocr_by_item(domain, target_run_id)
    for item_id, item in target_by_item.items():
        ocr_row = ocr_by_item.get(item_id, {})
        # OCR text applies only to approved image-backed items and is supporting
        # evidence for EN↔target review, not a standalone issue generator.
        if not _is_image_item(item):
            continue
        if ocr_row.get("status") == "ok":
            item["ocr_text"] = str(ocr_row.get("ocr_text", "")).strip()
            item["ocr_engine"] = f"{ocr_row.get('ocr_provider', '')}:{ocr_row.get('ocr_engine', '')}".strip(":")
            notes = ocr_row.get("ocr_notes", [])
            if isinstance(notes, list):
                item["ocr_notes"] = [str(note).strip() for note in notes if str(note).strip()]
    en_collected_by_item = _index_collected(en_collected)
    en_screens_by_page = _index_screenshots(en_screens)
    target_collected_by_item = _index_collected(target_collected)
    target_screens_by_page = _index_screenshots(target_screens)
    target_language = next((str(item.get("language", "")).strip() for item in target_eligible if str(item.get("language", "")).strip() and str(item.get("language", "")).lower() != "en"), "")
    blocked_pages = _load_blocked_overlay_pages(domain, target_language, target_screens) if target_language else []
    provider = build_provider(mode=os.environ.get("PHASE6_REVIEW_PROVIDER", "offline"))

    issues: list[dict] = []

    for item_id in sorted(en_by_item.keys()):
        en_item = en_by_item[item_id]
        t_item = target_by_item.get(item_id)
        evidence_base = _build_evidence(t_item, target_collected_by_item, target_screens_by_page) if t_item else _build_missing_target_evidence(en_item, en_collected_by_item, en_screens_by_page)
        issues.extend(
            review_pair(
                ReviewContext(
                    en_item=en_item,
                    target_item=t_item,
                    evidence_base=evidence_base,
                    language=target_language,
                ),
                provider=provider,
            )
        )

    for blocked in blocked_pages:
        issues.append(overlay_blocked_issue(blocked["capture_context_id"], blocked))

    issues.sort(key=lambda i: (i["category"], i["id"]))

    try:
        validate("issues", issues)
    except SchemaValidationError as e:
        print(f"STOP: {e}", file=sys.stderr)
        sys.exit(1)

    write_json_artifact(domain, target_run_id, "issues.json", issues)
    manifest = {
        "schema_version": "v1.0",
        "phase": "phase6",
        "run_id": target_run_id,
        "domain": domain,
        "artifact_uris": [f"gs://{BUCKET_NAME}/{domain}/{target_run_id}/issues.json"],
        "summary_counters": {"issues": len(issues)},
        "error_records": [],
        "provenance": {"en_run_id": en_run_id, "target_run_id": target_run_id},
    }
    write_phase_manifest(domain, target_run_id, "phase6", manifest)
    return issues


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 6 — Localization QA")
    parser.add_argument("--domain", required=True)
    parser.add_argument("--en-run-id", required=True)
    parser.add_argument("--target-run-id", required=True)
    args = parser.parse_args()
    run(args.domain, args.en_run_id, args.target_run_id)
