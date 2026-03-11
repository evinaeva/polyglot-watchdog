"""Interactive capture — Playwright-driven element extraction and artifact production.

Contract: contract/watchdog_contract_v1.0.md §3, §6 Phase 1
Architecture: docs/Interactive Capture Architecture.md

Key determinism rules:
- Stable element ordering via _canonical_element_sort_key.
- Stable item_id via compute_item_id (text excluded — Contract §3.4).
- No per-element screenshots — only one full-page screenshot per capture context.
- Deterministic page_id via compute_page_id.
- Explicit fail-fast if determinism cannot be guaranteed.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import asyncio
from dataclasses import dataclass, field
from typing import Any, Protocol

# ---------------------------------------------------------------------------
# Contract: capture_context identity fields — §3.1
# language is EXCLUDED from identity per contract.
# ---------------------------------------------------------------------------
CONTRACT_CAPTURE_CONTEXT_FIELDS = ("url", "viewport_kind", "state", "user_tier")


@dataclass(frozen=True)
class CaptureContext:
    domain: str
    url: str
    language: str
    viewport_kind: str
    state: str
    user_tier: str | None


@dataclass(frozen=True)
class CapturePoint:
    state: str


@dataclass(frozen=True)
class RecipeStep:
    action: str
    selector: str | None = None
    wait_for: str | None = None


@dataclass(frozen=True)
class Recipe:
    id: str
    url_pattern: str
    states: list[CapturePoint]
    steps: list[RecipeStep] = field(default_factory=list)
    capture_markers: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CaptureJob:
    context: CaptureContext
    recipe_id: str | None = None


@dataclass(frozen=True)
class RunContext:
    run_id: str
    run_started_at: str


# ---------------------------------------------------------------------------
# Contract-aligned stable ID functions
# ---------------------------------------------------------------------------

VALID_STATES = {"guest", "user", "baseline"}


def validate_state_name(state: str) -> None:
    # Allow well-known states and recipe-generated scripted states
    if state in VALID_STATES:
        return
    if state and all(ch.isalnum() or ch == "_" for ch in state):
        return
    raise ValueError(f"Invalid state name: {state!r}")


def build_capture_context_id(context: CaptureContext) -> str:
    # Invariant: include domain + contract capture-context fields only.
    # Contract capture-context fields are exactly CONTRACT_CAPTURE_CONTEXT_FIELDS,
    # so language must stay excluded from this identity hash.
    payload = "|".join([
        context.domain,
        context.url,
        context.viewport_kind,
        context.state,
        context.user_tier or "",
    ])
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def compute_page_id(context: CaptureContext) -> str:
    # Invariant: page_id must be built from contract capture-context fields only
    # (url, viewport_kind, state, user_tier). language must stay excluded.
    payload = "|".join([context.url, context.viewport_kind, context.state, context.user_tier or ""])
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def compute_item_id(domain: str, url: str, css_selector: str | None, bbox: dict, element_type: str) -> str:
    # Contract §3.4 — text MUST NOT be part of item_id.
    canonical_bbox = _canonical_bbox_payload(bbox)
    payload = f"{domain}|{url}|{css_selector or ''}|{canonical_bbox}|{element_type}"
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def deterministic_url_hash(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


def assert_language_not_in_contract_identity(context: CaptureContext) -> None:
    """Enforce that language does not affect capture_context_id or page_id."""
    probe = CaptureContext(
        domain=context.domain,
        url=context.url,
        language="__probe_language__",
        viewport_kind=context.viewport_kind,
        state=context.state,
        user_tier=context.user_tier,
    )
    if build_capture_context_id(context) != build_capture_context_id(probe):
        raise DeterminismError("language leaked into capture_context_id")
    if compute_page_id(context) != compute_page_id(probe):
        raise DeterminismError("language leaked into page_id")


# ---------------------------------------------------------------------------
# Artifact writer protocol and GCS implementation
# ---------------------------------------------------------------------------


class ArtifactWriter(Protocol):
    data_bucket: str

    def write_capture(
        self,
        context: CaptureContext,
        page_artifact: dict[str, Any],
        elements: list[dict[str, Any]],
        screenshot_bytes: bytes,
    ) -> dict[str, str]:
        ...


class GCSArtifactWriter:
    """Writes capture artifacts to GCS following canonical storage paths."""

    def __init__(self, config_store: Any, data_bucket: str, review_bucket: str | None = None):
        self._config_store = config_store
        self.data_bucket = data_bucket
        self._review_bucket = review_bucket or data_bucket

    def write_capture(
        self,
        context: CaptureContext,
        page_artifact: dict[str, Any],
        elements: list[dict[str, Any]],
        screenshot_bytes: bytes,
    ) -> dict[str, str]:
        from pipeline.storage import _gcs_client

        client = _gcs_client()
        bucket = client.bucket(self.data_bucket)

        url_hash = deterministic_url_hash(context.url)
        suffix = f"{context.language}/{url_hash}/{context.state}/{context.viewport_kind}/{context.user_tier or 'null'}"
        screenshot_path = f"domain/{context.domain}/screenshots/{suffix}/screenshot.png"
        screenshot_uri = f"gs://{self.data_bucket}/{screenshot_path}"

        blob = bucket.blob(screenshot_path)
        blob.upload_from_string(screenshot_bytes, content_type="image/png")

        return {"screenshot_uri": screenshot_uri}

    def set_review_status(self, domain: str, capture_context_id: str, language: str, record: dict) -> str:
        from pipeline.storage import _gcs_client

        client = _gcs_client()
        bucket = client.bucket(self._review_bucket)
        path = f"{domain}/reviews/{capture_context_id}/{language}/status.json"
        blob = bucket.blob(path)
        blob.upload_from_string(json.dumps(record), content_type="application/json")
        return f"gs://{self._review_bucket}/{path}"

    def get_review_status(self, domain: str, capture_context_id: str, language: str) -> dict | None:
        from pipeline.storage import _gcs_client

        client = _gcs_client()
        bucket = client.bucket(self._review_bucket)
        path = f"{domain}/reviews/{capture_context_id}/{language}/status.json"
        blob = bucket.blob(path)
        if not blob.exists():
            return None
        return json.loads(blob.download_as_text())

    def list_review_statuses(self, domain: str) -> list[dict]:
        from pipeline.storage import _gcs_client

        client = _gcs_client()
        bucket = client.bucket(self._review_bucket)
        prefix = f"{domain}/reviews/"
        results = []
        for blob_meta in bucket.list_blobs(prefix=prefix):
            name = blob_meta.name
            if not name.endswith("/status.json"):
                continue
            parts = name[len(prefix):].split("/")
            if len(parts) < 3:
                continue
            capture_context_id = parts[0]
            language = parts[1]
            blob = bucket.blob(name)
            try:
                record = json.loads(blob.download_as_text())
                record["capture_context_id"] = capture_context_id
                record["language"] = language
                results.append(record)
            except Exception:
                continue
        return results


# ---------------------------------------------------------------------------
# Determinism helpers
# ---------------------------------------------------------------------------


class DeterminismError(Exception):
    pass


def _canonical_bbox_payload(bbox: dict) -> str:
    return json.dumps(
        {
            "x": _round_coord(bbox.get("x", 0)),
            "y": _round_coord(bbox.get("y", 0)),
            "width": _round_coord(bbox.get("width", 0)),
            "height": _round_coord(bbox.get("height", 0)),
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def _round_coord(value: Any) -> int:
    try:
        return int(math.floor(float(value)))
    except (TypeError, ValueError):
        return 0


def _canonical_element_sort_key(el: dict) -> tuple:
    bbox = el.get("bbox", {})
    return (
        el.get("css_selector") or "",
        _round_coord(bbox.get("y", 0)),
        _round_coord(bbox.get("x", 0)),
        _round_coord(bbox.get("width", 0)),
        _round_coord(bbox.get("height", 0)),
        el.get("element_type", ""),
    )


# ---------------------------------------------------------------------------
# capture_state — single capture context → validated artifacts
# ---------------------------------------------------------------------------

from pipeline.schema_validator import validate


def capture_state(
    context: CaptureContext,
    page_payload: tuple[dict[str, Any], list[dict[str, Any]]],
    writer: ArtifactWriter,
    run_context: RunContext,
) -> dict[str, Any]:
    validate_state_name(context.state)
    assert_language_not_in_contract_identity(context)
    capture_context_id = build_capture_context_id(context)
    page_id = compute_page_id(context)
    page_content, raw_elements = page_payload

    elements: list[dict[str, Any]] = []
    for raw in sorted(raw_elements, key=_canonical_element_sort_key):
        selector = raw.get("css_selector")
        bbox = raw.get("bbox")
        if bbox is None:
            raise DeterminismError("Bounding box unavailable")
        canonical_bbox = json.loads(_canonical_bbox_payload(bbox))
        elements.append({
            "item_id": compute_item_id(context.domain, context.url, selector, canonical_bbox, raw.get("element_type", "unknown")),
            "page_id": page_id,
            "url": context.url,
            "language": context.language,
            "viewport_kind": context.viewport_kind,
            "state": context.state,
            "user_tier": context.user_tier,
            "element_type": raw.get("element_type", "unknown"),
            "css_selector": selector,
            "bbox": canonical_bbox,
            "text": raw.get("text", ""),
            "visible": bool(raw.get("visible", True)),
            "tag": raw.get("tag"),
            "attributes": raw.get("attributes"),
        })

    elements.sort(key=lambda row: row["item_id"])
    page_artifact = {
        "page_id": page_id,
        "url": context.url,
        "language": context.language,
        "viewport_kind": context.viewport_kind,
        "state": context.state,
        "user_tier": context.user_tier,
        "screenshot_id": f"screenshot-{page_id}",
        "storage_uri": "",
        "captured_at": run_context.run_started_at,
        "viewport": page_content.get("viewport"),
    }
    validate("collected_items", elements)

    predicted_url_hash = deterministic_url_hash(context.url)
    predicted_suffix = f"{context.language}/{predicted_url_hash}/{context.state}/{context.viewport_kind}/{context.user_tier or 'null'}"
    predicted_screenshot_uri = f"gs://{writer.data_bucket}/domain/{context.domain}/screenshots/{predicted_suffix}/screenshot.png"
    page_artifact["storage_uri"] = predicted_screenshot_uri
    validate("page_screenshots", [page_artifact])

    uris = writer.write_capture(context, page_artifact, elements, page_content["screenshot_bytes"])
    if uris["screenshot_uri"] != predicted_screenshot_uri:
        raise DeterminismError("Artifact writer returned unexpected screenshot URI")
    return {"capture_context_id": capture_context_id, "page": page_artifact, "elements": elements, "uris": uris}


def build_universal_sections_en_only(
    en_pages: list[dict[str, Any]],
    en_items: list[dict[str, Any]],
    run_context: RunContext,
) -> list[dict[str, Any]]:
    baseline_pages = sorted((p for p in en_pages if p["state"] == "baseline"), key=lambda p: p["url"])
    items_by_page: dict[str, list[dict[str, Any]]] = {}
    for item in en_items:
        if item["state"] == "baseline" and item.get("language") == "en":
            items_by_page.setdefault(item["page_id"], []).append(item)

    fingerprints: dict[str, dict[str, Any]] = {}
    for page in baseline_pages:
        page_id = page["page_id"]
        page_items = sorted(items_by_page.get(page_id, []), key=lambda r: r["item_id"])
        if not page_items:
            continue
        fp_payload = json.dumps(
            [{"item_id": it["item_id"], "text": it.get("text", "")} for it in page_items],
            sort_keys=True, separators=(",", ":"),
        )
        fingerprint = hashlib.sha1(fp_payload.encode("utf-8")).hexdigest()
        if fingerprint not in fingerprints:
            fingerprints[fingerprint] = {
                "fingerprint": fingerprint,
                "representative_url": page["url"],
                "representative_page_id": page_id,
                "item_ids": [it["item_id"] for it in page_items],
                "element_count": len(page_items),
                "created_at": run_context.run_started_at,
            }
    return sorted(fingerprints.values(), key=lambda s: s["fingerprint"])
