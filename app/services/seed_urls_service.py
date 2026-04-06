from __future__ import annotations

from http import HTTPStatus

from app.seed_urls import normalize_seed_url, parse_seed_urls_with_errors, read_seed_urls, write_seed_rows, write_seed_urls


def get_seed_urls(*, domain: str) -> dict:
    return read_seed_urls(domain)


def put_seed_urls(*, domain: str, urls_multiline: str) -> dict:
    parsed_urls = parse_seed_urls_with_errors(urls_multiline)
    saved = write_seed_urls(domain, parsed_urls["urls"])
    saved["validation_errors"] = parsed_urls["errors"]
    return saved


def add_seed_urls(*, domain: str, urls_multiline: str) -> dict:
    parsed_urls = parse_seed_urls_with_errors(urls_multiline)
    incoming = parsed_urls["urls"]
    existing = read_seed_urls(domain)
    existing_urls = {str(row.get("url", "")) for row in existing.get("urls", []) if isinstance(row, dict) and row.get("url")}
    merged = sorted(existing_urls | set(incoming))
    saved = write_seed_urls(domain, merged)
    saved["validation_errors"] = parsed_urls["errors"]
    return saved


def delete_seed_url(*, domain: str, url: str) -> dict:
    normalized = normalize_seed_url(url)
    if normalized is None:
        raise ValueError("url is required")
    existing = read_seed_urls(domain)
    remaining = [
        str(row.get("url"))
        for row in existing.get("urls", [])
        if isinstance(row, dict) and row.get("url") and str(row.get("url")) != normalized
    ]
    return write_seed_urls(domain, remaining)


def clear_seed_urls(*, domain: str) -> dict:
    return write_seed_urls(domain, [])


def upsert_seed_row(*, domain: str, row: dict) -> dict:
    existing = read_seed_urls(domain)
    rows = [r for r in existing.get("urls", []) if isinstance(r, dict)]
    normalized_url = normalize_seed_url(str(row.get("url", "")))
    if normalized_url is None:
        raise ValueError("row.url is required")
    merged = [r for r in rows if str(r.get("url")) != normalized_url]
    merged.append({
        "url": normalized_url,
        "description": row.get("description"),
        "recipe_ids": row.get("recipe_ids", []),
        "active": bool(row.get("active", True)),
    })
    return write_seed_rows(domain, merged)
