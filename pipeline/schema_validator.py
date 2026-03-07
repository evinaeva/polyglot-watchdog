"""Schema validation gate for Polyglot Watchdog artifacts.

Contract: SPEC_LOCK_EXECUTION_PROTOCOL.md §3
All emitted artifacts MUST validate against their authoritative schema.

This module provides validate() which raises SchemaValidationError
if an artifact does not conform.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import jsonschema  # type: ignore

# Authoritative schema directory — Contract §7
_SCHEMA_DIR = Path(__file__).resolve().parents[1] / "contract" / "schemas"

# Artifact name -> schema filename mapping — Contract §7
ARTIFACT_SCHEMAS: dict[str, str] = {
    "url_inventory": "url_inventory.schema.json",
    "url_rules": "url_rules.schema.json",
    "page_screenshots": "page_screenshots.schema.json",
    "collected_items": "collected_items.schema.json",
    "universal_sections": "universal_sections.schema.json",
    "template_rules": "template_rules.schema.json",
    "eligible_dataset": "eligible_dataset.schema.json",
    "issues": "issues.schema.json",
    "seed_urls": "seed_urls.schema.json",
}


class SchemaValidationError(Exception):
    """Raised when an artifact fails schema validation."""


def _load_schema(schema_filename: str) -> dict:
    schema_path = _SCHEMA_DIR / schema_filename
    if not schema_path.exists():
        raise SchemaValidationError(
            f"STOP: Schema file not found: {schema_path}. "
            "Cannot emit artifact without authoritative schema."
        )
    with schema_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate(artifact_name: str, data: object) -> None:
    """Validate data against the authoritative schema for artifact_name.

    Raises SchemaValidationError if validation fails.
    This is a hard stop per SPEC_LOCK_EXECUTION_PROTOCOL.md §2.
    """
    if artifact_name not in ARTIFACT_SCHEMAS:
        raise SchemaValidationError(
            f"STOP: Unknown artifact '{artifact_name}'. "
            f"Known artifacts: {sorted(ARTIFACT_SCHEMAS.keys())}"
        )
    schema = _load_schema(ARTIFACT_SCHEMAS[artifact_name])
    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as exc:
        raise SchemaValidationError(
            f"STOP: Artifact '{artifact_name}' failed schema validation: {exc.message}"
        ) from exc
