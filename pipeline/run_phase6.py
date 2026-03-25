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
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

project_root = str(Path(__file__).resolve().parents[1])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from pipeline.phase6_providers import build_provider
from pipeline.phase6_review import ReviewContext, overlay_blocked_issue, prepare_review_inputs, review_pair
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


def _stable_semantic_attrs(item: dict) -> dict[str, str]:
    attrs = item.get("semantic_attrs")
    if not isinstance(attrs, dict):
        return {}
    return {
        str(k): str(v).strip()
        for k, v in sorted(attrs.items())
        if str(v).strip()
    }


def _derive_page_canonical_key(item: dict) -> str:
    existing = str(item.get("page_canonical_key", "")).strip()
    if existing:
        return existing
    payload = json.dumps({
        "url": item.get("url", ""),
        "viewport_kind": item.get("viewport_kind", ""),
        "state": item.get("state", ""),
        "user_tier": item.get("user_tier") or "",
    }, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def _derive_logical_match_key(item: dict) -> str:
    existing = str(item.get("logical_match_key", "")).strip()
    if existing:
        return existing
    payload = json.dumps({
        "page_canonical_key": _derive_page_canonical_key(item),
        "element_type": item.get("element_type", ""),
        "css_selector": item.get("css_selector", ""),
        "role_hint": item.get("role_hint") or "",
        "local_path_signature": item.get("local_path_signature") or "",
        "stable_ordinal": item.get("stable_ordinal", 0) or 0,
        "semantic_attrs": _stable_semantic_attrs(item),
    }, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def _score_pair(en_item: dict, target_item: dict) -> tuple[float, dict[str, float]]:
    breakdown: dict[str, float] = {}
    score = 0.0

    if str(en_item.get("css_selector", "")) == str(target_item.get("css_selector", "")):
        breakdown["selector"] = 0.33
        score += 0.33
    if str(en_item.get("item_id", "")) and str(en_item.get("item_id", "")) == str(target_item.get("item_id", "")):
        breakdown["item_id_hint"] = 0.25
        score += 0.25
    if str(en_item.get("local_path_signature", "")) == str(target_item.get("local_path_signature", "")) and str(en_item.get("local_path_signature", "")):
        breakdown["path"] = 0.2
        score += 0.2
    if str(en_item.get("container_signature", "")) == str(target_item.get("container_signature", "")) and str(en_item.get("container_signature", "")):
        breakdown["container"] = 0.15
        score += 0.15
    if str(en_item.get("role_hint", "")) and str(en_item.get("role_hint", "")) == str(target_item.get("role_hint", "")):
        breakdown["role"] = 0.08
        score += 0.08
    if str(en_item.get("element_type", "")) == str(target_item.get("element_type", "")) and str(en_item.get("element_type", "")):
        breakdown["tag"] = 0.08
        score += 0.08
    if int(en_item.get("stable_ordinal", 0) or 0) and int(en_item.get("stable_ordinal", 0) or 0) == int(target_item.get("stable_ordinal", 0) or 0):
        breakdown["ordinal"] = 0.08
        score += 0.08

    en_attrs = _stable_semantic_attrs(en_item)
    target_attrs = _stable_semantic_attrs(target_item)
    if en_attrs and target_attrs:
        overlap = sum(1 for key, value in en_attrs.items() if target_attrs.get(key) == value)
        ratio = overlap / max(len(en_attrs), len(target_attrs))
        attr_score = round(0.13 * ratio, 4)
        if attr_score > 0:
            breakdown["attrs"] = attr_score
            score += attr_score

    en_text = str(en_item.get("text", "")).strip()
    target_text = str(target_item.get("text", "")).strip()
    if en_text and target_text and en_text == target_text:
        breakdown["text_weak"] = 0.04
        score += 0.04

    return round(score, 4), breakdown


def _pair_target_items(en_item: dict, candidates: list[dict], used_target_ids: set[str]) -> tuple[dict | None, dict[str, Any]]:
    available = [item for item in candidates if item.get("item_id") not in used_target_ids]
    if not available:
        return None, {
            "pairing_basis": "none",
            "pairing_confidence": 0.0,
            "matched_target_item_id": None,
            "logical_match_key": _derive_logical_match_key(en_item),
            "pairing_score_breakdown": {},
        }

    logical_key = _derive_logical_match_key(en_item)
    exact = [item for item in available if _derive_logical_match_key(item) == logical_key]
    if len(exact) == 1:
        matched = exact[0]
        return matched, {
            "pairing_basis": "logical_match_key_exact",
            "pairing_confidence": 1.0,
            "matched_target_item_id": matched.get("item_id"),
            "logical_match_key": logical_key,
            "pairing_score_breakdown": {},
        }
    if len(exact) > 1:
        return None, {
            "pairing_basis": "ambiguous_logical_match_key",
            "pairing_confidence": 0.0,
            "matched_target_item_id": None,
            "logical_match_key": logical_key,
            "pairing_score_breakdown": {
                "candidate_item_ids": sorted(str(row.get("item_id", "")) for row in exact),
            },
        }

    scored = []
    for candidate in available:
        score, breakdown = _score_pair(en_item, candidate)
        scored.append((score, str(candidate.get("item_id", "")), candidate, breakdown))
    scored.sort(key=lambda row: (-row[0], row[1]))
    top_score, _, top_candidate, top_breakdown = scored[0]
    second_score = scored[1][0] if len(scored) > 1 else -1.0
    tie = len(scored) > 1 and abs(top_score - second_score) < 0.0001
    min_viable_score = 0.20 if len(scored) == 1 else 0.35
    if top_score < min_viable_score or tie:
        return None, {
            "pairing_basis": "fallback_ambiguous" if tie else "fallback_no_viable_candidate",
            "pairing_confidence": 0.0,
            "matched_target_item_id": None,
            "logical_match_key": logical_key,
            "pairing_score_breakdown": {
                "top_score": top_score,
                "top_candidate_item_id": top_candidate.get("item_id"),
                "top_breakdown": top_breakdown,
                "second_score": second_score if len(scored) > 1 else None,
                "second_candidate_item_id": scored[1][2].get("item_id") if len(scored) > 1 else None,
            },
        }

    return top_candidate, {
        "pairing_basis": "fallback_weighted",
        "pairing_confidence": top_score,
        "matched_target_item_id": top_candidate.get("item_id"),
        "logical_match_key": logical_key,
        "pairing_score_breakdown": {
            "top_score": top_score,
            "weights": top_breakdown,
        },
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


def _resolve_review_mode(review_mode: str | None, require_explicit_mode: bool) -> str:
    env_mode = os.environ.get("PHASE6_REVIEW_PROVIDER")
    resolved = (review_mode or env_mode or "").strip()
    if resolved:
        return resolved
    raise ValueError(
        "Phase 6 review mode must be set explicitly via --review-mode or PHASE6_REVIEW_PROVIDER. "
        "Supported modes: test-heuristic, disabled, llm"
    )


def _image_meta(item: dict, ocr_row: dict | None) -> dict:
    attrs = item.get("attributes") if isinstance(item.get("attributes"), dict) else {}
    src = str((ocr_row or {}).get("src", "") or attrs.get("src", "") or "").strip()
    alt = str((ocr_row or {}).get("alt", "") or attrs.get("alt", "") or "").strip()
    is_svg = bool((ocr_row or {}).get("is_svg")) or str(item.get("tag", "")).strip().lower() == "svg" or "image/svg+xml" in src.lower() or src.lower().endswith(".svg")
    svg_text = str((ocr_row or {}).get("svg_text", "")).strip()
    asset_hash = str((ocr_row or {}).get("asset_hash", "")).strip() or hashlib.sha1((src or item.get("item_id", "")).encode("utf-8")).hexdigest()
    return {
        "asset_hash": asset_hash,
        "src": src,
        "alt": alt,
        "is_svg": is_svg,
        "svg_text": svg_text,
    }


def _build_coverage_gaps(
    target_eligible: list[dict],
    target_collected_by_item: dict[str, dict],
    ocr_by_item: dict[str, dict],
    blocked_item_ids: set[str],
    pairing_meta_by_en_item: dict[str, dict[str, Any]],
) -> tuple[list[dict], dict[str, int]]:
    rows: list[dict] = []
    counters = {
        "image_text_reviewed": 0,
        "image_text_not_reviewed": 0,
        "image_text_review_blocked": 0,
    }
    for item in sorted((r for r in target_eligible if str(r.get("language", "")).strip().lower() != "en"), key=lambda r: (r.get("item_id", ""), r.get("url", ""))):
        item_id = str(item.get("item_id", "")).strip()
        if not item_id:
            continue
        collected = target_collected_by_item.get(item_id, {})
        candidate = {**collected, **item}
        if not _is_image_item(candidate):
            continue
        ocr_row = ocr_by_item.get(item_id, {})
        meta = _image_meta(candidate, ocr_row)
        reviewed = bool(meta["svg_text"]) or ocr_row.get("status") == "ok"
        blocked = item_id in blocked_item_ids
        if blocked:
            status = "image_text_review_blocked"
            reason = "capture_blocked_by_overlay"
        elif reviewed:
            status = "image_text_reviewed"
            reason = "svg_text_extracted" if meta["svg_text"] else "ocr_text_available"
        else:
            status = "image_text_not_reviewed"
            reason = "no_svg_or_ocr_text"
        counters[status] += 1
        if status == "image_text_reviewed":
            continue
        pair_meta = pairing_meta_by_en_item.get(item_id, {})
        rows.append({
            "item_id": item_id,
            "page_id": candidate.get("page_id"),
            "url": candidate.get("url", ""),
            "language": candidate.get("language", ""),
            "image_text_review_status": status,
            "asset_hash": meta["asset_hash"],
            "src": meta["src"],
            "alt": meta["alt"],
            "is_svg": meta["is_svg"],
            "svg_text": meta["svg_text"],
            "matched_target_item_id": pair_meta.get("matched_target_item_id"),
            "pairing_basis": pair_meta.get("pairing_basis"),
            "ocr_status": ocr_row.get("status"),
            "coverage_reason": reason,
        })
    rows.sort(key=lambda row: (row["item_id"], row["url"]))
    return rows, counters


def run(
    domain: str,
    en_run_id: str,
    target_run_id: str,
    review_mode: str | None = None,
    *,
    require_explicit_mode: bool = True,
) -> list[dict]:
    resolved_review_mode = _resolve_review_mode(review_mode, require_explicit_mode=require_explicit_mode)
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
    blocked_item_ids: set[str] = set()
    blocked_urls = {str(row.get("url", "")).strip() for row in blocked_pages}
    for item in target_eligible:
        item_id = str(item.get("item_id", "")).strip()
        if item_id and str(item.get("url", "")).strip() in blocked_urls:
            blocked_item_ids.add(item_id)
    provider = build_provider(mode=resolved_review_mode)
    if hasattr(provider, "prefetch_reviews"):
        prefetch_pairs = []
        used_target_ids_for_prefetch: set[str] = set()
        target_candidates = [target_by_item[item_id] for item_id in sorted(target_by_item.keys())]
        for item_id in sorted(en_by_item.keys()):
            matched, _ = _pair_target_items(en_by_item[item_id], target_candidates, used_target_ids_for_prefetch)
            if not matched:
                continue
            used_target_ids_for_prefetch.add(str(matched.get("item_id")))
            prepared = prepare_review_inputs(en_by_item[item_id], matched)
            prefetch_pairs.append((prepared.en_text, prepared.target_text))
        provider.prefetch_reviews(prefetch_pairs, target_language)

    issues: list[dict] = []
    used_target_ids: set[str] = set()
    target_candidates = [target_by_item[item_id] for item_id in sorted(target_by_item.keys())]
    pairing_meta_by_target_item_id: dict[str, dict[str, Any]] = {}

    for item_id in sorted(en_by_item.keys()):
        en_item = en_by_item[item_id]
        t_item, pairing_meta = _pair_target_items(en_item, target_candidates, used_target_ids)
        if t_item:
            used_target_ids.add(str(t_item.get("item_id")))
            pairing_meta_by_target_item_id[str(t_item.get("item_id"))] = dict(pairing_meta)
        evidence_base = _build_evidence(t_item, target_collected_by_item, target_screens_by_page) if t_item else _build_missing_target_evidence(en_item, en_collected_by_item, en_screens_by_page)
        evidence_base.update(pairing_meta)
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
    coverage_gaps, coverage_counters = _build_coverage_gaps(
        target_eligible=target_eligible,
        target_collected_by_item=target_collected_by_item,
        ocr_by_item=ocr_by_item,
        blocked_item_ids=blocked_item_ids,
        pairing_meta_by_en_item=pairing_meta_by_target_item_id,
    )
    validate("coverage_gaps", coverage_gaps)
    write_json_artifact(domain, target_run_id, "coverage_gaps.json", coverage_gaps)
    if hasattr(provider, "get_llm_review_stats"):
        llm_review_stats = provider.get_llm_review_stats()
    else:
        llm_review_stats = {}
    llm_review_stats["review_mode"] = str(llm_review_stats.get("review_mode") or resolved_review_mode)
    write_json_artifact(domain, target_run_id, "llm_review_stats.json", llm_review_stats)
    manifest = {
        "schema_version": "v1.0",
        "phase": "phase6",
        "run_id": target_run_id,
        "domain": domain,
        "artifact_uris": sorted([
            f"gs://{BUCKET_NAME}/{domain}/{target_run_id}/coverage_gaps.json",
            f"gs://{BUCKET_NAME}/{domain}/{target_run_id}/issues.json",
            f"gs://{BUCKET_NAME}/{domain}/{target_run_id}/llm_review_stats.json",
        ]),
        "summary_counters": {
            "issues": len(issues),
            **coverage_counters,
            "coverage_gaps": len(coverage_gaps),
        },
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
    parser.add_argument("--review-mode", dest="review_mode", required=False)
    args = parser.parse_args()
    run(
        args.domain,
        args.en_run_id,
        args.target_run_id,
        review_mode=args.review_mode,
        require_explicit_mode=True,
    )
