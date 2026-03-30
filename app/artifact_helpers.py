from __future__ import annotations

import re
import sys
from urllib.parse import urlencode


def _read_json_safe(domain: str, run_id: str, filename: str, default):
    from pipeline.storage import read_json_artifact

    try:
        return read_json_artifact(domain, run_id, filename)
    except Exception as exc:
        print(f"[storage] read fallback domain={domain} run_id={run_id} file={filename}: {exc}", file=sys.stderr)
        return default


def _read_json_required(domain: str, run_id: str, filename: str):
    from pipeline.storage import read_json_artifact

    try:
        return read_json_artifact(domain, run_id, filename)
    except Exception as exc:
        raise ValueError(f"{filename} artifact_read_failed") from exc


def _read_list_artifact_required(domain: str, run_id: str, filename: str):
    payload = _read_json_required(domain, run_id, filename)
    if not isinstance(payload, list):
        raise ValueError(f"{filename} artifact_invalid")
    return payload


def _artifact_exists(domain: str, run_id: str, filename: str) -> bool:
    from pipeline.storage import artifact_path, list_run_artifacts

    try:
        return artifact_path(domain, run_id, filename) in list_run_artifacts(domain, run_id)
    except Exception as exc:
        print(
            f"[storage] exists_check fallback domain={domain} run_id={run_id} file={filename}: {exc}",
            file=sys.stderr,
        )
        return False


def _artifact_exists_strict(domain: str, run_id: str, filename: str) -> bool:
    from pipeline.storage import artifact_path, list_run_artifacts

    try:
        return artifact_path(domain, run_id, filename) in list_run_artifacts(domain, run_id)
    except Exception as exc:
        raise ValueError(f"{filename} artifact_read_failed") from exc


def _read_list_artifact_optional_strict(domain: str, run_id: str, filename: str):
    exists = _artifact_exists_strict(domain, run_id, filename)
    if not exists:
        return None
    payload = _read_json_required(domain, run_id, filename)
    if not isinstance(payload, list):
        raise ValueError(f"{filename} artifact_invalid")
    return payload


def _require_artifact_exists(domain: str, run_id: str, filename: str) -> None:
    if not _artifact_exists_strict(domain, run_id, filename):
        raise FileNotFoundError(f"{filename} artifact missing")


def _capture_artifacts_ready(domain: str, run_id: str) -> bool:
    return _artifact_exists(domain, run_id, "page_screenshots.json") and _artifact_exists(domain, run_id, "collected_items.json")


def _parse_gs_uri(uri: str) -> tuple[str, str] | None:
    text = str(uri or "").strip()
    match = re.match(r"^gs://([^/]+)/(.+)$", text)
    if not match:
        return None
    return match.group(1), match.group(2)


def _parse_http_uri(uri: str) -> str | None:
    text = str(uri or "").strip()
    if re.match(r"^https?://", text, flags=re.IGNORECASE):
        return text
    return None


def _read_json_artifact_from_gs_uri(uri: str):
    from pipeline.storage import read_json_artifact

    parsed_uri = _parse_gs_uri(uri)
    if not parsed_uri:
        raise ValueError("llm_input_artifact is not a valid gs:// URI")
    _, path = parsed_uri
    parts = path.rsplit("/", 2)
    if len(parts) != 3:
        raise ValueError("llm_input_artifact has invalid artifact path")
    domain, run_id, filename = parts
    return read_json_artifact(domain, run_id, filename)


def _not_ready_payload(artifact_base: str) -> dict:
    return {"error": f"{artifact_base} artifact missing", "status": "not_ready"}


def _structured_not_ready(action: str, error: str, *, previous_state: str = "not_ready", next_expected_state: str = "ready") -> dict:
    return {
        "status": "not_ready",
        "action": action,
        "error": error,
        "previous_state": previous_state,
        "resulting_state": "not_ready",
        "next_expected_state": next_expected_state,
        "remediation": ["complete prerequisite workflow step", "refresh workflow status", "resolve capture runner prerequisites"],
    }


def _page_screenshot_view_url(domain: str, run_id: str, page_id: str) -> str:
    query = urlencode({"domain": domain, "run_id": run_id, "page_id": page_id})
    return f"/api/page-screenshot?{query}"
