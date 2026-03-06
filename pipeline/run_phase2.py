"""Phase 2 runner — Annotation (template_rules) persistence.

Usage:
    python pipeline/run_phase2.py --domain example.com --run-id <run_id> \\
        --item-id <item_id> --url <url> --rule-type IGNORE_ENTIRE_ELEMENT

Reads existing template_rules from GCS (if any) and appends/updates the rule.
Outputs to GCS:
    gs://{ARTIFACTS_BUCKET}/{domain}/{run_id}/template_rules.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

project_root = str(Path(__file__).resolve().parents[1])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from pipeline.phase2_annotator import make_rule, ALLOWED_RULE_TYPES
from pipeline.storage import write_json_artifact, read_json_artifact
from pipeline.schema_validator import validate, SchemaValidationError


def run(
    domain: str,
    run_id: str,
    item_id: str,
    url: str,
    rule_type: str,
    note: str | None = None,
) -> dict:
    """Append or update a single rule in template_rules artifact.

    Per Contract §6 Phase 2: per element per URL, deterministic.
    """
    print(f"[Phase 2] Saving rule: item_id={item_id} url={url} rule_type={rule_type}")

    if rule_type not in ALLOWED_RULE_TYPES:
        print(f"[Phase 2] STOP: invalid rule_type={rule_type!r}", file=sys.stderr)
        sys.exit(1)

    # Load existing rules
    existing: list[dict] = []
    try:
        existing = read_json_artifact(domain, run_id, "template_rules.json")
    except Exception:
        existing = []

    new_rule = make_rule(item_id=item_id, url=url, rule_type=rule_type, note=note)

    # Remove any existing rule for the same (item_id, url) — last write wins
    updated = [
        r for r in existing
        if not (r["item_id"] == item_id and r["url"] == url)
    ]
    updated.append(new_rule)

    # Sort for determinism — Contract §1
    updated.sort(key=lambda r: (r["item_id"], r["url"], r["created_at"]))

    # Validate
    try:
        validate("template_rules", updated)
        print("[Phase 2] template_rules schema validation: PASSED")
    except SchemaValidationError as e:
        print(f"[Phase 2] STOP: {e}", file=sys.stderr)
        sys.exit(1)

    uri = write_json_artifact(domain, run_id, "template_rules.json", updated)
    print(f"[Phase 2] Wrote template_rules -> {uri} ({len(updated)} rules total)")
    return new_rule


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 2 — Annotation")
    parser.add_argument("--domain", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--item-id", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--rule-type", required=True, choices=sorted(ALLOWED_RULE_TYPES))
    parser.add_argument("--note", default=None)
    args = parser.parse_args()
    run(args.domain, args.run_id, args.item_id, args.url, args.rule_type, args.note)
