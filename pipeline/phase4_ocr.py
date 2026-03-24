from __future__ import annotations

import argparse
import io
import hashlib
from pathlib import Path
import re
import sys
from urllib.parse import unquote

from PIL import Image

project_root = str(Path(__file__).resolve().parents[1])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from pipeline.phase4_ocr_provider import extract_text_with_ocrspace_fallback
from pipeline.storage import BUCKET_NAME, read_json_artifact, write_json_artifact, write_phase_manifest

_IMAGE_TAGS = {"img", "image"}


def _is_image_item(item: dict) -> bool:
    tag = str(item.get("tag", "")).strip().lower()
    element_type = str(item.get("element_type", "")).strip().lower()
    return tag in _IMAGE_TAGS or element_type in _IMAGE_TAGS


def _clamp_bbox(bbox: dict, width: int, height: int) -> tuple[int, int, int, int] | None:
    x = max(0, int(float(bbox.get("x", 0))))
    y = max(0, int(float(bbox.get("y", 0))))
    w = max(1, int(float(bbox.get("width", 0))))
    h = max(1, int(float(bbox.get("height", 0))))
    right = min(width, x + w)
    bottom = min(height, y + h)
    if right <= x or bottom <= y:
        return None
    return (x, y, right, bottom)


def _crop_image_bytes(png_bytes: bytes, bbox: dict) -> bytes:
    with Image.open(io.BytesIO(png_bytes)) as img:
        rgb = img.convert("RGB")
        crop_box = _clamp_bbox(bbox, rgb.width, rgb.height)
        if not crop_box:
            return b""
        cropped = rgb.crop(crop_box)
        out = io.BytesIO()
        cropped.save(out, format="PNG")
        return out.getvalue()


def _extract_svg_text(item: dict) -> tuple[bool, str]:
    tag = str(item.get("tag", "")).strip().lower()
    attrs = item.get("attributes") if isinstance(item.get("attributes"), dict) else {}
    src = str(attrs.get("src", "")).strip()
    raw_svg = ""
    if tag == "svg":
        raw_svg = str(item.get("text", "")).strip()
    elif src.lower().startswith("data:image/svg+xml,"):
        raw_svg = unquote(src.split(",", 1)[1])
    elif src.lower().startswith("data:image/svg+xml;base64,"):
        try:
            import base64

            raw_svg = base64.b64decode(src.split(",", 1)[1]).decode("utf-8", errors="ignore")
        except Exception:
            raw_svg = ""
    if not raw_svg:
        return False, ""
    text_nodes = re.findall(r">([^<>]+)<", raw_svg)
    normalized = " ".join(" ".join(node.split()) for node in text_nodes).strip()
    return True, normalized


def _download_gs_uri(gs_uri: str) -> bytes:
    from google.cloud import storage  # type: ignore

    if not gs_uri.startswith("gs://"):
        raise ValueError("Expected gs:// URI")
    path = gs_uri[len("gs://"):]
    bucket_name, _, blob_path = path.partition("/")
    client = storage.Client()
    blob = client.bucket(bucket_name).blob(blob_path)
    return blob.download_as_bytes()


