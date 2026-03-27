from __future__ import annotations

import datetime
import hashlib
import json
import time


def _require_query_params(query: dict[str, list[str]], *params: str) -> tuple[dict[str, str], list[str]]:
    values = {name: str(query.get(name, [""])[0]).strip() for name in params}
    missing = [name for name, value in values.items() if not value]
    return values, missing


def _missing_required_query_params(*missing: str) -> dict:
    return {"error": "missing_required_query_params", "missing": list(missing)}


def _validate_run_id(run_id: str) -> str:
    normalized = str(run_id or "").strip()
    if not normalized:
        raise ValueError("run_id required")
    if "/" in normalized or "\\" in normalized or ".." in normalized:
        raise ValueError("run_id contains invalid path-like segments")
    if any(ord(char) < 32 or ord(char) == 127 for char in normalized):
        raise ValueError("run_id contains control characters")
    return normalized


def _utc_now_rfc3339() -> str:
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _issue_sort_key(issue: dict) -> tuple[int, int, str]:
    raw = str(issue.get("id", "")).strip()
    if raw.isdigit():
        return (0, int(raw), raw)
    return (1, 0, raw)


def _as_int(value: object, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return default


def _as_float(value: object) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _as_bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    normalized = str(value or "").strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    return None


def _first_present(payload: dict, *keys: str):
    for key in keys:
        if key in payload and payload.get(key) is not None:
            return payload.get(key)
    return None


def _coalesce(*values: object):
    for value in values:
        if value is not None and str(value) != "":
            return value
    return None


def _stable_json_hash(payload: object) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _parse_utc_timestamp(value: str) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return time.mktime(time.strptime(text, "%Y-%m-%dT%H:%M:%SZ"))
    except ValueError:
        return None
