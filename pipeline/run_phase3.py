"""Phase 3 runner — Filtered Rescan / EN Reference Build.

Usage:
    python pipeline/run_phase3.py --domain example.com --run-id <run_id>

Reads from GCS:
    collected_items.json (Phase 1 output)
    template_rules.json  (Phase 2 output, optional — empty = no filtering)

Outputs to GCS:
    gs://{ARTIFACTS_BUCKET}/{domain}/{run_id}/eligible_dataset.json
    gs://{ARTIFACTS_BUCKET}/{domain}/{run_id}/phase3_created_at.txt

Contract: contract/watchdog_contract_v1.0.md §6 Phase 3
Schema: contract/schemas/eligible_dataset.schema.json

Rules:
  - Derived deterministically from collected_items + template_rules (Filter-only mode).
  - EN reference creation time MUST be recorded.
"""

from __future__ import annotations

import argparse
import datetime
import sys
from pathlib import Path

project_root = str(Path(__file__).resolve().parents[1])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from pipeline.phase2_annotator import filter_items_by_rules
from pipeline.storage import write_json_artifact, write_text_artifact, read_json_artifact
from pipeline.schema_validator import validate, SchemaValidationError


def run(domain: str, run_id: str) -> list[dict]:
    """Build eligible_dataset from collected_items + template_rules.

    Contract §6 Phase 3: deterministic filter-only mode.
    """
    print(f"[Phase 3] Starting EN Reference Build domain={domain} run_id={run_id}")

    # Load collected_items
    try:
        collected_items = read_json_artifact(domain, run_id, "collected_items.json")
    except Exception as e:
        print(f"[Phase 3] STOP: Cannot read collected_items — {e}", file=sys.stderr)
        sys.exit(1)

    # Load template_rules (optional)
    template_rules: list[dict] = []
    try:
        template_rules = read_json_artifact(domain, run_id, "template_rules.json")
        print(f"[Phase 3] Loaded {len(template_rules)} template_rules")
    except Exception:
        print("[Phase 3] No template_rules found — proceeding without filtering")

    # Apply rules — Contract §6 Phase 3
    eligible_dataset = filter_items_by_rules(collected_items, template_rules)
    print(f"[Phase 3] eligible_dataset: {len(eligible_dataset)} items (from {len(collected_items)} collected)")

    # Schema validation gate — SPEC_LOCK §3
    try:
        validate("eligible_dataset", eligible_dataset)
        print("[Phase 3] eligible_dataset schema validation: PASSED")
    except SchemaValidationError as e:
        print(f"[Phase 3] STOP: {e}", file=sys.stderr)
        sys.exit(1)

    # Write artifacts
    uri = write_json_artifact(domain, run_id, "eligible_dataset.json", eligible_dataset)
    print(f"[Phase 3] Wrote eligible_dataset -> {uri}")

    # Record creation time — Contract §6 Phase 3
    created_at = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    write_text_artifact(domain, run_id, "phase3_created_at.txt", created_at)
    print(f"[Phase 3] EN reference created_at={created_at}")

    print(f"[Phase 3] Complete.")
    return eligible_dataset


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 3 — EN Reference Build")
    parser.add_argument("--domain", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    run(args.domain, args.run_id)
