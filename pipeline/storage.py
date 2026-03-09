"""GCS artifact storage utilities for Polyglot Watchdog.

All artifact paths are deterministic and derived from:
  domain, run_id, artifact type.

Artifact layout in GCS:
  gs://{bucket}/{domain}/{run_id}/url_inventory.json
  gs://{bucket}/{domain}/{run_id}/url_rules.json
  gs://{bucket}/{domain}/{run_id}/page_screenshots.json
  gs://{bucket}/{domain}/{run_id}/collected_items.json
  gs://{bucket}/{domain}/{run_id}/universal_sections.json
  gs://{bucket}/{domain}/{run_id}/template_rules.json
  gs://{bucket}/{domain}/{run_id}/eligible_dataset.json
  gs://{bucket}/{domain}/{run_id}/phase3_created_at.txt
  gs://{bucket}/{domain}/{run_id}/screenshots/{page_id}.png

All JSON artifacts are serialized with sort_keys=True and ensure_ascii=False
for deterministic output — Contract §1.
"""

from __future__ import annotations

import json
import os
from typing import Any

from pipeline.schema_validator import validate

BUCKET_NAME = os.environ.get(
    "ARTIFACTS_BUCKET",
    "polyglot-watchdog-artifacts-1018698441568",
)


# Contract schema-gate applies only to normative v1.0 artifacts.
# Phase manifests are intentionally out-of-band until/if a dedicated manifest schema is introduced.
_ARTIFACT_NAME_BY_FILENAME = {
    "url_inventory.json": "url_inventory",
    "url_rules.json": "url_rules",
    "page_screenshots.json": "page_screenshots",
    "collected_items.json": "collected_items",
    "universal_sections.json": "universal_sections",
    "template_rules.json": "template_rules",
    "eligible_dataset.json": "eligible_dataset",
    "issues.json": "issues",
}


def _canonical_json_text(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def write_phase_manifest(domain: str, run_id: str, phase_name: str, manifest: dict[str, Any]) -> str:
    return write_json_artifact(domain, run_id, f"{phase_name}_manifest.json", manifest)


def _gcs_client():
    """Return authenticated GCS client."""
    from google.cloud import storage  # type: ignore
    return storage.Client()


def artifact_path(domain: str, run_id: str, filename: str) -> str:
    """Return GCS object path for a named artifact."""
    return f"{domain}/{run_id}/{filename}"


def screenshot_path(domain: str, run_id: str, page_id: str) -> str:
    """Return GCS object path for a screenshot."""
    return f"{domain}/{run_id}/screenshots/{page_id}.png"


def screenshot_uri(domain: str, run_id: str, page_id: str) -> str:
    """Return full gs:// URI for a screenshot."""
    return f"gs://{BUCKET_NAME}/{screenshot_path(domain, run_id, page_id)}"


def write_json_artifact(
    domain: str, run_id: str, filename: str, data: Any
) -> str:
    """Write JSON artifact to GCS. Returns gs:// URI."""
    client = _gcs_client()
    bucket = client.bucket(BUCKET_NAME)
    path = artifact_path(domain, run_id, filename)
    blob = bucket.blob(path)
    artifact_name = _ARTIFACT_NAME_BY_FILENAME.get(filename)
    if artifact_name is not None:
        validate(artifact_name, data)
    content = _canonical_json_text(data)
    blob.upload_from_string(content, content_type="application/json; charset=utf-8")
    return f"gs://{BUCKET_NAME}/{path}"


def write_text_artifact(
    domain: str, run_id: str, filename: str, text: str
) -> str:
    """Write plain text artifact to GCS. Returns gs:// URI."""
    client = _gcs_client()
    bucket = client.bucket(BUCKET_NAME)
    path = artifact_path(domain, run_id, filename)
    blob = bucket.blob(path)
    blob.upload_from_string(text.encode("utf-8"), content_type="text/plain; charset=utf-8")
    return f"gs://{BUCKET_NAME}/{path}"


def write_screenshot(
    domain: str, run_id: str, page_id: str, png_bytes: bytes
) -> str:
    """Write screenshot PNG to GCS. Returns gs:// URI."""
    client = _gcs_client()
    bucket = client.bucket(BUCKET_NAME)
    path = screenshot_path(domain, run_id, page_id)
    blob = bucket.blob(path)
    blob.upload_from_string(png_bytes, content_type="image/png")
    return f"gs://{BUCKET_NAME}/{path}"


def read_json_artifact(domain: str, run_id: str, filename: str) -> Any:
    """Read and parse a JSON artifact from GCS."""
    client = _gcs_client()
    bucket = client.bucket(BUCKET_NAME)
    path = artifact_path(domain, run_id, filename)
    blob = bucket.blob(path)
    content = blob.download_as_text(encoding="utf-8")
    return json.loads(content)


def list_run_artifacts(domain: str, run_id: str) -> list[str]:
    """List all GCS paths under domain/run_id/."""
    client = _gcs_client()
    bucket = client.bucket(BUCKET_NAME)
    prefix = f"{domain}/{run_id}/"
    blobs = bucket.list_blobs(prefix=prefix)
    return sorted(b.name for b in blobs)
