"""Phase 1 — Data Collection for Polyglot Watchdog.

Contract: contract/watchdog_contract_v1.0.md §3, §6 Phase 1
Schemas:
  contract/schemas/page_screenshots.schema.json
  contract/schemas/collected_items.schema.json
  contract/schemas/universal_sections.schema.json

Key contract rules enforced:
  §3.1 — One full-page screenshot per capture context (url, viewport_kind, state, user_tier).
         Elements reference page_id, NOT screenshot directly.
         Per-element screenshots are FORBIDDEN.
  §3.4 — Stable item_id = sha1(domain + url + css_selector + bbox(x,y,w,h) + element_type).
         text MUST NOT be part of item_id.
  §6 Phase 1 — Double spaces MUST NOT be normalized.
               Numeric/price strings MUST NOT be excluded.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import uuid
from typing import Any


# ---------------------------------------------------------------------------
# Stable item_id — Contract §3.4
# ---------------------------------------------------------------------------

def compute_item_id(domain: str, url: str, css_selector: str, bbox: dict, element_type: str) -> str:
    """Return sha1-based stable item_id per Contract §3.4.

    item_id = sha1(domain + url + css_selector + bbox(x,y,width,height) + element_type)

    text MUST NOT be included.
    """
    payload = (
        domain
        + url
        + css_selector
        + str(bbox.get("x", 0))
        + str(bbox.get("y", 0))
        + str(bbox.get("width", 0))
        + str(bbox.get("height", 0))
        + element_type
    )
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# page_id generation
# ---------------------------------------------------------------------------

def compute_page_id(url: str, viewport_kind: str, state: str, user_tier: str | None) -> str:
    """Return stable page_id for a capture context.

    page_id = sha1(url + viewport_kind + state + (user_tier or ""))
    """
    payload = url + viewport_kind + state + (user_tier or "")
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# screenshot_id generation
# ---------------------------------------------------------------------------

def compute_screenshot_id(page_id: str) -> str:
    """Return screenshot_id derived from page_id."""
    return f"screenshot-{page_id}"


# ---------------------------------------------------------------------------
# Universal sections fingerprint — Contract §5
# ---------------------------------------------------------------------------

def compute_section_fingerprint(items: list[dict]) -> str:
    """Return deterministic fingerprint for a section's element set.

    Fingerprint = sha1 of sorted (css_selector, element_type, text) tuples.
    Stable — does not depend on order of items passed in.
    """
    key_tuples = sorted(
        (i.get("css_selector", ""), i.get("element_type", ""), i.get("text", ""))
        for i in items
    )
    raw = json.dumps(key_tuples, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Element extraction helpers
# ---------------------------------------------------------------------------

EXTRACTION_JS = """
() => {
  const results = [];
  const walker = document.createTreeWalker(
    document.body,
    NodeFilter.SHOW_ELEMENT,
    null
  );

  function getSelector(el) {
    // Best-effort stable selector: id > unique class > tag+nth
    if (el.id) return '#' + CSS.escape(el.id);
    const path = [];
    let current = el;
    while (current && current !== document.body) {
      let selector = current.tagName.toLowerCase();
      if (current.className && typeof current.className === 'string') {
        const classes = current.className.trim().split(/\\s+/).filter(Boolean);
        if (classes.length > 0) {
          selector += '.' + classes.map(c => CSS.escape(c)).join('.');
        }
      }
      const parent = current.parentElement;
      if (parent) {
        const siblings = Array.from(parent.children).filter(
          s => s.tagName === current.tagName
        );
        if (siblings.length > 1) {
          const idx = siblings.indexOf(current) + 1;
          selector += ':nth-of-type(' + idx + ')';
        }
      }
      path.unshift(selector);
      current = current.parentElement;
    }
    return path.join(' > ');
  }

  function getBbox(el) {
    const r = el.getBoundingClientRect();
    return { x: Math.round(r.left), y: Math.round(r.top), width: Math.round(r.width), height: Math.round(r.height) };
  }

  function isVisible(el) {
    const style = window.getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  }

  let node;
  while ((node = walker.nextNode())) {
    const tag = node.tagName.toLowerCase();

    // Collect text-bearing elements
    const text = (node.innerText || '').replace(/\\r\\n/g, '\\n');
    const trimmed = text.trim();
    // Do NOT skip numeric/price strings (Contract §6 Phase 1)
    // Do NOT normalize double spaces (Contract §6 Phase 1)
    if (trimmed && node.children.length === 0) {
      results.push({
        element_type: tag,
        tag: tag,
        css_selector: getSelector(node),
        bbox: getBbox(node),
        text: text,  // preserve double spaces
        visible: isVisible(node),
        attributes: null
      });
    }

    // Collect img elements
    if (tag === 'img') {
      const alt = node.getAttribute('alt') || '';
      const src = node.getAttribute('src') || '';
      results.push({
        element_type: 'img',
        tag: 'img',
        css_selector: getSelector(node),
        bbox: getBbox(node),
        text: alt,  // use alt as text for img
        visible: isVisible(node),
        attributes: { src: src, alt: alt }
      });
    }
  }
  return results;
}
"""


async def wait_for_capture_readiness(page, state: str) -> None:
    """Fail-fast readiness policy before extraction/bbox capture."""
    await page.wait_for_load_state("domcontentloaded", timeout=15000)
    await page.wait_for_load_state("networkidle", timeout=10000)
    await page.wait_for_selector("body", state="attached", timeout=5000)
    if state != "baseline":
        # Deterministic state-specific stabilization wait before bbox capture.
        await page.wait_for_timeout(200)


async def pull_page(
    page,  # Playwright Page object
    url: str,
    domain: str,
    viewport_kind: str,
    state: str,
    user_tier: str | None,
    language: str,
) -> tuple[dict, list[dict], bytes]:
    """Pull a single page and return (page_screenshot_record, collected_items, screenshot_bytes).

    Contract §3.1: exactly one full-page screenshot, elements reference page_id.
    Contract §3.4: stable item_id.
    """
    page_id = compute_page_id(url, viewport_kind, state, user_tier)
    screenshot_id = compute_screenshot_id(page_id)
    captured_at = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    # Navigate + deterministic readiness checks (fail-fast on timeout).
    await page.goto(url, timeout=30000)
    await wait_for_capture_readiness(page, state)

    # Extract elements via JS — Contract §3.1 (no per-element screenshots)
    raw_elements = await page.evaluate(EXTRACTION_JS)

    # Full-page screenshot — Contract §3.1 (one per capture context)
    screenshot_bytes = await page.screenshot(full_page=True)

    viewport = await page.evaluate(
        "() => ({ width: window.innerWidth, height: window.innerHeight })"
    )

    # Build page_screenshot record
    page_screenshot = {
        "page_id": page_id,
        "url": url,
        "viewport_kind": viewport_kind,
        "state": state,
        "user_tier": user_tier,
        "screenshot_id": screenshot_id,
        "storage_uri": "",  # filled in by caller after GCS upload
        "captured_at": captured_at,
        "viewport": {"width": viewport["width"], "height": viewport["height"]},
    }

    # Build collected_items
    items: list[dict] = []
    for el in raw_elements:
        css_selector = el.get("css_selector", "")
        bbox = el.get("bbox", {"x": 0, "y": 0, "width": 0, "height": 0})
        element_type = el.get("element_type", "")
        text = el.get("text", "")
        visible = el.get("visible", False)

        # stable item_id — Contract §3.4; text excluded
        item_id = compute_item_id(domain, url, css_selector, bbox, element_type)

        item = {
            "item_id": item_id,
            "page_id": page_id,  # reference page, NOT screenshot — Contract §3.1
            "url": url,
            "language": language,
            "viewport_kind": viewport_kind,
            "state": state,
            "user_tier": user_tier,
            "element_type": element_type,
            "css_selector": css_selector,
            "bbox": {
                "x": bbox.get("x", 0),
                "y": bbox.get("y", 0),
                "width": bbox.get("width", 0),
                "height": bbox.get("height", 0),
            },
            "text": text,  # double spaces preserved — Contract §6 Phase 1
            "visible": visible,
            "tag": el.get("tag"),
            "attributes": el.get("attributes"),
        }
        items.append(item)

    # Sort items for determinism — Contract §1 (stable ordering)
    items.sort(key=lambda i: (i["item_id"],))

    return page_screenshot, items, screenshot_bytes


# ---------------------------------------------------------------------------
# Universal sections detection — Contract §5
# ---------------------------------------------------------------------------

def detect_universal_sections(
    all_items_by_url: dict[str, list[dict]],
    representative_page_ids: dict[str, str],
    created_at: str,
) -> list[dict]:
    """Detect repeated identical sections (e.g. header/footer) across URLs.

    Contract §5:
    - fingerprint = deterministic content fingerprint.
    - representative = FIRST observed occurrence (by URL sort order).
    - EN only (caller responsibility).

    Returns list of universal_sections records (sorted by section_id).
    """
    # Group items by (css_selector, element_type) structural patterns
    # Simplified: detect sections where selector starts with header/footer/nav
    # and identical fingerprint across multiple URLs.
    section_patterns: dict[str, dict] = {}  # fingerprint -> section data

    sorted_urls = sorted(all_items_by_url.keys())

    for url in sorted_urls:
        items = all_items_by_url[url]
        # Group by top-level section tag hint
        for section_tag in ("header", "footer", "nav"):
            section_items = [
                i for i in items
                if i.get("element_type") == section_tag
                or i.get("css_selector", "").startswith(section_tag)
            ]
            if len(section_items) < 2:
                continue

            fingerprint = compute_section_fingerprint(section_items)
            if fingerprint not in section_patterns:
                # First occurrence = representative — Contract §5
                section_patterns[fingerprint] = {
                    "fingerprint": fingerprint,
                    "label": f"universal_{section_tag}",
                    "representative_url": url,
                    "representative_page_id": representative_page_ids.get(url, ""),
                    "member_urls": [url],
                    "member_urls_count": 1,
                    "created_at": created_at,
                }
            else:
                section_patterns[fingerprint]["member_urls"].append(url)
                section_patterns[fingerprint]["member_urls_count"] += 1

    # Keep only sections appearing on more than one URL
    multi_url_sections = [
        v for v in section_patterns.values() if v["member_urls_count"] > 1
    ]

    # Assign stable section_ids and sort — Contract §1
    result: list[dict] = []
    for sec in multi_url_sections:
        section_id = f"sec-{sec['fingerprint'][:16]}"
        result.append({
            "section_id": section_id,
            "label": sec["label"],
            "representative_url": sec["representative_url"],
            "representative_page_id": sec["representative_page_id"],
            "fingerprint": sec["fingerprint"],
            "member_urls_count": sec["member_urls_count"],
            "member_urls": sorted(sec["member_urls"]),
            "created_at": created_at,
        })

    result.sort(key=lambda s: s["section_id"])
    return result
