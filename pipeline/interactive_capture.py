from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Protocol
from pipeline.phase0_crawler import canonicalize_url
from pipeline.schema_validator import validate

STATE_PATTERN = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
_ITEM_ID_DELIMITER = "\x1f"


class DeterminismError(RuntimeError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


@dataclass(frozen=True)
class RunContext:
    run_id: str
    run_started_at: str


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
    recipe_id: str
    url_pattern: str
    steps: tuple[RecipeStep, ...]
    capture_points: tuple[CapturePoint, ...]


@dataclass(frozen=True)
class CaptureJob:
    context: CaptureContext
    mode: str
    recipe_id: str | None = None


class ConfigStore(Protocol):
    def read_json(self, bucket: str, key: str) -> Any: ...
    def write_json(self, bucket: str, key: str, value: Any) -> str: ...
    def write_bytes(self, bucket: str, key: str, value: bytes, content_type: str) -> str: ...


class ArtifactWriter(Protocol):
    def write_capture(self, context: CaptureContext, page_artifact: dict[str, Any], elements_artifact: list[dict[str, Any]], screenshot_bytes: bytes) -> dict[str, str]: ...


def canonicalize_url_for_hash(url: str) -> str:
    # Reuse the contract-authoritative canonicalization implementation from Phase 0.
    return canonicalize_url(url)


def deterministic_url_hash(url: str) -> str:
    return hashlib.sha1(canonicalize_url_for_hash(url).encode("utf-8")).hexdigest()


def build_capture_context_id(context: CaptureContext) -> str:
    payload = "|".join([
        context.domain,
        context.url,
        context.viewport_kind,
        context.state,
        context.user_tier or "",
    ])
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def compute_page_id(context: CaptureContext) -> str:
    payload = "|".join([context.url, context.viewport_kind, context.state, context.user_tier or ""])
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def _canonical_bbox_payload(bbox: dict[str, Any]) -> str:
    required = ("x", "y", "width", "height")
    missing = [k for k in required if k not in bbox or bbox[k] is None]
    if missing:
        raise DeterminismError(f"Bounding box unavailable: missing {','.join(missing)}")
    for key in required:
        value = bbox[key]
        if not isinstance(value, (int, float)):
            raise DeterminismError(f"Bounding box field '{key}' must be numeric")
    canonical_bbox = {k: bbox[k] for k in required}
    return json.dumps(canonical_bbox, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def compute_item_id(domain: str, url: str, css_selector: str, bbox: dict[str, Any], element_type: str) -> str:
    if not css_selector:
        raise DeterminismError("Selector generation cannot be guaranteed")
    canonical_bbox = _canonical_bbox_payload(bbox)
    payload = _ITEM_ID_DELIMITER.join([domain, url, css_selector, canonical_bbox, element_type])
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def validate_state_name(state: str) -> None:
    if not STATE_PATTERN.fullmatch(state):
        raise ValueError(f"Invalid state name: {state}")


class DeterministicPlanner:
    def expand_jobs(self, seed_urls: dict[str, Any], recipes: dict[str, Recipe], languages: list[str], viewports: list[str], user_tiers: list[str]) -> list[CaptureJob]:
        rows = sorted(seed_urls["urls"], key=lambda row: row["url"])
        jobs: list[CaptureJob] = []
        for language in sorted(languages):
            for viewport in sorted(viewports):
                for user_tier in sorted(user_tiers):
                    for row in rows:
                        url = row["url"]
                        jobs.append(CaptureJob(CaptureContext(seed_urls["domain"], url, language, viewport, "baseline", user_tier), "baseline"))
                        for recipe_id in sorted(row.get("recipe_ids", [])):
                            recipe = recipes[recipe_id]
                            for point in recipe.capture_points:
                                validate_state_name(point.state)
                                jobs.append(CaptureJob(CaptureContext(seed_urls["domain"], url, language, viewport, point.state, user_tier), "recipe", recipe_id))
        jobs.sort(key=lambda j: (j.context.domain, j.context.language, j.context.url, j.context.viewport_kind, j.context.user_tier or "", j.context.state, j.recipe_id or ""))
        return jobs


class InMemoryStore:
    def __init__(self):
        self.objects: dict[tuple[str, str], bytes] = {}

    def read_json(self, bucket: str, key: str) -> Any:
        return json.loads(self.objects[(bucket, key)].decode("utf-8"))

    def write_json(self, bucket: str, key: str, value: Any) -> str:
        self.objects[(bucket, key)] = canonical_json_bytes(value)
        return f"gs://{bucket}/{key}"

    def write_bytes(self, bucket: str, key: str, value: bytes, content_type: str) -> str:
        self.objects[(bucket, key)] = value
        return f"gs://{bucket}/{key}"


class GCSArtifactWriter:
    def __init__(self, store: ConfigStore, data_bucket: str, review_bucket: str):
        self.store = store
        self.data_bucket = data_bucket
        self.review_bucket = review_bucket

    def _prefix(self, context: CaptureContext) -> str:
        return f"domain/{context.domain}"

    def write_capture(self, context: CaptureContext, page_artifact: dict[str, Any], elements_artifact: list[dict[str, Any]], screenshot_bytes: bytes) -> dict[str, str]:
        url_hash = deterministic_url_hash(context.url)
        suffix = f"{url_hash}/{context.state}/{context.viewport_kind}/{context.user_tier or 'null'}"
        screenshot_uri = self.store.write_bytes(
            self.data_bucket,
            f"{self._prefix(context)}/screenshots/{suffix}/screenshot.png",
            screenshot_bytes,
            "image/png",
        )
        page_with_storage = dict(page_artifact)
        page_with_storage["storage_uri"] = screenshot_uri
        page_uri = self.store.write_json(self.data_bucket, f"{self._prefix(context)}/pages/{suffix}/page.json", page_with_storage)
        elements_uri = self.store.write_json(self.data_bucket, f"{self._prefix(context)}/elements/{suffix}/elements.json", elements_artifact)
        return {"page_uri": page_uri, "elements_uri": elements_uri, "screenshot_uri": screenshot_uri}

    def set_review_status(self, domain: str, record: dict[str, Any]) -> str:
        return self.store.write_json(self.review_bucket, f"{domain}/capture_status/{record['capture_context_id']}.json", record)


def _canonical_element_sort_key(raw: dict[str, Any]) -> tuple[str, str, str, str]:
    selector = raw.get("css_selector")
    if not selector:
        raise DeterminismError("Selector generation cannot be guaranteed")
    bbox = raw.get("bbox")
    if bbox is None:
        raise DeterminismError("Bounding box unavailable")
    bbox_payload = _canonical_bbox_payload(bbox)
    return (
        selector,
        raw.get("element_type", "unknown"),
        bbox_payload,
        raw.get("tag") or "",
    )


def capture_state(
    context: CaptureContext,
    page_payload: tuple[dict[str, Any], list[dict[str, Any]]],
    writer: ArtifactWriter,
    run_context: RunContext,
) -> dict[str, Any]:
    validate_state_name(context.state)
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
    predicted_suffix = f"{predicted_url_hash}/{context.state}/{context.viewport_kind}/{context.user_tier or 'null'}"
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

    grouped: dict[str, dict[str, Any]] = {}
    for page in baseline_pages:
        section_items = [
            i
            for i in items_by_page.get(page["page_id"], [])
            if i["css_selector"].startswith("header") or i["css_selector"].startswith("footer")
        ]
        if not section_items:
            continue
        signature = sorted((i["css_selector"], i["element_type"], i["text"]) for i in section_items)
        fingerprint = hashlib.sha1(canonical_json_bytes(signature)).hexdigest()
        if fingerprint not in grouped:
            grouped[fingerprint] = {
                "section_id": f"sec-{fingerprint[:16]}",
                "label": "universal_section",
                "representative_url": page["url"],
                "representative_page_id": page["page_id"],
                "fingerprint": fingerprint,
                "member_urls_count": 1,
                "member_urls": [page["url"]],
                "created_at": run_context.run_started_at,
            }
        else:
            grouped[fingerprint]["member_urls_count"] += 1
            grouped[fingerprint]["member_urls"].append(page["url"])

    sections = [s for s in grouped.values() if s["member_urls_count"] > 1]
    for sec in sections:
        sec["member_urls"] = sorted(sec["member_urls"])
    sections.sort(key=lambda s: s["section_id"])
    validate("universal_sections", sections)
    return sections


def build_eligible_dataset(
    collected_items: list[dict[str, Any]],
    review_statuses: list[dict[str, Any]],
    page_records_by_capture_context_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    blocked_page_ids: set[str] = set()
    for review in review_statuses:
        if review["status"] != "blocked_by_overlay":
            continue
        page_record = page_records_by_capture_context_id.get(review["capture_context_id"])
        if page_record is None:
            raise DeterminismError(f"Missing page record for capture_context_id={review['capture_context_id']}")
        blocked_page_ids.add(page_record["page_id"])

    eligible = [item for item in collected_items if item["page_id"] not in blocked_page_ids]
    eligible.sort(key=lambda row: row["item_id"])
    return eligible


def pair_by_item_id(source_items: list[dict[str, Any]], target_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    target_by_id = {item["item_id"]: item for item in target_items}
    return [{"item_id": src["item_id"], "source": src, "target": target_by_id.get(src["item_id"])} for src in sorted(source_items, key=lambda i: i["item_id"])]


def generate_issues(pairs: list[dict[str, Any]], expected_states: set[str], actual_states: set[str], blocked_contexts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for rec in sorted(blocked_contexts, key=lambda r: r["capture_context_id"]):
        issues.append({
            "id": f"overlay-{rec['capture_context_id']}",
            "category": "OVERLAY_BLOCKED_CAPTURE",
            "confidence": 1.0,
            "message": "Capture blocked by overlay",
            "evidence": {"url": rec.get("url", ""), "bbox": {"x": 0, "y": 0, "width": 0, "height": 0}, "storage_uri": rec.get("storage_uri", "")},
        })
    for state in sorted(expected_states - actual_states):
        issues.append({
            "id": f"missing-state-{state}",
            "category": "MISSING_INTERACTIVE_STATE",
            "confidence": 1.0,
            "message": f"Missing expected interactive state: {state}",
            "evidence": {"url": "", "bbox": {"x": 0, "y": 0, "width": 0, "height": 0}, "storage_uri": ""},
        })
    for pair in pairs:
        if pair["target"] is None:
            issues.append({
                "id": f"missing-translation-{pair['item_id']}",
                "category": "MISSING_TRANSLATION",
                "confidence": 0.9,
                "message": "Missing paired target item",
                "evidence": {"url": pair["source"]["url"], "bbox": pair["source"]["bbox"], "storage_uri": pair["source"].get("storage_uri", "")},
            })
    issues.sort(key=lambda item: item["id"])
    return issues
