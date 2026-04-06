from __future__ import annotations

from typing import Any

from app.artifact_helpers import (
    _artifact_exists,
    _read_json_required,
    _read_json_safe,
    _read_list_artifact_optional_strict,
    _read_list_artifact_required,
    _require_artifact_exists,
    _read_json_artifact_from_gs_uri,
)
from pipeline import storage


def artifact_exists(domain: str, run_id: str, filename: str) -> bool:
    return _artifact_exists(domain, run_id, filename)


def require_artifact_exists(domain: str, run_id: str, filename: str) -> None:
    _require_artifact_exists(domain, run_id, filename)


def read_json_safe(domain: str, run_id: str, filename: str, default: Any) -> Any:
    return _read_json_safe(domain, run_id, filename, default)


def read_json_required(domain: str, run_id: str, filename: str) -> dict:
    return _read_json_required(domain, run_id, filename)


def read_list_required(domain: str, run_id: str, filename: str) -> list[dict]:
    return _read_list_artifact_required(domain, run_id, filename)


def read_list_optional_strict(domain: str, run_id: str, filename: str) -> list[dict] | None:
    return _read_list_artifact_optional_strict(domain, run_id, filename)


def read_json_from_gs_uri(uri: str) -> Any:
    return _read_json_artifact_from_gs_uri(uri)


def write_json_artifact(domain: str, run_id: str, filename: str, payload: Any) -> str:
    return storage.write_json_artifact(domain, run_id, filename, payload)
