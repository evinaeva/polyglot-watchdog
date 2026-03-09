"""Seed URL persistence and normalization helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from pipeline import storage
from pipeline.runtime_config import validate_seed_urls_payload


def normalize_seed_url(line: str) -> str | None:
    """Normalize one seed URL line using contract rules."""
    value = line.strip()
    if not value:
        return None
    if not (value.lower().startswith("http://") or value.lower().startswith("https://")):
        value = f"https://{value}"
    parsed = urlsplit(value)
    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValueError("url must use http or https scheme")
    if not parsed.netloc:
        raise ValueError("url must include host")
    lower_netloc = parsed.netloc.lower()
    return urlunsplit((parsed.scheme.lower(), lower_netloc, parsed.path or "/", parsed.query, parsed.fragment))


def parse_seed_urls(multiline: str) -> list[str]:
    """Parse, normalize, de-duplicate, and sort seed URLs from text."""
    normalized = [normalize_seed_url(line) for line in multiline.splitlines()]
    return sorted({url for url in normalized if url is not None})


def _utc_now_rfc3339() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _seed_rows(urls: list[str]) -> list[dict[str, Any]]:
    return [{"url": url, "description": None, "recipe_ids": []} for url in sorted(set(urls))]


def _normalize_seed_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized_url = normalize_seed_url(str(row.get("url", "")))
    if not normalized_url:
        raise ValueError("url is required")
    recipe_ids_raw = row.get("recipe_ids", [])
    recipe_ids = sorted({str(r).strip() for r in recipe_ids_raw if str(r).strip()}) if isinstance(recipe_ids_raw, list) else []
    description = row.get("description")
    if description is not None:
        description = str(description)
    return {"url": normalized_url, "description": description, "recipe_ids": recipe_ids}


def _seed_payload(domain: str, urls: list[str], updated_at: str | None = None) -> dict[str, Any]:
    return {
        "domain": domain,
        "updated_at": updated_at or _utc_now_rfc3339(),
        "urls": _seed_rows(urls),
    }


def validate_domain(domain: str) -> str:
    if not domain or any(char.isspace() for char in domain):
        raise ValueError("domain must be non-empty and contain no whitespace")
    return domain


def read_seed_urls(domain: str) -> dict[str, Any]:
    """Load persisted seed URLs or return empty payload when missing."""
    try:
        payload = storage.read_json_artifact(domain, "manual", "seed_urls.json")
    except Exception:
        return _seed_payload(domain, [])

    if not isinstance(payload, dict):
        return _seed_payload(domain, [])

    urls = payload.get("urls")
    updated_at = payload.get("updated_at")
    if not isinstance(urls, list) or not isinstance(updated_at, str):
        return _seed_payload(domain, [])

    normalized_urls: list[str] = []
    for row in urls:
        if isinstance(row, dict) and isinstance(row.get("url"), str):
            normalized_urls.append(str(row["url"]))
        else:
            return _seed_payload(domain, [])

    result = _seed_payload(domain, normalized_urls, updated_at=updated_at)
    validate_seed_urls_payload(result)
    return result


def write_seed_urls(domain: str, urls: list[str]) -> dict[str, Any]:
    """Persist full seed URL list under the fixed manual namespace."""
    payload = _seed_payload(domain, urls)
    validate_seed_urls_payload(payload)
    storage.write_json_artifact(domain, "manual", "seed_urls.json", payload)
    return payload


def write_seed_url_rows(domain: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    payload = {
        "domain": domain,
        "updated_at": _utc_now_rfc3339(),
        "urls": sorted([_normalize_seed_row(row) for row in rows], key=lambda r: r["url"]),
    }
    validate_seed_urls_payload(payload)
    storage.write_json_artifact(domain, "manual", "seed_urls.json", payload)
    return payload


def upsert_seed_url_row(domain: str, row: dict[str, Any]) -> dict[str, Any]:
    payload = read_seed_urls(domain)
    normalized = _normalize_seed_row(row)
    by_url = {
        str(existing.get("url")): _normalize_seed_row(existing)
        for existing in payload.get("urls", [])
        if isinstance(existing, dict) and existing.get("url")
    }
    by_url[normalized["url"]] = normalized
    return write_seed_url_rows(domain, list(by_url.values()))
