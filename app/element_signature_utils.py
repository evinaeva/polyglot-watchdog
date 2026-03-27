"""Helpers for deterministic element-signature normalization and rendering."""

from __future__ import annotations

import json


def _normalize_class_list(value: object) -> list[str]:
    if isinstance(value, list):
        parts = [str(item or "") for item in value]
    else:
        parts = str(value or "").split()
    return sorted({chunk.strip() for chunk in parts if chunk and chunk.strip()})


def _normalize_signature_attributes(value: object) -> dict[str, str]:
    attrs = value if isinstance(value, dict) else {}
    normalized: dict[str, str] = {}
    test_id = str(
        attrs.get("data-testid")
        or attrs.get("data_testid")
        or attrs.get("dataTestid")
        or ""
    ).strip()
    if test_id:
        normalized["data-testid"] = test_id
    return normalized


def _build_element_signature(row: dict) -> dict[str, object]:
    attrs = row.get("attributes") if isinstance(row.get("attributes"), dict) else {}
    tag = str(row.get("tag") or row.get("element_type") or "").strip().lower()
    element_id = str(attrs.get("id") or row.get("id") or "").strip()
    classes = _normalize_class_list(attrs.get("class") or attrs.get("className") or row.get("classes") or "")
    css_selector = str(row.get("css_selector") or "").strip()
    stable_attrs = _normalize_signature_attributes(attrs)
    return {
        "match_type": "element_signature",
        "tag": tag,
        "id": element_id,
        "classes": classes,
        "css_selector": css_selector,
        "attributes": stable_attrs,
    }


def _signature_is_specific(signature: dict[str, object]) -> bool:
    classes = [str(token).strip() for token in list(signature.get("classes") or []) if str(token).strip()]
    attrs = signature.get("attributes") if isinstance(signature.get("attributes"), dict) else {}
    return bool(
        str(signature.get("id") or "").strip()
        or str(attrs.get("data-testid") or "").strip()
        or str(signature.get("css_selector") or "").strip()
        or len(classes) >= 2
    )


def _signature_key(signature: dict[str, object]) -> str:
    canonical = {
        "tag": str(signature.get("tag") or ""),
        "id": str(signature.get("id") or ""),
        "classes": list(signature.get("classes") or []),
        "css_selector": str(signature.get("css_selector") or ""),
        "attributes": dict(signature.get("attributes") or {}),
    }
    return json.dumps(canonical, sort_keys=True, separators=(",", ":"))


def _signature_description(signature: dict[str, object]) -> str:
    tag = str(signature.get("tag") or "element")
    element_id = str(signature.get("id") or "")
    classes = [str(c) for c in signature.get("classes") or [] if str(c).strip()]
    selector = str(signature.get("css_selector") or "")
    attrs = signature.get("attributes") if isinstance(signature.get("attributes"), dict) else {}
    id_part = f"#{element_id}" if element_id else ""
    class_part = "".join(f".{c}" for c in classes)
    parts = [f"{tag}{id_part}{class_part}".strip()]
    if selector:
        parts.append(f"selector={selector}")
    if attrs:
        attrs_view = ", ".join(f"{k}={v}" for k, v in sorted(attrs.items()))
        parts.append(f"attrs({attrs_view})")
    return " · ".join(parts)
