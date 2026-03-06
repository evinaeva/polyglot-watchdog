"""Phase 0 — URL Discovery for Polyglot Watchdog.

Contract: contract/watchdog_contract_v1.0.md §4, §6 Phase 0
Schema:   contract/schemas/url_inventory.schema.json
          contract/schemas/url_rules.schema.json

Determinism guarantees:
- Output is sorted lexicographically (stable ordering).
- Canonicalization: strip fragment, normalize scheme to https.
- url_rules applied when present and enabled.
- No global query stripping.
- No global trailing-slash alteration.
- No global www alteration.
"""

from __future__ import annotations

import re
from urllib.parse import urldefrag, urlparse, urlunparse


# ---------------------------------------------------------------------------
# Canonicalization — Contract §4.1
# ---------------------------------------------------------------------------

def canonicalize_url(raw: str) -> str:
    """Return canonical form of url per Contract §4.1.

    Rules applied:
    1. Remove fragment (#...).
    2. Normalize scheme to https (merge http → https).

    Rules NOT applied (forbidden in v1.0):
    - No global query stripping.
    - No global trailing-slash alteration.
    - No global www alteration.
    """
    no_frag, _ = urldefrag(raw)
    parsed = urlparse(no_frag)
    if parsed.scheme in ("http", "https"):
        normalized = parsed._replace(scheme="https")
    else:
        normalized = parsed
    return urlunparse(normalized)


# ---------------------------------------------------------------------------
# URL Rules — Contract §4.2
# ---------------------------------------------------------------------------

def load_drop_rules(rules_json: dict) -> list[dict]:
    """Return list of enabled DROP_URL rules from url_rules artifact."""
    return [
        r for r in rules_json.get("rules", [])
        if r.get("enabled", False) and r.get("action") == "DROP_URL"
    ]


def url_is_dropped(url: str, rules: list[dict]) -> bool:
    """Return True if url matches any enabled DROP_URL rule.

    Match condition: path starts with rule.match.path_prefix AND
    the query string contains rule.match.query_param as a key.
    """
    parsed = urlparse(url)
    for rule in rules:
        match = rule.get("match", {})
        path_prefix = match.get("path_prefix", "")
        query_param = match.get("query_param", "")
        if not path_prefix or not query_param:
            continue
        if parsed.path.startswith(path_prefix):
            query = parsed.query
            params = re.split(r"[&;]", query) if query else []
            for p in params:
                key = p.split("=", 1)[0]
                if key == query_param:
                    return True
    return False


# ---------------------------------------------------------------------------
# Core Phase 0 function
# ---------------------------------------------------------------------------

def build_url_inventory(
    discovered_urls: list[str],
    domain: str,
    url_rules: list[dict] | None = None,
) -> list[str]:
    """Build deterministic url_inventory from raw discovered URLs.

    Args:
        discovered_urls: Raw URLs discovered by crawler.
        domain:          EN base domain (e.g. "example.com").
        url_rules:       Parsed list of enabled DROP_URL rules.

    Returns:
        Sorted, deduplicated, canonicalized list of URLs.
        This IS the url_inventory artifact (validated against
        contract/schemas/url_inventory.schema.json).
    """
    rules = url_rules or []
    seen: set[str] = set()
    result: list[str] = []

    for raw in discovered_urls:
        canonical = canonicalize_url(raw)
        parsed = urlparse(canonical)

        if parsed.netloc != domain:
            continue
        if parsed.scheme != "https":
            continue
        if url_is_dropped(canonical, rules):
            continue
        if canonical in seen:
            continue
        seen.add(canonical)
        result.append(canonical)

    result.sort()  # deterministic ordering — Contract §1
    return result


async def crawl_domain(base_url: str, url_rules: list[dict] | None = None) -> list[str]:
    """Crawl domain starting from base_url, returning url_inventory.

    Uses Playwright Chromium to follow same-domain links.
    Contract §4.1 canonicalization applied.
    Contract §4.2 url_rules applied.

    Returns deterministic url_inventory (sorted list of canonical URLs).
    """
    from playwright.async_api import async_playwright
    from urllib.parse import urljoin

    domain = urlparse(base_url).netloc
    if not domain:
        raise ValueError(f"Cannot extract domain from base_url: {base_url}")

    visited: set[str] = set()
    pending: list[str] = [canonicalize_url(base_url)]
    raw_discovered: list[str] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="polyglot-watchdog/1.0",
        )
        while pending:
            pending.sort()  # deterministic traversal order
            url = pending.pop(0)
            if url in visited:
                continue
            visited.add(url)
            raw_discovered.append(url)

            try:
                page = await context.new_page()
                await page.goto(url, timeout=30000)
                try:
                    await page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass
                links = await page.evaluate(
                    "Array.from(document.querySelectorAll('a[href]')).map(a => a.href)"
                )
                await page.close()
            except Exception:
                continue

            for link in links:
                if not link:
                    continue
                parsed = urlparse(link)
                if parsed.scheme not in ("http", "https"):
                    continue
                # Resolve relative URLs
                if not parsed.netloc:
                    link = urljoin(url, link)
                canonical_link = canonicalize_url(link)
                if urlparse(canonical_link).netloc != domain:
                    continue
                if canonical_link not in visited and canonical_link not in pending:
                    pending.append(canonical_link)

        await browser.close()

    return build_url_inventory(raw_discovered, domain, url_rules)
