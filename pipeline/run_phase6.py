"""Phase 6 runner — Localization QA issues generation.

Inputs:
- EN run artifacts: eligible_dataset.json, collected_items.json, page_screenshots.json
- Target run artifacts: eligible_dataset.json, collected_items.json, page_screenshots.json

Output:
- issues.json (schema: contract/schemas/issues.schema.json)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

project_root = str(Path(__file__).resolve().parents[1])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from pipeline.phase5_normalizer import normalize_text
from pipeline.interactive_capture import CaptureContext, build_capture_context_id
from pipeline.schema_validator import SchemaValidationError, validate
from pipeline.storage import BUCKET_NAME, read_json_artifact, write_json_artifact, write_phase_manifest

_PLACEHOLDER_RE = re.compile(r"(%[^%]+%|\[[^\]]+\]|<[^>]+>)")
_DYNAMIC_NUMBER_RE = re.compile(r"\d+")
_HEADER_ONLINE_CLASS_TOKENS = {"header_online", "bc_flex", "bc_flex_items_center"}




def _item_classes(item: dict) -> set[str]:
    attributes = item.get("attributes") if isinstance(item, dict) else None
    if not isinstance(attributes, dict):
        return set()
    class_value = str(attributes.get("class", "")).strip()
    if not class_value:
        return set()
    return {token for token in class_value.split() if token}


def _is_header_online_dynamic_counter(en_item: dict, target_item: dict) -> bool:
    classes = _item_classes(en_item) | _item_classes(target_item)
    return _HEADER_ONLINE_CLASS_TOKENS.issubset(classes)


def _normalize_dynamic_counter_text(item: dict, text: str) -> str:
    if _is_header_online_dynamic_counter(item, item):
        return _DYNAMIC_NUMBER_RE.sub("<NUM>", text)
    return text

def _issue_id(category: str, en_item_id: str, target_url: str, message: str) -> str:
    raw = f"{category}|{en_item_id}|{target_url}|{message}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


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
    target_by_item = {i["item_id"]: i for i in target_eligible if i.get("language") != "en"}
    en_collected_by_item = _index_collected(en_collected)
    en_screens_by_page = _index_screenshots(en_screens)
    target_collected_by_item = _index_collected(target_collected)
    target_screens_by_page = _index_screenshots(target_screens)
    target_language = next((str(item.get("language", "")).strip() for item in target_eligible if str(item.get("language", "")).strip() and str(item.get("language", "")).lower() != "en"), "")
    blocked_pages = _load_blocked_overlay_pages(domain, target_language, target_screens) if target_language else []

    issues: list[dict] = []

    for item_id in sorted(en_by_item.keys()):
        en_item = en_by_item[item_id]
        t_item = target_by_item.get(item_id)

        en_text = _normalize_dynamic_counter_text(en_item, normalize_text(en_item.get("text", "")))

        if not t_item:
            evidence = {
                "url": en_item.get("url", ""),
                "bbox": en_collected_by_item.get(item_id, {}).get("bbox", {"x": 0, "y": 0, "width": 0, "height": 0}),
                "storage_uri": en_screens_by_page.get(en_item.get("page_id"), {}).get("storage_uri", ""),
                "item_id": item_id,
            }
            msg = "Missing target element for EN reference item"
            issues.append({
                "id": _issue_id("MISSING_TRANSLATION", item_id, en_item.get("url", ""), msg),
                "category": "MISSING_TRANSLATION",
                "confidence": 0.95,
                "message": msg,
                "evidence": evidence,
            })
            continue

        t_text = _normalize_dynamic_counter_text(t_item, normalize_text(t_item.get("text", "")))
        evidence = _build_evidence(t_item, target_collected_by_item, target_screens_by_page)

        en_placeholders = sorted(_PLACEHOLDER_RE.findall(en_text))
        t_placeholders = sorted(_PLACEHOLDER_RE.findall(t_text))
        if en_placeholders != t_placeholders:
            msg = "Placeholder tokens differ between EN and target text"
            issues.append({
                "id": _issue_id("FORMATTING_MISMATCH", item_id, t_item["url"], msg),
                "category": "FORMATTING_MISMATCH",
                "confidence": 0.9,
                "message": msg,
                "evidence": evidence,
            })

        is_dynamic_counter = _is_header_online_dynamic_counter(en_item, t_item)
        if en_text and t_text and en_text == t_text and not en_placeholders and not is_dynamic_counter:
            msg = "Target text appears untranslated (identical to EN)"
            issues.append({
                "id": _issue_id("TRANSLATION_MISMATCH", item_id, t_item["url"], msg),
                "category": "TRANSLATION_MISMATCH",
                "confidence": 0.7,
                "message": msg,
                "evidence": evidence,
            })

    for blocked in blocked_pages:
        msg = "Capture blocked by overlay"
        issues.append({
            "id": _issue_id("OVERLAY_BLOCKED_CAPTURE", blocked["capture_context_id"], blocked["url"], msg),
            "category": "OVERLAY_BLOCKED_CAPTURE",
            "confidence": 1.0,
            "message": msg,
            "evidence": {
                "url": blocked["url"],
                "bbox": {"x": 0, "y": 0, "width": 0, "height": 0},
                "storage_uri": blocked["storage_uri"],
            },
        })

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
