"""Phase 6 runner — Localization QA issues generation.

Inputs:
- EN run artifacts: eligible_dataset.json, collected_items.json, page_screenshots.json
- Target run artifacts: eligible_dataset.json, collected_items.json, page_screenshots.json

Output:
- issues.json (schema: contract/schemas/issues.schema.json)
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

project_root = str(Path(__file__).resolve().parents[1])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from pipeline.phase5_normalizer import normalize_text
from pipeline.schema_validator import SchemaValidationError, validate
from pipeline.storage import read_json_artifact, write_json_artifact

_PLACEHOLDER_RE = re.compile(r"(%[^%]+%|\[[^\]]+\]|<[^>]+>)")


def _issue_id(category: str, en_item_id: str, target_url: str, message: str) -> str:
    raw = f"{category}|{en_item_id}|{target_url}|{message}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


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


def run(domain: str, en_run_id: str, target_run_id: str) -> list[dict]:
    en_eligible = read_json_artifact(domain, en_run_id, "eligible_dataset.json")
    target_eligible = read_json_artifact(domain, target_run_id, "eligible_dataset.json")

    en_collected = read_json_artifact(domain, en_run_id, "collected_items.json")
    target_collected = read_json_artifact(domain, target_run_id, "collected_items.json")

    en_screens = read_json_artifact(domain, en_run_id, "page_screenshots.json")
    target_screens = read_json_artifact(domain, target_run_id, "page_screenshots.json")

    en_by_item = {i["item_id"]: i for i in en_eligible if i.get("language") == "en"}
    target_by_item = {i["item_id"]: i for i in target_eligible if i.get("language") != "en"}
    target_collected_by_item = _index_collected(target_collected)
    target_screens_by_page = _index_screenshots(target_screens)

    issues: list[dict] = []

    for item_id in sorted(en_by_item.keys()):
        en_item = en_by_item[item_id]
        t_item = target_by_item.get(item_id)

        en_text = normalize_text(en_item.get("text", ""))

        if not t_item:
            evidence = {
                "url": en_item.get("url", ""),
                "bbox": _index_collected(en_collected).get(item_id, {}).get("bbox", {"x": 0, "y": 0, "width": 0, "height": 0}),
                "storage_uri": _index_screenshots(en_screens).get(en_item.get("page_id"), {}).get("storage_uri", ""),
                "item_id": item_id,
            }
            msg = "Missing target element for EN reference item"
            issues.append({
                "id": _issue_id("OTHER", item_id, en_item.get("url", ""), msg),
                "category": "OTHER",
                "confidence": 0.95,
                "message": msg,
                "evidence": evidence,
            })
            continue

        t_text = normalize_text(t_item.get("text", ""))
        evidence = _build_evidence(t_item, target_collected_by_item, target_screens_by_page)

        en_placeholders = sorted(_PLACEHOLDER_RE.findall(en_text))
        t_placeholders = sorted(_PLACEHOLDER_RE.findall(t_text))
        if en_placeholders != t_placeholders:
            msg = "Placeholder tokens differ between EN and target text"
            issues.append({
                "id": _issue_id("PLACEHOLDER", item_id, t_item["url"], msg),
                "category": "PLACEHOLDER",
                "confidence": 0.9,
                "message": msg,
                "evidence": evidence,
            })

        if en_text and t_text and en_text == t_text and not en_placeholders:
            msg = "Target text appears untranslated (identical to EN)"
            issues.append({
                "id": _issue_id("MEANING", item_id, t_item["url"], msg),
                "category": "MEANING",
                "confidence": 0.7,
                "message": msg,
                "evidence": evidence,
            })

    issues.sort(key=lambda i: (i["category"], i["id"]))

    try:
        validate("issues", issues)
    except SchemaValidationError as e:
        print(f"STOP: {e}", file=sys.stderr)
        sys.exit(1)

    write_json_artifact(domain, target_run_id, "issues.json", issues)
    return issues


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 6 — Localization QA")
    parser.add_argument("--domain", required=True)
    parser.add_argument("--en-run-id", required=True)
    parser.add_argument("--target-run-id", required=True)
    args = parser.parse_args()
    run(args.domain, args.en_run_id, args.target_run_id)
