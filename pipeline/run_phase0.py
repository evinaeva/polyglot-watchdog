"""Phase 0 runner — URL Discovery.

Usage:
    python pipeline/run_phase0.py --domain example.com --run-id <run_id>

Outputs to GCS:
    gs://{ARTIFACTS_BUCKET}/{domain}/{run_id}/url_inventory.json
    gs://{ARTIFACTS_BUCKET}/{domain}/{run_id}/url_rules.json  (if --url-rules provided)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

project_root = str(Path(__file__).resolve().parents[1])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from pipeline.phase0_crawler import crawl_domain, build_url_inventory
from pipeline.storage import write_json_artifact, read_json_artifact
from pipeline.schema_validator import validate, SchemaValidationError


async def main(domain: str, run_id: str, url_rules_path: str | None) -> None:
    print(f"[Phase 0] Starting URL discovery for domain={domain} run_id={run_id}")

    # Load url_rules if provided
    url_rules_data: dict = {"version": "1.0", "rules": []}
    active_rules: list[dict] = []
    if url_rules_path:
        with open(url_rules_path, "r", encoding="utf-8") as f:
            url_rules_data = json.load(f)
        # Validate url_rules
        validate("url_rules", url_rules_data)
        from pipeline.phase0_crawler import load_drop_rules
        active_rules = load_drop_rules(url_rules_data)
        print(f"[Phase 0] Loaded {len(active_rules)} active DROP_URL rules")

    base_url = f"https://{domain}/"
    print(f"[Phase 0] Crawling from {base_url}")

    url_inventory = await crawl_domain(base_url, active_rules)
    print(f"[Phase 0] Discovered {len(url_inventory)} canonical URLs")

    # Schema validation gate — SPEC_LOCK §3
    try:
        validate("url_inventory", url_inventory)
        print("[Phase 0] url_inventory schema validation: PASSED")
    except SchemaValidationError as e:
        print(f"[Phase 0] STOP: {e}", file=sys.stderr)
        sys.exit(1)

    # Write artifacts to GCS
    uri = write_json_artifact(domain, run_id, "url_inventory.json", url_inventory)
    print(f"[Phase 0] Wrote url_inventory -> {uri}")

    if url_rules_path:
        uri2 = write_json_artifact(domain, run_id, "url_rules.json", url_rules_data)
        print(f"[Phase 0] Wrote url_rules -> {uri2}")

    print(f"[Phase 0] Complete. {len(url_inventory)} URLs in inventory.")
    return url_inventory


def run(domain: str, run_id: str, url_rules_path: str | None = None):
    return asyncio.run(main(domain, run_id, url_rules_path))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 0 — URL Discovery")
    parser.add_argument("--domain", required=True, help="EN base domain (e.g. example.com)")
    parser.add_argument("--run-id", required=True, help="Unique run identifier")
    parser.add_argument("--url-rules", default=None, help="Path to url_rules JSON file")
    args = parser.parse_args()
    run(args.domain, args.run_id, args.url_rules)
