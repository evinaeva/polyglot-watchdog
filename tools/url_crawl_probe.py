#!/usr/bin/env python3
"""Lightweight URL crawl/probe utility for canonicalization analysis."""

from __future__ import annotations

import argparse
import json
import time
from collections import deque
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib import error, parse, request
from xml.etree import ElementTree


class LinkExtractor(HTMLParser):
    """Extract href values from anchor tags."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        for name, value in attrs:
            if name.lower() == "href" and value:
                self.links.append(value)


def remove_fragment(url: str) -> str:
    parsed = parse.urlsplit(url)
    return parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ""))


def classify_url(url: str, base_domain: str) -> tuple[bool, dict[str, str] | None]:
    parsed = parse.urlsplit(url)
    scheme = (parsed.scheme or "").lower()
    host = (parsed.hostname or "").lower()

    if scheme not in {"http", "https"}:
        return False, None

    if scheme != "https":
        return (
            False,
            {
                "url": url,
                "reason": "non_https_scheme",
                "expected_host": base_domain.lower(),
                "found_host": host,
                "found_scheme": scheme,
            },
        )

    if host != base_domain.lower():
        return False, None

    return True, None


def normalized_netloc(parsed: parse.SplitResult) -> str:
    auth = ""
    if parsed.username is not None:
        auth = parsed.username
        if parsed.password is not None:
            auth = f"{auth}:{parsed.password}"
        auth = f"{auth}@"

    host = (parsed.hostname or "").lower()
    port = f":{parsed.port}" if parsed.port is not None else ""
    return f"{auth}{host}{port}"


def fetch_links(url: str, timeout: float = 10.0) -> list[str]:
    req = request.Request(url, headers={"User-Agent": "polyglot-watchdog-url-crawl-probe/1.0"})
    with request.urlopen(req, timeout=timeout) as response:
        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type:
            return []
        payload = response.read().decode("utf-8", errors="ignore")

    parser = LinkExtractor()
    parser.feed(payload)
    return parser.links


def fetch_sitemap_urls(url: str, timeout: float = 10.0) -> list[str]:
    req = request.Request(url, headers={"User-Agent": "polyglot-watchdog-url-crawl-probe/1.0"})
    with request.urlopen(req, timeout=timeout) as response:
        payload = response.read().decode("utf-8", errors="ignore")

    root = ElementTree.fromstring(payload)
    loc_values: list[str] = []
    for element in root.iter():
        if element.tag.split("}")[-1] == "loc" and element.text:
            loc_values.append(element.text.strip())
    return loc_values


def is_excluded_tag_path(url: str) -> bool:
    parsed = parse.urlsplit(url)
    excluded_prefixes = (
        "/couples/tags/",
        "/female/tags/",
        "/male/tags/",
        "/tags/",
        "/trans/tags/",
    )
    return any(parsed.path.startswith(prefix) for prefix in excluded_prefixes)


def canonicalize_url(url: str) -> str:
    parsed = parse.urlsplit(remove_fragment(url))
    return parse.urlunsplit((parsed.scheme, normalized_netloc(parsed), parsed.path, parsed.query, ""))


def should_drop_pagination(url: str, ignore_prefix: str, ignore_param: str) -> bool:
    parsed = parse.urlsplit(url)
    if not parsed.path.startswith(ignore_prefix):
        return False
    query = parse.parse_qs(parsed.query, keep_blank_values=True)
    return ignore_param in query


def crawl(
    start_url: str,
    base_domain: str,
    max_pages: int,
    delay_s: float = 0.2,
) -> tuple[set[str], list[dict[str, str]]]:
    discovered: set[str] = set()
    strict_drop_map: dict[tuple[str, str, str, str, str], dict[str, str]] = {}

    sitemap_url = f"https://{base_domain.lower()}/basic-sitemap.xml"
    try:
        sitemap_urls = fetch_sitemap_urls(sitemap_url)
    except (error.URLError, ValueError, TimeoutError, ElementTree.ParseError):
        sitemap_urls = []

    for absolute in sitemap_urls[:max_pages]:
        allowed, drop_entry = classify_url(absolute, base_domain)
        if not allowed:
            if drop_entry is not None:
                key = (
                    drop_entry["url"],
                    drop_entry["reason"],
                    drop_entry["expected_host"],
                    drop_entry["found_host"],
                    drop_entry["found_scheme"],
                )
                strict_drop_map[key] = drop_entry
            continue

        no_fragment = remove_fragment(absolute)
        if is_excluded_tag_path(no_fragment):
            continue
        discovered.add(no_fragment)
        time.sleep(delay_s)

    strict_dropped = sorted(
        strict_drop_map.values(),
        key=lambda item: (
            item["url"],
            item["reason"],
            item["expected_host"],
            item["found_host"],
            item["found_scheme"],
        ),
    )
    return discovered, strict_dropped


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def build_canonical_inventory(
    raw_urls: Iterable[str],
    ignore_prefix: str,
    ignore_param: str,
) -> tuple[list[str], list[dict[str, str]]]:
    canonical_set: set[str] = set()
    dropped: list[dict[str, str]] = []

    for raw_url in raw_urls:
        canonical = canonicalize_url(raw_url)
        if should_drop_pagination(canonical, ignore_prefix, ignore_param):
            dropped.append(
                {
                    "url": canonical,
                    "reason": "pagination_param",
                    "matched_prefix": ignore_prefix,
                    "param": ignore_param,
                }
            )
            continue
        canonical_set.add(canonical)

    canonical_urls = sorted(canonical_set)
    dropped_sorted = sorted(
        dropped,
        key=lambda item: (
            item.get("url", ""),
            item.get("reason", ""),
            item.get("matched_prefix", ""),
            item.get("param", ""),
            item.get("expected_host", ""),
            item.get("found_host", ""),
            item.get("found_scheme", ""),
        ),
    )
    return canonical_urls, dropped_sorted


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Crawl a site and probe canonicalization effects.")
    parser.add_argument("--start-url", required=True)
    parser.add_argument("--base-domain", required=True)
    parser.add_argument("--max-pages", type=int, default=2000)
    parser.add_argument("--out-dir", default="output/crawl_probe")
    parser.add_argument("--pagination-ignore-prefix", required=True)
    parser.add_argument("--pagination-ignore-param", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    raw_set, strict_dropped = crawl(
        start_url=args.start_url,
        base_domain=args.base_domain,
        max_pages=args.max_pages,
    )
    raw_urls = sorted(raw_set)

    canonical_urls, pagination_dropped = build_canonical_inventory(
        raw_urls,
        ignore_prefix=args.pagination_ignore_prefix,
        ignore_param=args.pagination_ignore_param,
    )

    dropped = sorted(
        strict_dropped + pagination_dropped,
        key=lambda item: (
            item.get("url", ""),
            item.get("reason", ""),
            item.get("matched_prefix", ""),
            item.get("param", ""),
            item.get("expected_host", ""),
            item.get("found_host", ""),
            item.get("found_scheme", ""),
        ),
    )

    out_dir = Path(args.out_dir)
    write_json(
        out_dir / "raw_urls.json",
        {"start_url": args.start_url, "urls": raw_urls},
    )
    write_json(
        out_dir / "canonical_urls.json",
        {"start_url": args.start_url, "urls": canonical_urls},
    )
    write_json(
        out_dir / "drop_report.json",
        {
            "dropped": dropped,
            "stats": {
                "raw_count": len(raw_urls),
                "canonical_count": len(canonical_urls),
                "dropped_count": len(dropped),
            },
        },
    )


if __name__ == "__main__":
    main()
