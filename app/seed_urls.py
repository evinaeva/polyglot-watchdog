"""Seed URL persistence and normalization helpers."""

from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from pipeline import storage
from pipeline.runtime_config import validate_seed_urls_payload


_SEED_URLS_FILENAME = "seed_urls.json"
_SEED_URL_STATES_FILENAME = "seed_url_states.json"


def normalize_seed_url(line: str) -> str | None:
    """Normalize one seed URL line using contract-compatible rules."""
    value = line.strip()
    if not value:
        return None
    if "://" not in value:
        value = f"https://{value}"
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("url must use http or https")
    if not parsed.netloc:
        raise ValueError("url must include host")

    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/") or "/"

    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, parsed.query, parsed.fragment))


def parse_seed_urls_with_errors(multiline: str) -> dict[str, list]:
    """Parse multiline URLs and return canonical urls + per-line validation errors."""
    urls: set[str] = set()
    errors: list[dict[str, Any]] = []
    for line_no, raw in enumerate(multiline.splitlines(), start=1):
        try:
            value = normalize_seed_url(raw)
            if value is not None:
                urls.add(value)
        except ValueError as exc:
            errors.append({"line": line_no, "input": raw, "error": str(exc)})
    return {"urls": sorted(urls), "errors": errors}


def parse_seed_urls(multiline: str) -> list[str]:
    """Backward-compatible parser that raises on first invalid line."""
    parsed = parse_seed_urls_with_errors(multiline)
    if parsed["errors"]:
        first = parsed["errors"][0]
        raise ValueError(f"line {first['line']}: {first['error']}")
    return parsed["urls"]


def _utc_now_rfc3339() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _seed_rows(urls: list[str], active_by_url: dict[str, bool] | None = None) -> list[dict[str, Any]]:
    active_lookup = active_by_url or {}
    rows: list[dict[str, Any]] = []
    for raw in sorted(set(urls)):
        rows.append({
            "url": raw,
            "description": None,
            "recipe_ids": [],
            "active": bool(active_lookup.get(raw, True)),
        })
    return rows


def _seed_payload(
    domain: str,
    urls: list[str],
    updated_at: str | None = None,
    *,
    active_by_url: dict[str, bool] | None = None,
) -> dict[str, Any]:
    return {
        "domain": domain,
        "updated_at": updated_at or _utc_now_rfc3339(),
        "urls": _seed_rows(urls, active_by_url=active_by_url),
    }


def _contract_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "url": row["url"],
            "description": row.get("description"),
            "recipe_ids": row.get("recipe_ids", []),
        }
        for row in rows
    ]


def _active_map_payload(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "updated_at": _utc_now_rfc3339(),
        "states": [
            {"url": row["url"], "active": bool(row.get("active", True))}
            for row in rows
        ],
    }


def _load_active_map(domain: str) -> dict[str, bool]:
    payload = storage.read_json_artifact(domain, "manual", _SEED_URL_STATES_FILENAME)
    if not isinstance(payload, dict):
        return {}
    states = payload.get("states", [])
    if not isinstance(states, list):
        return {}
    result: dict[str, bool] = {}
    for row in states:
        if not isinstance(row, dict):
            continue
        try:
            url = normalize_seed_url(str(row.get("url", "")))
        except ValueError:
            continue
        if not url:
            continue
        result[url] = bool(row.get("active", True))
    return result


def validate_domain(domain: str) -> str:
    if not domain or any(char.isspace() for char in domain):
        raise ValueError("domain must be non-empty and contain no whitespace")
    if re.match(r"^bhttps?://", str(domain).strip(), flags=re.IGNORECASE):
        raise ValueError("domain appears malformed")
    return domain


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized_url = normalize_seed_url(str(row.get("url", "")))
    if normalized_url is None:
        raise ValueError("url row missing url")
    recipe_ids = sorted({str(item).strip() for item in row.get("recipe_ids", []) if str(item).strip()})
    return {
        "url": normalized_url,
        "description": row.get("description"),
        "recipe_ids": recipe_ids,
        "active": bool(row.get("active", True)),
    }


def read_seed_urls(domain: str) -> dict[str, Any]:
    """Load persisted seed URLs or return empty payload when missing."""
    try:
        payload = storage.read_json_artifact(domain, "manual", _SEED_URLS_FILENAME)
    except Exception:
        return _seed_payload(domain, [])

    if not isinstance(payload, dict):
        return _seed_payload(domain, [])

    urls = payload.get("urls")
    raw_updated_at = payload.get("updated_at")
    updated_at = raw_updated_at if isinstance(raw_updated_at, str) else _utc_now_rfc3339()
    if not isinstance(urls, list):
        return _seed_payload(domain, [], updated_at=updated_at)

    try:
        active_by_url = _load_active_map(domain)
    except Exception:
        active_by_url = {}

    rows: list[dict[str, Any]] = []
    for row in urls:
        if not isinstance(row, dict):
            return _seed_payload(domain, [], updated_at=updated_at)
        normalized = _normalize_row(row)
        if normalized["url"] in active_by_url:
            normalized["active"] = active_by_url[normalized["url"]]
        rows.append(normalized)

    contract_payload = {"domain": domain, "updated_at": updated_at, "urls": _contract_rows(rows)}
    validate_seed_urls_payload(contract_payload)
    return {"domain": domain, "updated_at": updated_at, "urls": rows}


def write_seed_urls(domain: str, urls: list[str]) -> dict[str, Any]:
    rows = _seed_rows(urls)
    payload = {"domain": domain, "updated_at": _utc_now_rfc3339(), "urls": _contract_rows(rows)}
    validate_seed_urls_payload(payload)
    storage.write_json_artifact(domain, "manual", _SEED_URLS_FILENAME, payload)
    storage.write_json_artifact(domain, "manual", _SEED_URL_STATES_FILENAME, _active_map_payload(rows))
    return {"domain": domain, "updated_at": payload["updated_at"], "urls": rows}


def write_seed_rows(domain: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    normalized_rows = [_normalize_row(row) for row in rows]
    deduped_by_url = {row["url"]: row for row in normalized_rows}
    merged_rows = [deduped_by_url[url] for url in sorted(deduped_by_url)]
    updated_at = _utc_now_rfc3339()
    payload = {
        "domain": domain,
        "updated_at": updated_at,
        "urls": _contract_rows(merged_rows),
    }
    validate_seed_urls_payload(payload)
    storage.write_json_artifact(domain, "manual", _SEED_URLS_FILENAME, payload)
    storage.write_json_artifact(domain, "manual", _SEED_URL_STATES_FILENAME, _active_map_payload(merged_rows))
    return {"domain": domain, "updated_at": updated_at, "urls": merged_rows}
