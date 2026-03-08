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
    if not (value.startswith("http://") or value.startswith("https://")):
        value = f"https://{value}"
    parsed = urlsplit(value)
    lower_netloc = parsed.netloc.lower()
    return urlunsplit((parsed.scheme, lower_netloc, parsed.path, parsed.query, parsed.fragment))


def parse_seed_urls(multiline: str) -> list[str]:
    """Parse, normalize, de-duplicate, and sort seed URLs from text."""
    normalized = [normalize_seed_url(line) for line in multiline.splitlines()]
    return sorted({url for url in normalized if url is not None})


def _utc_now_rfc3339() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _seed_rows(urls: list[str]) -> list[dict[str, Any]]:
    return [{"url": url, "description": None, "recipe_ids": []} for url in sorted(set(urls))]


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
            normalized_urls.append(row["url"])
        elif isinstance(row, str):
            # TEMP_COMPAT: legacy flat-string seed_urls format.
            # Removal condition: drop this branch in PW-BL-017.
            normalized_urls.append(row)
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

