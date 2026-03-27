from __future__ import annotations

import time

from app.artifact_helpers import _artifact_exists, _read_json_required
from app.element_signature_utils import (
    _build_element_signature,
    _normalize_class_list,
    _normalize_signature_attributes,
    _signature_description,
    _signature_is_specific,
    _signature_key,
)

_WHITELIST_RUN_ID = "_shared"
_WHITELIST_FILENAME = "element_type_whitelist.json"


def _normalize_whitelist_entry(value: object) -> dict[str, object] | None:
    if isinstance(value, str):
        # Keep legacy broad artifacts editable, but never apply them during matching.
        tag = value.strip().lower()
        if not tag:
            return None
        legacy = {
            "match_type": "legacy_element_type",
            "tag": tag,
            "id": "",
            "classes": [],
            "css_selector": "",
            "attributes": {},
            "created_at": "",
        }
        legacy["signature_key"] = _signature_key(legacy)
        legacy["description"] = f"Legacy broad rule ({tag})"
        return legacy
    if not isinstance(value, dict):
        return None
    if str(value.get("match_type") or "element_signature") != "element_signature":
        return None
    signature = {
        "match_type": "element_signature",
        "tag": str(value.get("tag") or "").strip().lower(),
        "id": str(value.get("id") or "").strip(),
        "classes": _normalize_class_list(value.get("classes") or []),
        "css_selector": str(value.get("css_selector") or "").strip(),
        "attributes": _normalize_signature_attributes(value.get("attributes") or {}),
        "created_at": str(value.get("created_at") or "").strip(),
    }
    if not signature["tag"] or not _signature_is_specific(signature):
        return None
    signature["signature_key"] = _signature_key(signature)
    signature["description"] = _signature_description(signature)
    return signature


def _load_domain_element_type_whitelist(domain: str) -> list[dict[str, object]]:
    if not _artifact_exists(domain, _WHITELIST_RUN_ID, _WHITELIST_FILENAME):
        return []
    payload = _read_json_required(domain, _WHITELIST_RUN_ID, _WHITELIST_FILENAME)
    if not isinstance(payload, list):
        raise ValueError(f"{_WHITELIST_FILENAME} artifact_invalid")
    values: list[dict[str, object]] = []
    seen: set[str] = set()
    for row in payload:
        value = _normalize_whitelist_entry(row)
        if value is None:
            continue
        key = str(value.get("signature_key") or "")
        if not key or key in seen:
            continue
        seen.add(key)
        values.append(value)
    values.sort(key=lambda item: str(item.get("description") or item.get("tag") or ""))
    return values


def _save_domain_element_type_whitelist(domain: str, values: list[dict[str, object]]) -> list[dict[str, object]]:
    from pipeline.storage import write_json_artifact

    deduped: dict[str, dict[str, object]] = {}
    for raw in values:
        normalized = _normalize_whitelist_entry(raw)
        if normalized is None or str(normalized.get("match_type")) != "element_signature":
            continue
        deduped[str(normalized["signature_key"])] = {
            "match_type": "element_signature",
            "tag": normalized["tag"],
            "id": normalized["id"],
            "classes": normalized["classes"],
            "css_selector": normalized["css_selector"],
            "attributes": normalized["attributes"],
            "created_at": str(normalized.get("created_at") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        }
    saved = sorted(deduped.values(), key=lambda item: _signature_description(item))
    write_json_artifact(domain, _WHITELIST_RUN_ID, _WHITELIST_FILENAME, saved)
    return _load_domain_element_type_whitelist(domain)


def _add_domain_element_type_whitelist(domain: str, source_row: dict) -> tuple[list[dict[str, object]], dict[str, object]]:
    values = _load_domain_element_type_whitelist(domain)
    signature = _build_element_signature(source_row)
    if not signature.get("tag") or not _signature_is_specific(signature):
        raise ValueError("element_signature_requires_specific_attributes")
    signature["created_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    values.append(signature)
    updated = _save_domain_element_type_whitelist(domain, values)
    added_key = _signature_key(signature)
    added = next((entry for entry in updated if str(entry.get("signature_key") or "") == added_key), {})
    return updated, added


def _remove_domain_element_type_whitelist(domain: str, signature_key: str) -> list[dict[str, object]]:
    normalized = str(signature_key or "").strip()
    values = [v for v in _load_domain_element_type_whitelist(domain) if str(v.get("signature_key") or "") != normalized]
    return _save_domain_element_type_whitelist(domain, values)


def _row_matches_whitelist(row: dict, whitelist: list[dict[str, object]]) -> bool:
    candidate = _build_element_signature(row)
    if not candidate.get("tag"):
        return False
    for entry in whitelist:
        if str(entry.get("match_type")) != "element_signature":
            continue
        if str(entry.get("tag") or "") != str(candidate.get("tag") or ""):
            continue
        if entry.get("id") and entry.get("id") != candidate.get("id"):
            continue
        if entry.get("css_selector") and entry.get("css_selector") != candidate.get("css_selector"):
            continue
        if entry.get("classes") and list(entry.get("classes") or []) != list(candidate.get("classes") or []):
            continue
        entry_attrs = entry.get("attributes") if isinstance(entry.get("attributes"), dict) else {}
        candidate_attrs = candidate.get("attributes") if isinstance(candidate.get("attributes"), dict) else {}
        if any(candidate_attrs.get(k) != v for k, v in entry_attrs.items()):
            continue
        return True
    return False