def build_phase4_ocr_rows(
    eligible_dataset: list[dict],
    collected_items: list[dict],
    page_screenshots: list[dict],
    *,
    image_fetcher=_download_gs_uri,
    ocr_fn=extract_text_with_ocrspace_fallback,
) -> list[dict]:
    collected_by_item = {row.get("item_id"): row for row in collected_items}
    screenshot_by_page = {row.get("page_id"): row for row in page_screenshots}

    rows: list[dict] = []
    for eligible in sorted(eligible_dataset, key=lambda r: (r.get("item_id", ""), r.get("url", ""))):
        item_id = eligible.get("item_id")
        collected = collected_by_item.get(item_id, {})
        if not _is_image_item(collected):
            continue

        page_id = collected.get("page_id") or eligible.get("page_id")
        screenshot = screenshot_by_page.get(page_id, {}) if page_id else {}
        source_image_uri = screenshot.get("storage_uri", "")

        row = {
            "item_id": item_id,
            "page_id": page_id,
            "url": eligible.get("url", ""),
            "language": eligible.get("language", ""),
            "viewport_kind": collected.get("viewport_kind", eligible.get("viewport_kind", "")),
            "state": collected.get("state", eligible.get("state", "")),
            "user_tier": collected.get("user_tier", eligible.get("user_tier")),
            "source_image_uri": source_image_uri,
            "ocr_text": "",
            "ocr_provider": "ocr.space",
            "ocr_engine": "3",
            "ocr_notes": [],
            "provider_meta": {},
            "status": "failed",
            "asset_hash": "",
            "src": "",
            "alt": "",
            "is_svg": False,
            "svg_text": "",
            "image_text_review_status": "image_text_not_reviewed",
        }
        attrs = collected.get("attributes") if isinstance(collected.get("attributes"), dict) else {}
        src = str(attrs.get("src", "")).strip()
        alt = str(attrs.get("alt", "")).strip()
        is_svg, svg_text = _extract_svg_text(collected)
        row["src"] = src
        row["alt"] = alt
        row["is_svg"] = is_svg
        row["svg_text"] = svg_text
        if src:
            row["asset_hash"] = hashlib.sha1(src.encode("utf-8")).hexdigest()
        elif svg_text:
            row["asset_hash"] = hashlib.sha1(svg_text.encode("utf-8")).hexdigest()

        if is_svg and svg_text:
            row["status"] = "ok"
            row["ocr_text"] = svg_text
            row["ocr_provider"] = "svg_dom"
            row["ocr_engine"] = "svg_text"
            row["ocr_notes"] = ["svg_text_extracted"]
            row["image_text_review_status"] = "image_text_reviewed"
            rows.append(row)
            continue

        if not source_image_uri:
            row["status"] = "failed"
            row["ocr_notes"] = ["missing_source_image"]
            row["image_text_review_status"] = "image_text_review_blocked"
            rows.append(row)
            continue

        try:
            page_png = image_fetcher(source_image_uri)
            crop_png = _crop_image_bytes(page_png, collected.get("bbox", {}))
            if not crop_png:
                row["status"] = "failed"
                row["ocr_notes"] = ["invalid_bbox"]
                row["image_text_review_status"] = "image_text_review_blocked"
                rows.append(row)
                continue
            ocr_result = ocr_fn(crop_png)
        except Exception as exc:
            row["status"] = "failed"
            row["ocr_notes"] = ["prepare_or_fetch_failed"]
            row["provider_meta"] = {"error": str(exc)}
            row["image_text_review_status"] = "image_text_review_blocked"
            rows.append(row)
            continue

        row.update(ocr_result)
        row["image_text_review_status"] = "image_text_reviewed" if row.get("status") == "ok" else "image_text_not_reviewed"
        rows.append(row)

    rows.sort(key=lambda r: (r.get("item_id", ""), r.get("url", "")))
    return rows


def run(domain: str, run_id: str) -> list[dict]:
    eligible_dataset = read_json_artifact(domain, run_id, "eligible_dataset.json")
    collected_items = read_json_artifact(domain, run_id, "collected_items.json")
    page_screenshots = read_json_artifact(domain, run_id, "page_screenshots.json")

    rows = build_phase4_ocr_rows(eligible_dataset, collected_items, page_screenshots)
    write_json_artifact(domain, run_id, "phase4_ocr.json", rows)
    manifest = {
        "schema_version": "v1.0",
        "phase": "phase4",
        "run_id": run_id,
        "domain": domain,
        "artifact_uris": [f"gs://{BUCKET_NAME}/{domain}/{run_id}/phase4_ocr.json"],
        "summary_counters": {
            "ocr_rows": len(rows),
            "ok": len([r for r in rows if r.get("status") == "ok"]),
            "failed": len([r for r in rows if r.get("status") == "failed"]),
            "skipped": len([r for r in rows if r.get("status") == "skipped"]),
            "image_text_reviewed": len([r for r in rows if r.get("image_text_review_status") == "image_text_reviewed"]),
            "image_text_not_reviewed": len([r for r in rows if r.get("image_text_review_status") == "image_text_not_reviewed"]),
            "image_text_review_blocked": len([r for r in rows if r.get("image_text_review_status") == "image_text_review_blocked"]),
        },
        "error_records": [],
        "provenance": {"primary_provider": "ocr.space", "fallback_provider": "google_vision"},
    }
    write_phase_manifest(domain, run_id, "phase4", manifest)
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 4 — OCR for approved image-backed items")
    parser.add_argument("--domain", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    run(args.domain, args.run_id)
