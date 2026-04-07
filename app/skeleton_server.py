"""Deterministic operator UI server for Polyglot Watchdog.

The repository is not a blank scaffold: core artifact-backed pipeline paths
and operator routes are implemented, while release readiness remains
pre-production and gated by documented criteria.

Some operator-visible flows are still incomplete or under pre-production
hardening and must not be presented as production-ready.
"""

from __future__ import annotations

import datetime
import html
import json
import os
import re
import asyncio
import base64
import hashlib
import hmac
import secrets
import sys
import threading
import time
import traceback
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from zoneinfo import ZoneInfo

# Ensure project root is on sys.path for pipeline imports
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.recipes import delete_recipe, list_recipes, upsert_recipe, load_recipes_for_planner
from app.artifact_helpers import (
    _artifact_exists,
    _artifact_exists_strict,
    _capture_artifacts_ready,
    _not_ready_payload,
    _page_screenshot_view_url,
    _parse_gs_uri,
    _parse_http_uri,
    _read_json_artifact_from_gs_uri,
    _read_json_required,
    _read_json_safe,
    _read_list_artifact_optional_strict,
    _read_list_artifact_required,
    _require_artifact_exists,
    _structured_not_ready,
)
from app.seed_urls import (
    normalize_seed_url,
    parse_seed_urls,
    parse_seed_urls_with_errors,
    read_seed_urls,
    validate_domain,
    write_seed_rows,
    write_seed_urls,
)
from app.server_utils import (
    _as_bool,
    _as_float,
    _as_int,
    _coalesce,
    _first_present,
    _issue_sort_key,
    _missing_required_query_params,
    _parse_utc_timestamp,
    _require_query_params,
    _stable_json_hash,
    _utc_now_rfc3339,
    _validate_run_id,
)
from app.whitelist_utils import (
    _add_domain_element_type_whitelist,
    _load_domain_element_type_whitelist,
    _normalize_whitelist_entry,
    _remove_domain_element_type_whitelist,
    _row_matches_whitelist,
    _save_domain_element_type_whitelist,
)
from app.issues_utils import (
    _estimate_severity,
    _filter_issues,
    _format_summary_pairs,
    _issues_to_csv,
    _summarize_issues_payload,
)
from app.check_languages_service import (
    CANONICAL_TARGET_LANGUAGES,
    GITHUB_PAGES_TESTSITE_CANONICAL_DOMAIN,
    GITHUB_PAGES_TESTSITE_LEGACY_ROOT_DOMAIN,
    GITHUB_PAGES_TESTSITE_PROJECT_PREFIX,
    NORMAL_CHECK_LANGUAGE_DOMAINS,
    SUPPORTED_CHECK_LANGUAGE_DOMAINS,
    _build_check_languages_target_url,
    _build_exception_diagnostics,
    _check_languages_payload_status,
    _check_languages_llm_review_telemetry_status,
    _check_languages_llm_request_artifact_status,
    _check_languages_source_hashes,
    _check_languages_site_family_key,
    _check_languages_llm_input_artifact_status,
    _check_languages_run_domains as _service_check_languages_run_domains,
    _default_english_reference_run_id,
    _find_in_progress_check_languages_job as _service_find_in_progress_check_languages_job,
    _generate_target_run_id as _service_generate_target_run_id,
    _is_english_language,
    _is_missing_artifact_error,
    _is_special_check_languages_test_domain,
    _is_supported_check_languages_domain,
    _latest_check_languages_job as _service_latest_check_languages_job,
    _latest_successful_en_standard_run_id,
    _load_check_language_runs as _service_load_check_language_runs,
    _load_target_languages,
    _normalize_check_languages_domain,
    _normalize_testsite_domain_key,
    _normalize_optional_string,
    _normalize_target_language,
    _parse_github_pages_project_language_url,
    _parse_gs_uri_safe,
    _persist_check_languages_failure_artifacts_safe,
    _phase6_artifact_readiness,
    _replay_scope_from_reference_run,
    _replay_unit_diagnostics,
    _resolve_check_languages_domain,
    _run_display_label,
    _run_has_en_standard_success_marker,
    _run_is_en_reference_candidate,
    _run_is_english_only,
    _run_is_explicit_en_reference,
    _run_languages,
    _target_capture_url_from_reference_url,
)
from app.check_languages_presenter import _h, _llm_review_display
from app import check_languages_ui
from app.testbench import get_modules, run_module_test
from pipeline import storage
from pipeline.runtime_config import validate_seed_urls_payload, load_phase1_runtime_config
from pipeline.interactive_capture import GCSArtifactWriter

TEMPLATES_DIR = BASE_DIR / "web" / "templates"
STATIC_DIR = BASE_DIR / "web" / "static"
FIXTURE_DIR = STATIC_DIR / "watchdog-fixture"

SESSION_COOKIE = "pw_session"
CSRF_COOKIE = "pw_csrf"
WATCHDOG_PASSWORD_ENV = "WATCHDOG_PASSWORD"
SESSION_SIGNING_SECRET_ENV = "SESSION_SIGNING_SECRET"
AUTH_MODE = "OFF"
SESSION_MAX_AGE_SECONDS = max(int(os.environ.get("SESSION_MAX_AGE_SECONDS", "28800")), 300)


# In-memory job status store (cleared on restart — for UI feedback only)
_jobs: dict[str, dict] = {}
_template_cache: dict[Path, tuple[int, str]] = {}
_TALLINN_TZ = ZoneInfo("Europe/Tallinn")


def _strip_json5_comments(source: str) -> str:
    result: list[str] = []
    index = 0
    in_string = False
    quote_char = ""
    escaped = False
    length = len(source)
    while index < length:
        char = source[index]
        nxt = source[index + 1] if index + 1 < length else ""
        if in_string:
            result.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote_char:
                in_string = False
            index += 1
            continue
        if char in {'"', "'"}:
            in_string = True
            quote_char = char
            result.append(char)
            index += 1
            continue
        if char == "/" and nxt == "/":
            index += 2
            while index < length and source[index] not in {"\n", "\r"}:
                index += 1
            continue
        if char == "/" and nxt == "*":
            index += 2
            while index + 1 < length and not (source[index] == "*" and source[index + 1] == "/"):
                index += 1
            index += 2
            continue
        result.append(char)
        index += 1
    return "".join(result)


def _parse_json_or_json5(raw: bytes) -> dict:
    text = raw.decode("utf-8-sig")
    parsed = json.loads(text)
    if isinstance(parsed, dict):
        return parsed
    raise ValueError("recipe file must contain a JSON object")


def _parse_json_or_json5_safe(raw: bytes) -> dict:
    """Parse JSON with limited JSON5 compatibility (comments + trailing commas only)."""
    try:
        return _parse_json_or_json5(raw)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        pass
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("invalid JSON/JSON5 payload") from exc
    without_comments = _strip_json5_comments(text)
    cleaned = re.sub(r",(\s*[}\]])", r"\1", without_comments)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError("invalid JSON/JSON5 payload") from exc
    if isinstance(parsed, dict):
        return parsed
    raise ValueError("recipe file must contain a JSON object")


def _compat_recipe_for_storage(raw_recipe: dict) -> dict:
    """Create a storage-compatibility copy without mutating the uploaded source payload."""
    compat = dict(raw_recipe)
    if not isinstance(compat.get("url_pattern"), str):
        compat["url_pattern"] = str(compat.get("url_pattern", "") or "")
    if not str(compat.get("url_pattern", "")).strip():
        compat["url_pattern"] = "*"
    steps = compat.get("steps", [])
    compat["steps"] = list(steps) if isinstance(steps, list) else []
    capture_points = compat.get("capture_points", [])
    compat["capture_points"] = list(capture_points) if isinstance(capture_points, list) else []
    return compat


def _write_seed_rows_preserve_order(domain: str, rows: list[dict]) -> dict:
    updated_at = _utc_now_rfc3339()
    contract_payload = {
        "domain": domain,
        "updated_at": updated_at,
        "urls": [
            {
                "url": row["url"],
                "description": row.get("description"),
                "recipe_ids": list(row.get("recipe_ids", [])),
            }
            for row in rows
        ],
    }
    validate_seed_urls_payload(contract_payload)
    storage.write_json_artifact(domain, "manual", "seed_urls.json", contract_payload)
    storage.write_json_artifact(
        domain,
        "manual",
        "seed_url_states.json",
        {
            "updated_at": updated_at,
            "states": [{"url": row["url"], "active": bool(row.get("active", True))} for row in rows],
        },
    )
    return {"domain": domain, "updated_at": updated_at, "urls": rows}


def _check_languages_run_domains(value: str) -> list[str]:
    return _service_check_languages_run_domains(value, _list_domains)


def _load_check_language_runs(domain: str) -> list[dict]:
    return _service_load_check_language_runs(domain, load_runs=_load_runs, list_domains=_list_domains)


def _default_check_languages_domain() -> str:
    candidates: list[tuple[str, str]] = []
    for raw_domain in _list_domains():
        domain = _normalize_check_languages_domain(raw_domain)
        if not domain or not _is_supported_check_languages_domain(domain):
            continue
        runs = _load_check_language_runs(domain)
        en_candidates = [row for row in runs if _run_is_en_reference_candidate(row)]
        selected_en_run_id = _latest_successful_en_standard_run_id(domain, en_candidates) or _default_english_reference_run_id(en_candidates)
        if not selected_en_run_id:
            continue
        run = next((row for row in en_candidates if str(row.get("run_id", "")).strip() == selected_en_run_id), None)
        created_at = str((run or {}).get("created_at", "")).strip()
        candidates.append((created_at, domain))
    if candidates:
        candidates.sort(reverse=True)
        return candidates[0][1]
    return SUPPORTED_CHECK_LANGUAGE_DOMAINS[0]


def _generate_target_run_id(domain: str, en_run_id: str, target_language: str) -> str:
    return _service_generate_target_run_id(domain, en_run_id, target_language, load_runs=_load_runs, list_domains=_list_domains)


def _find_in_progress_check_languages_job(domain: str, en_run_id: str, target_language: str) -> dict | None:
    return _service_find_in_progress_check_languages_job(
        domain,
        en_run_id,
        target_language,
        load_runs=_load_runs,
        list_domains=_list_domains,
        as_stale_failed_job=_as_stale_failed_job,
        is_stale_running_job=_is_stale_running_job,
    )


def _latest_check_languages_job(domain: str, run_id: str) -> dict | None:
    return _service_latest_check_languages_job(
        domain,
        run_id,
        load_runs=_load_runs,
        list_domains=_list_domains,
        as_stale_failed_job=_as_stale_failed_job,
        is_stale_running_job=_is_stale_running_job,
    )


def _latest_phase6_job(domain: str, run_id: str) -> dict | None:
    runs_payload = _load_runs(domain)
    runs = runs_payload.get("runs", []) if isinstance(runs_payload, dict) else []
    run = next((r for r in runs if isinstance(r, dict) and str(r.get("run_id", "")) == run_id), None)
    if not isinstance(run, dict):
        return None
    jobs = run.get("jobs", []) if isinstance(run.get("jobs", []), list) else []
    phase6_jobs: list[dict] = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        if str(job.get("phase", "")).strip() == "6" or str(job.get("type", "")).strip() == "issues" or str(job.get("job_id", "")).startswith("phase6-"):
            phase6_jobs.append(_as_stale_failed_job(job) if _is_stale_running_job(job) else dict(job))
    if not phase6_jobs:
        return None
    phase6_jobs.sort(key=lambda row: (str(row.get("updated_at", "")), str(row.get("created_at", "")), str(row.get("job_id", ""))))
    return phase6_jobs[-1]


def _latest_phase3_job(domain: str, run_id: str) -> dict | None:
    runs_payload = _load_runs(domain)
    runs = runs_payload.get("runs", []) if isinstance(runs_payload, dict) else []
    run = next((r for r in runs if isinstance(r, dict) and str(r.get("run_id", "")) == run_id), None)
    if not isinstance(run, dict):
        return None
    jobs = run.get("jobs", []) if isinstance(run.get("jobs", []), list) else []
    phase3_jobs: list[dict] = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        if str(job.get("phase", "")).strip() == "3" or str(job.get("type", "")).strip() == "eligible_dataset" or str(job.get("job_id", "")).startswith("phase3-"):
            phase3_jobs.append(_as_stale_failed_job(job) if _is_stale_running_job(job) else dict(job))
    if not phase3_jobs:
        return None
    phase3_jobs.sort(key=lambda row: (str(row.get("updated_at", "")), str(row.get("created_at", "")), str(row.get("job_id", ""))))
    return phase3_jobs[-1]


def _capture_context_id_from_page(domain: str, page: dict) -> str:
    from pipeline.interactive_capture import CaptureContext, build_capture_context_id

    ctx = CaptureContext(
        domain=domain,
        url=str(page.get("url", "")),
        language=str(page.get("language", "")),
        viewport_kind=str(page.get("viewport_kind", "")),
        state=str(page.get("state", "")),
        user_tier=page.get("user_tier") or None,
    )
    return build_capture_context_id(ctx)


def _to_rule_type(decision: str) -> str:
    value = str(decision or "").strip().lower()
    mapping = {
        "eligible": "ALWAYS_COLLECT",
        "exclude": "IGNORE_ENTIRE_ELEMENT",
        "needs-fix": "MASK_VARIABLE",
    }
    return mapping.get(value, decision)
def _list_domains() -> list[str]:
    from pipeline.storage import write_json_artifact

    payload = _read_json_safe("_system", "manual", "domains.json", {"domains": []})
    values = payload.get("domains") if isinstance(payload, dict) else []
    normalized: set[str] = set()
    for raw in values:
        value = _normalize_testsite_domain_key(str(raw).strip())
        if not value:
            continue
        try:
            normalized.add(validate_domain(value))
        except ValueError:
            continue
    cleaned = sorted(normalized)
    if isinstance(payload, dict) and payload.get("domains") != cleaned:
        write_json_artifact("_system", "manual", "domains.json", {"domains": cleaned})
    return cleaned


def _register_domain(domain: str) -> None:
    from pipeline.storage import write_json_artifact

    domain = validate_domain(_normalize_testsite_domain_key(domain))
    domains = set(_list_domains())
    domains.add(domain)
    write_json_artifact("_system", "manual", "domains.json", {"domains": sorted(domains)})


def _read_urls_page_state() -> dict:
    payload = _read_json_safe("_system", "manual", "urls_page_state.json", {})
    if not isinstance(payload, dict):
        return {}
    return payload


def _last_used_first_run_domain() -> str:
    from pipeline.storage import write_json_artifact

    payload = _read_urls_page_state()
    raw_value = _normalize_testsite_domain_key(str(payload.get("last_used_first_run_domain", "")).strip())
    try:
        return validate_domain(raw_value)
    except ValueError:
        if isinstance(payload, dict) and payload.get("last_used_first_run_domain"):
            payload["last_used_first_run_domain"] = ""
            write_json_artifact("_system", "manual", "urls_page_state.json", payload)
        return ""


def _set_last_used_first_run_domain(domain: str) -> None:
    from pipeline.storage import write_json_artifact

    valid_domain = validate_domain(_normalize_testsite_domain_key(domain))
    payload = _read_urls_page_state()
    payload["last_used_first_run_domain"] = valid_domain
    write_json_artifact("_system", "manual", "urls_page_state.json", payload)
    _register_domain(valid_domain)


def _load_runs(domain: str) -> dict:
    payload = _read_json_safe(domain, "manual", "capture_runs.json", {"runs": []})
    if not isinstance(payload, dict) or not isinstance(payload.get("runs"), list):
        return {"runs": []}
    return payload


def _sort_runs_newest_first(runs: list[dict]) -> list[dict]:
    def sort_key(run: dict) -> tuple[float, str]:
        created_ts = _parse_utc_timestamp(str((run or {}).get("created_at", "")))
        run_id = str((run or {}).get("run_id", ""))
        return (created_ts if created_ts is not None else float("-inf"), run_id)

    return sorted(
        (row for row in runs if isinstance(row, dict)),
        key=sort_key,
        reverse=True,
    )


def _persisted_issue_results_payload(domain: str) -> dict[str, Any]:
    run_domains = _check_languages_run_domains(domain) or [domain]
    run_rows_by_key: dict[tuple[str, str], dict] = {}
    results_by_key: dict[tuple[str, str], dict] = {}
    diagnostics = {
        "requested_domain": domain,
        "searched_domains": run_domains,
        "manifest_runs_scanned": 0,
        "artifact_fallback_runs_scanned": 0,
    }

    def upsert_result(row: dict, *, source: str) -> None:
        row_domain = str((row or {}).get("domain", "")).strip()
        run_id = str((row or {}).get("run_id", "")).strip()
        if not row_domain or not run_id:
            return
        result_key = (row_domain, run_id)
        created_at = str((row or {}).get("created_at", "")).strip()
        current = results_by_key.get(result_key)
        if current is None:
            out = dict(row)
            out["result_key"] = f"{row_domain}|{run_id}"
            out["source"] = source
            results_by_key[result_key] = out
            return
        current_ts = _parse_utc_timestamp(str(current.get("created_at", ""))) or float("-inf")
        candidate_ts = _parse_utc_timestamp(created_at) or float("-inf")
        if candidate_ts > current_ts:
            out = dict(row)
            out["result_key"] = f"{row_domain}|{run_id}"
            out["source"] = source
            results_by_key[result_key] = out

    for run_domain in run_domains:
        runs_payload = _load_runs(run_domain)
        runs = runs_payload.get("runs", []) if isinstance(runs_payload, dict) else []
        diagnostics["manifest_runs_scanned"] += len([row for row in runs if isinstance(row, dict)])
        for run in _sort_runs_newest_first(runs):
            run_id = str((run or {}).get("run_id", "")).strip()
            if not run_id:
                continue
            run_rows_by_key[(run_domain, run_id)] = run
            if not _artifact_exists(run_domain, run_id, "issues.json"):
                continue
            upsert_result({
                "domain": run_domain,
                "run_id": run_id,
                "created_at": str((run or {}).get("created_at", "")).strip(),
                "display_label": _run_display_label(run),
            }, source="manifest")
    try:
        from pipeline.storage import _gcs_client

        bucket = _gcs_client().bucket(storage.BUCKET_NAME)
        for run_domain in run_domains:
            prefix = f"{run_domain}/"
            suffix = "/issues.json"
            for blob in bucket.list_blobs(prefix=prefix):
                name = str(getattr(blob, "name", "") or "")
                if not name.startswith(prefix) or not name.endswith(suffix):
                    continue
                run_id = name[len(prefix): -len(suffix)].strip()
                if not run_id or "/" in run_id:
                    continue
                diagnostics["artifact_fallback_runs_scanned"] += 1
                run = run_rows_by_key.get((run_domain, run_id), {})
                created_at = str((run or {}).get("created_at", "")).strip()
                if not created_at:
                    updated = getattr(blob, "updated", None)
                    if isinstance(updated, datetime.datetime):
                        created_at = updated.astimezone(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
                discovered_label = f"Artifact run · {run_id}"
                if created_at:
                    discovered_label = f"Artifact run ({created_at}) · {run_id}"
                run_label = _run_display_label(run) if isinstance(run, dict) else ""
                upsert_result({
                    "domain": run_domain,
                    "run_id": run_id,
                    "created_at": created_at,
                    "display_label": run_label or discovered_label,
                }, source="artifact_fallback")
    except Exception:
        pass
    results = [row for row in results_by_key.values() if isinstance(row, dict) and str(row.get("run_id", "")).strip()]
    results.sort(
        key=lambda row: (
            -(_parse_utc_timestamp(str(row.get("created_at", ""))) or float("-inf")),
            str(row.get("run_id", "")),
        )
    )
    return {"results": results, "diagnostics": diagnostics}


def _list_persisted_issue_results(domain: str) -> list[dict]:
    return _persisted_issue_results_payload(domain)["results"]


def _infer_target_language_for_run(domain: str, run_id: str, query_language: str = "") -> str:
    explicit = _normalize_target_language(str(query_language or "").strip())
    if explicit:
        return explicit
    runs_payload = _load_runs(domain)
    runs = runs_payload.get("runs", []) if isinstance(runs_payload, dict) else []
    run = next((row for row in runs if isinstance(row, dict) and str(row.get("run_id", "")).strip() == run_id), None)
    if not isinstance(run, dict):
        run = {}
    direct = _normalize_target_language(str(run.get("target_language", "")).strip())
    if direct:
        return direct
    jobs = run.get("jobs", [])
    if isinstance(jobs, list):
        for job in reversed(jobs):
            if not isinstance(job, dict):
                continue
            value = _normalize_target_language(str(job.get("target_language", "")).strip())
            if value:
                return value
    issues = _read_json_safe(domain, run_id, "issues.json", [])
    if isinstance(issues, list):
        candidates: dict[str, int] = {}
        for issue in issues:
            if not isinstance(issue, dict):
                continue
            evidence = issue.get("evidence", {}) if isinstance(issue.get("evidence"), dict) else {}
            raw = (
                str(issue.get("language", "") or issue.get("target_language", "") or issue.get("lang", "")).strip()
                or str(evidence.get("language", "") or evidence.get("target_language", "") or evidence.get("lang", "")).strip()
            )
            normalized = _normalize_target_language(raw)
            if normalized:
                candidates[normalized] = candidates.get(normalized, 0) + 1
        if candidates:
            return sorted(candidates.items(), key=lambda item: (-item[1], item[0]))[0][0]
    return ""


def _result_file_artifact_status(domain: str, run_id: str, filename: str) -> dict[str, Any]:
    status = "missing"
    payload: Any = None
    error = ""
    try:
        payload = storage.read_json_artifact(domain, run_id, filename)
        status = "valid"
    except json.JSONDecodeError as exc:
        status = "malformed"
        error = str(exc)
    except Exception as exc:
        status = "missing" if _is_missing_artifact_error(exc) else "read_error"
        error = "" if status == "missing" else str(exc)
    return {
        "filename": filename,
        "status": status,
        "error": error,
        "payload": payload if status == "valid" else None,
        "path": f"gs://{storage.BUCKET_NAME}/{storage.artifact_path(domain, run_id, filename)}",
    }


def _save_runs(domain: str, payload: dict) -> None:
    from pipeline.storage import write_json_artifact

    write_json_artifact(domain, "manual", "capture_runs.json", payload)


def _en_standard_display_name_today() -> str:
    now_tallinn = datetime.datetime.now(datetime.UTC).astimezone(_TALLINN_TZ)
    return f"EN_standard_{now_tallinn.strftime('%H:%M|%d.%m.%Y')}"


def _default_run_display_name() -> str:
    now_tallinn = datetime.datetime.now(datetime.UTC).astimezone(_TALLINN_TZ)
    return f"First_run_{now_tallinn.strftime('%H:%M|%d.%m.%Y')}"


def _upsert_run_metadata(domain: str, run_id: str, metadata: dict) -> None:
    normalized = {str(key).strip(): value for key, value in (metadata or {}).items() if str(key).strip()}
    if not normalized:
        return
    runs_payload = _load_runs(domain)
    runs = runs_payload["runs"]
    run = next((r for r in runs if r.get("run_id") == run_id), None)
    if run is None:
        run = {"run_id": run_id, "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "jobs": []}
        runs.append(run)
    for key, value in normalized.items():
        run[key] = value
    _save_runs(domain, {"runs": _sort_runs_newest_first(runs)})


def _upsert_job_status(domain: str, run_id: str, job_record: dict) -> None:
    runs_payload = _load_runs(domain)
    runs = runs_payload["runs"]
    run = next((r for r in runs if r.get("run_id") == run_id), None)
    if run is None:
        run = {"run_id": run_id, "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "jobs": []}
        runs.append(run)
    display_name = _normalize_optional_string(job_record.get("display_name"))
    if display_name is not None:
        run["display_name"] = display_name
    elif "display_name" not in run and "display_name" in job_record:
        run["display_name"] = None
    prior_job = next((j for j in run.get("jobs", []) if j.get("job_id") == job_record.get("job_id")), None)
    normalized_job = dict(job_record)
    normalized_job.pop("display_name", None)
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    normalized_job["updated_at"] = now
    normalized_job["created_at"] = str((prior_job or {}).get("created_at") or now)
    jobs = [j for j in run.get("jobs", []) if j.get("job_id") != normalized_job.get("job_id")]
    jobs.append(normalized_job)
    jobs.sort(key=lambda r: r.get("job_id", ""))
    run["jobs"] = jobs
    _save_runs(domain, {"runs": _sort_runs_newest_first(runs)})


def _is_stale_running_job(job: dict) -> bool:
    status = str(job.get("status", "")).strip().lower()
    if status not in {"running", "queued"}:
        return False
    stale_after = max(int(os.environ.get("WORKFLOW_STALE_JOB_SECONDS", "180")), 30)
    updated_at = _parse_utc_timestamp(str(job.get("updated_at", "")))
    created_at = _parse_utc_timestamp(str(job.get("created_at", "")))
    last_seen = updated_at or created_at
    if last_seen is None:
        return False
    return (time.time() - last_seen) > stale_after


def _as_stale_failed_job(job: dict) -> dict:
    out = dict(job)
    out["status"] = "failed"
    out["error"] = str(out.get("error") or "capture worker stale: no completion heartbeat")
    out["stale"] = True
    return out




def _load_phase2_decisions(domain: str, run_id: str) -> list[dict]:
    if not _artifact_exists_strict(domain, run_id, "template_rules.json"):
        return []
    payload = _read_json_required(domain, run_id, "template_rules.json")
    if not isinstance(payload, list):
        raise ValueError("template_rules.json artifact_invalid")
    rows: list[dict] = []
    for row in payload:
        if not isinstance(row, dict):
            raise ValueError("template_rules.json artifact_invalid")
        item_id = str(row.get("item_id", "")).strip()
        url = str(row.get("url", "")).strip()
        rule_type = str(row.get("rule_type", "")).strip()
        if not item_id or not url or not rule_type:
            raise ValueError("template_rules.json artifact_invalid")
        rows.append({
            "item_id": item_id,
            "url": url,
            "rule_type": rule_type,
            "updated_at": str(row.get("created_at", "")),
        })
    return rows


def _save_phase2_decisions(domain: str, run_id: str, decisions: list[dict]) -> None:
    """Persist decisions via canonical Phase 2 writer (template_rules.json)."""
    ordered = sorted(
        [row for row in decisions if isinstance(row, dict)],
        key=lambda row: (
            str(row.get("item_id", "")),
            str(row.get("url", "")),
            str(_to_rule_type(str(row.get("rule_type", "")))),
            str(row.get("capture_context_id", "")),
            str(row.get("state", "")),
            str(row.get("language", "")),
            str(row.get("viewport_kind", "")),
            str(row.get("user_tier", "")),
            str(row.get("created_at") or row.get("updated_at") or ""),
        ),
    )
    for idx, row in enumerate(ordered):
        if not str(row.get("item_id", "")).strip() or not str(row.get("url", "")).strip():
            raise ValueError(f"invalid phase2 decision at index={idx}: item_id and url are required")
        _upsert_phase2_decision(domain, run_id, row)


def _decision_key(row: dict) -> tuple:
    return (
        str(row.get("capture_context_id", "")),
        str(row.get("item_id", "")),
        str(row.get("url", "")),
        str(row.get("state", "")),
        str(row.get("language", "")),
        str(row.get("viewport_kind", "")),
        str(row.get("user_tier") or ""),
    )


def _upsert_phase2_decision(domain: str, run_id: str, decision: dict) -> dict:
    from pipeline.run_phase2 import run as phase2_run

    item_id = str(decision.get("item_id", "")).strip()
    url = str(decision.get("url", "")).strip()
    rule_type = _to_rule_type(str(decision.get("rule_type", "")).strip())
    saved = phase2_run(domain=domain, run_id=run_id, item_id=item_id, url=url, rule_type=rule_type, note=None)
    out = dict(decision)
    out["rule_type"] = str(saved.get("rule_type", rule_type))
    out["created_at"] = str(saved.get("created_at", decision.get("created_at", "")))
    out["updated_at"] = out["created_at"]
    return out



def _review_writer() -> GCSArtifactWriter:
    from pipeline.storage import BUCKET_NAME

    review_bucket = os.environ.get("REVIEW_BUCKET", BUCKET_NAME)
    return GCSArtifactWriter(_ReviewConfigStore(), BUCKET_NAME, review_bucket)


def _review_status_key(domain: str, capture_context_id: str, language: str) -> str:
    return _review_writer().review_status_key(domain, capture_context_id, language)


def _read_review_status_record(domain: str, capture_context_id: str, language: str) -> dict | None:
    from pipeline.storage import BUCKET_NAME, _gcs_client

    key = _review_status_key(domain, capture_context_id, language)
    review_bucket = os.environ.get("REVIEW_BUCKET", BUCKET_NAME)
    bucket = _gcs_client().bucket(review_bucket)
    blob = bucket.blob(key)
    try:
        raw = json.loads(blob.download_as_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(raw, dict):
        return None
    return {
        "capture_context_id": str(raw.get("capture_context_id", capture_context_id)),
        "status": str(raw.get("status", "")).strip(),
        "reviewer": str(raw.get("reviewer", "")).strip(),
        "timestamp": str(raw.get("timestamp", "")).strip(),
        "language": language,
    }


def _load_review_statuses_for_contexts(domain: str, contexts: list[dict], language: str = "") -> dict[tuple[str, str], dict]:
    rows: dict[tuple[str, str], dict] = {}
    for context in contexts:
        if not isinstance(context, dict):
            continue
        capture_context_id = str(context.get("capture_context_id", "")).strip()
        row_language = str(context.get("language", "")).strip()
        if not capture_context_id or not row_language:
            continue
        if language and row_language != language:
            continue
        record = _read_review_status_record(domain, capture_context_id, row_language)
        if record is None:
            continue
        rows[(capture_context_id, row_language)] = {
            "capture_context_id": record["capture_context_id"],
            "status": record["status"],
            "reviewer": record["reviewer"],
            "timestamp": record["timestamp"],
        }
    return rows


def _load_all_review_statuses(domain: str, language: str = "") -> list[dict]:
    from pipeline.storage import BUCKET_NAME, _gcs_client

    review_bucket = os.environ.get("REVIEW_BUCKET", BUCKET_NAME)
    bucket = _gcs_client().bucket(review_bucket)
    prefix = _review_writer().review_status_prefix(domain)
    by_key: dict[tuple[str, str], dict] = {}
    for blob_meta in bucket.list_blobs(prefix=prefix):
        name = str(getattr(blob_meta, "name", ""))
        suffix = name.removeprefix(prefix)
        if "__" not in suffix or not suffix.endswith(".json"):
            continue
        capture_context_id, raw_language = suffix[:-5].split("__", 1)
        if language and raw_language != language:
            continue
        record = _read_review_status_record(domain, capture_context_id, raw_language)
        if record is None:
            continue
        key = (str(record.get("capture_context_id", "")), str(record.get("language", "")))
        existing = by_key.get(key)
        if existing is None or str(record.get("timestamp", "")) >= str(existing.get("timestamp", "")):
            by_key[key] = record
    rows = list(by_key.values())
    rows.sort(key=lambda row: (row.get("capture_context_id", ""), row.get("language", ""), row.get("timestamp", "")))
    return rows


def _expand_capture_plan(domain: str, planning_rows: list[dict], languages: list[str], viewports: list[str], tiers: list[str], recipes: dict) -> list[dict]:
    from pipeline.run_phase1 import build_planned_jobs

    # NOTE: we intentionally expand cross-product at this layer to guarantee deterministic
    # operator-visible plan ordering: language -> viewport -> user_tier.
    expanded_jobs = []
    seen: set[tuple[str, str, str, str, str, str, str]] = set()
    for language in sorted(languages):
        for viewport in sorted(viewports):
            for tier in sorted(tiers):
                jobs = build_planned_jobs(domain, planning_rows, language, viewport, tier or None, recipes)
                for job in jobs:
                    key = (
                        str(job.context.url),
                        str(job.context.language),
                        str(job.context.viewport_kind),
                        str(job.context.state),
                        str(job.context.user_tier or ""),
                        str(job.recipe_id or ""),
                        str(job.mode),
                    )
                    if key in seen:
                        continue
                    seen.add(key)
                    expanded_jobs.append(job)
    return [
        {
            "url": job.context.url,
            "language": job.context.language,
            "viewport_kind": job.context.viewport_kind,
            "state": job.context.state,
            "user_tier": job.context.user_tier,
            "mode": job.mode,
            "recipe_id": job.recipe_id,
        }
        for job in expanded_jobs
    ]

class _ReviewConfigStore:
    def _client(self):
        from google.cloud import storage  # type: ignore

        return storage.Client()

    def write_json(self, bucket: str, key: str, value):
        import json

        client = self._client()
        blob = client.bucket(bucket).blob(key)
        blob.upload_from_string(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")), content_type="application/json; charset=utf-8")
        return f"gs://{bucket}/{key}"


def _parse_rerun_payload(payload: dict) -> dict:
    required = ["domain", "run_id", "url", "viewport_kind", "state", "language", "capture_context_id"]
    missing = [k for k in required if not str(payload.get(k, "")).strip()]
    if missing:
        raise ValueError(f"missing required fields: {', '.join(missing)}")
    state = str(payload.get("state", "")).strip()
    recipe_id = _normalize_optional_string(payload.get("recipe_id"))
    capture_point_id = _normalize_optional_string(payload.get("capture_point_id"))
    if state == "baseline" and (recipe_id or capture_point_id):
        raise ValueError("baseline rerun cannot include recipe_id/capture_point_id")
    if state != "baseline" and (bool(recipe_id) != bool(capture_point_id)):
        raise ValueError("state rerun requires both recipe_id and capture_point_id, or neither for legacy state-only resolution")
    runtime_payload = {
        "domain": str(payload.get("domain", "")).strip(),
        "run_id": _validate_run_id(str(payload.get("run_id", "")).strip()),
        "language": str(payload.get("language", "")).strip(),
        "viewport_kind": str(payload.get("viewport_kind", "")).strip(),
        "state": state,
        "user_tier": payload.get("user_tier") or None,
        "url": str(payload.get("url", "")).strip(),
        "capture_context_id": str(payload.get("capture_context_id", "")).strip() or None,
        "recipe_id": recipe_id,
        "capture_point_id": capture_point_id,
    }
    load_phase1_runtime_config(runtime_payload)
    return runtime_payload


def _persist_capture_review(payload: dict) -> dict:
    from pipeline.schema_validator import validate

    domain = validate_domain(str(payload.get("domain", "")))
    capture_context_id = str(payload.get("capture_context_id", "")).strip()
    language = str(payload.get("language", "")).strip()
    status = str(payload.get("status", "")).strip()
    reviewer = str(payload.get("reviewer", "operator")).strip() or "operator"
    timestamp = str(payload.get("timestamp", "")).strip()
    if not capture_context_id:
        raise ValueError("capture_context_id is required")
    if not language:
        raise ValueError("language is required")
    if not timestamp:
        raise ValueError("timestamp is required")

    record = {
        "capture_context_id": capture_context_id,
        "status": status,
        "reviewer": reviewer,
        "timestamp": timestamp,
    }
    try:
        validate("capture_review_status", record)
    except Exception as exc:
        raise ValueError(str(exc)) from exc

    from pipeline.storage import BUCKET_NAME

    review_bucket = os.environ.get("REVIEW_BUCKET", BUCKET_NAME)
    writer = GCSArtifactWriter(_ReviewConfigStore(), BUCKET_NAME, review_bucket)
    uri = writer.set_review_status(domain, capture_context_id, language, record)
    return {"record": record, "storage_uri": uri}




def _run_phase0_async(job_id: str, domain: str, run_id: str) -> None:
    """Run Phase 0 in a background thread."""
    _jobs[job_id] = {"status": "running", "phase": "0", "domain": domain, "run_id": run_id}
    try:
        from pipeline.run_phase0 import run as phase0_run
        phase0_run(domain=domain, run_id=run_id)
        _jobs[job_id]["status"] = "done"
        _upsert_job_status(domain, run_id, {"job_id": job_id, "status": "succeeded", "phase": "0"})
    except Exception as exc:
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = str(exc)
        _upsert_job_status(domain, run_id, {"job_id": job_id, "status": "failed", "error": str(exc), "phase": "0"})


def _run_phase1_async(job_id: str, runtime_payload: dict) -> None:
    """Run Phase 1 in a background thread."""
    _jobs[job_id] = {"status": "running", "phase": "1", "domain": runtime_payload.get("domain"), "run_id": runtime_payload.get("run_id")}
    _upsert_job_status(str(runtime_payload.get("domain")), str(runtime_payload.get("run_id")), {"job_id": job_id, "status": "running", "context": runtime_payload})
    try:
        from pipeline.run_phase1 import run_with_config

        config = load_phase1_runtime_config(runtime_payload)
        run_with_config(config)
        _jobs[job_id]["status"] = "done"
        _upsert_job_status(str(runtime_payload.get("domain")), str(runtime_payload.get("run_id")), {"job_id": job_id, "status": "succeeded", "context": runtime_payload})
    except Exception as exc:
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = str(exc)
        _upsert_job_status(
            str(runtime_payload.get("domain")),
            str(runtime_payload.get("run_id")),
            {"job_id": job_id, "status": "failed", "error": str(exc), "context": runtime_payload, "type": "capture"},
        )


def _run_rerun_async(job_id: str, runtime_payload: dict) -> None:
    _jobs[job_id] = {"status": "running", "phase": "rerun", "domain": runtime_payload.get("domain"), "run_id": runtime_payload.get("run_id")}
    _upsert_job_status(str(runtime_payload.get("domain")), str(runtime_payload.get("run_id")), {"job_id": job_id, "status": "running", "context": runtime_payload, "type": "rerun"})
    try:
        from pipeline.run_phase1 import run_exact_context

        run_exact_context(
            domain=str(runtime_payload.get("domain")),
            run_id=str(runtime_payload.get("run_id")),
            url=str(runtime_payload.get("url")),
            viewport_kind=str(runtime_payload.get("viewport_kind")),
            state=str(runtime_payload.get("state")),
            user_tier=runtime_payload.get("user_tier"),
            language=str(runtime_payload.get("language")),
            original_context_id=runtime_payload.get("capture_context_id"),
            recipe_id=runtime_payload.get("recipe_id"),
            capture_point_id=runtime_payload.get("capture_point_id"),
        )
        _jobs[job_id]["status"] = "done"
        _upsert_job_status(str(runtime_payload.get("domain")), str(runtime_payload.get("run_id")), {"job_id": job_id, "status": "succeeded", "context": runtime_payload, "type": "rerun"})
    except Exception as exc:
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = str(exc)
        _upsert_job_status(str(runtime_payload.get("domain")), str(runtime_payload.get("run_id")), {"job_id": job_id, "status": "failed", "error": str(exc), "context": runtime_payload, "type": "rerun"})


def _run_phase3_async(job_id: str, domain: str, run_id: str) -> None:
    """Run Phase 3 in a background thread."""
    _jobs[job_id] = {"status": "running", "phase": "3", "domain": domain, "run_id": run_id}
    try:
        from pipeline.run_phase3 import run as phase3_run
        phase3_run(domain=domain, run_id=run_id)
        _require_artifact_exists(domain, run_id, "eligible_dataset.json")
        en_standard_display_name = _en_standard_display_name_today()
        _jobs[job_id]["status"] = "done"
        _upsert_job_status(domain, run_id, {"job_id": job_id, "status": "succeeded", "phase": "3"})
        _upsert_run_metadata(domain, run_id, {"en_standard_display_name": en_standard_display_name})
    except Exception as exc:
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = str(exc)
        _upsert_job_status(domain, run_id, {"job_id": job_id, "status": "failed", "phase": "3", "error": str(exc)})


def _run_phase6_async(job_id: str, domain: str, run_id: str, en_run_id: str) -> None:
    _jobs[job_id] = {"status": "running", "phase": "6", "domain": domain, "run_id": run_id, "en_run_id": en_run_id}
    try:
        from pipeline.run_phase6 import run as phase6_run

        review_mode = os.environ.get("PHASE6_REVIEW_PROVIDER", "").strip()
        if not review_mode:
            raise ValueError("PHASE6_REVIEW_PROVIDER is required for Phase 6 execution")
        phase6_run(domain=domain, en_run_id=en_run_id, target_run_id=run_id, review_mode=review_mode)
        _jobs[job_id]["status"] = "done"
        _upsert_job_status(domain, run_id, {"job_id": job_id, "status": "succeeded", "phase": "6", "en_run_id": en_run_id})
    except Exception as exc:
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = str(exc)
        _upsert_job_status(domain, run_id, {"job_id": job_id, "status": "failed", "phase": "6", "en_run_id": en_run_id, "error": str(exc)})





def _prepare_check_languages_async(job_id: str, domain: str, en_run_id: str, target_language: str, target_run_id: str, target_url: str) -> None:
    check_languages_ui.prepare_check_languages_async(
        job_id,
        domain,
        en_run_id,
        target_language,
        target_run_id,
        target_url,
        jobs=_jobs,
        upsert_job_status=_upsert_job_status,
    )


def _run_check_languages_llm_async(job_id: str, domain: str, en_run_id: str, target_language: str, target_run_id: str, target_url: str) -> None:
    check_languages_ui.run_check_languages_llm_async(
        job_id,
        domain,
        en_run_id,
        target_language,
        target_run_id,
        target_url,
        jobs=_jobs,
        upsert_job_status=_upsert_job_status,
    )


def _check_languages_llm_preflight_error() -> str | None:
    return check_languages_ui.check_languages_llm_preflight_error()


class _CheckLanguagesLlmPreflightError(check_languages_ui.CheckLanguagesLlmPreflightError):
    """Backward-compatible alias for tests that import this symbol from skeleton_server."""


# Legacy combined prepare+LLM flow retained intentionally for non-UI and test utility paths.
# The UI handler path currently runs _prepare_check_languages_async and
# _run_check_languages_llm_async as separate stages instead of calling this wrapper.
def _run_check_languages_async(job_id: str, domain: str, en_run_id: str, target_language: str, target_run_id: str, target_url: str) -> None:
    """Backward-compatible composed flow: prepare payload, then run LLM review."""
    check_languages_ui.run_check_languages_async(
        job_id,
        domain,
        en_run_id,
        target_language,
        target_run_id,
        target_url,
        jobs=_jobs,
        upsert_job_status=_upsert_job_status,
        latest_check_languages_job=_latest_check_languages_job,
    )


def _workflow_section_status(*, has_artifact: bool, count: int | None = None, pending_on: bool = False) -> str:
    if has_artifact:
        if count is not None and count == 0:
            return "empty"
        return "ready"
    if pending_on:
        return "not_ready"
    return "not_started"


def _workflow_status_payload(domain: str, run_id: str) -> dict:
    seed_payload = _read_json_safe(domain, "manual", "seed_urls.json", {"urls": []})
    seed_urls = seed_payload.get("urls") if isinstance(seed_payload, dict) else []
    seed_count = len([row for row in seed_urls if isinstance(row, dict) and str(row.get("url", "")).strip() and bool(row.get("active", True))])

    pages = _read_json_safe(domain, run_id, "page_screenshots.json", None)
    items = _read_json_safe(domain, run_id, "collected_items.json", None)
    rules = _read_json_safe(domain, run_id, "template_rules.json", None)
    dataset = _read_json_safe(domain, run_id, "eligible_dataset.json", None)
    issues = _read_json_safe(domain, run_id, "issues.json", None)

    pages_count = len(pages) if isinstance(pages, list) else 0
    items_count = len(items) if isinstance(items, list) else 0
    rules_count = len(rules) if isinstance(rules, list) else 0
    dataset_count = len(dataset) if isinstance(dataset, list) else 0
    issues_count = len(issues) if isinstance(issues, list) else 0

    contexts = [{"capture_context_id": _capture_context_id_from_page(domain, row), "language": str(row.get("language", ""))} for row in (pages or []) if isinstance(row, dict)]
    reviews = list(_load_review_statuses_for_contexts(domain, contexts).values()) if contexts else []
    reviewed_count = len(reviews)

    run_meta = next((row for row in _load_runs(domain).get("runs", []) if str(row.get("run_id", "")) == run_id), None)
    jobs = run_meta.get("jobs", []) if isinstance(run_meta, dict) else []
    effective_jobs = [_as_stale_failed_job(j) if _is_stale_running_job(j) else j for j in jobs]
    running = [j for j in effective_jobs if str(j.get("status", "")).lower() in {"running", "queued"}]
    failed = [j for j in effective_jobs if str(j.get("status", "")).lower() in {"failed", "error"}]
    capture_jobs = [
        j for j in effective_jobs
        if str(j.get("type", "")).lower() == "capture" or str(j.get("phase", "")).lower() == "1" or str(j.get("job_id", "")).startswith("phase1-")
    ]
    capture_attempted = bool(capture_jobs)
    capture_running = any(str(j.get("status", "")).lower() in {"running", "queued"} for j in capture_jobs)
    capture_failed_jobs = [j for j in capture_jobs if str(j.get("status", "")).lower() in {"failed", "error"}]
    capture_last_failure = capture_failed_jobs[-1] if capture_failed_jobs else None

    capture_status = "not_started"
    if capture_running:
        capture_status = "in_progress"
    elif isinstance(pages, list):
        capture_status = "ready" if pages_count > 0 else "empty"
    elif capture_last_failure is not None:
        capture_status = "failed"
    elif capture_attempted:
        capture_status = "not_ready"
    elif seed_count:
        capture_status = "not_ready"
    review_status = "not_started"
    if isinstance(pages, list):
        if pages_count == 0:
            review_status = "empty"
        elif reviewed_count == 0:
            review_status = "not_ready"
        elif reviewed_count < pages_count:
            review_status = "in_progress"
        else:
            review_status = "ready"

    annotation_status = _workflow_section_status(
        has_artifact=isinstance(rules, list),
        count=rules_count,
        pending_on=reviewed_count >= pages_count and pages_count > 0,
    )
    if isinstance(rules, list) and rules_count < items_count and items_count > 0:
        annotation_status = "partial"

    run_status = "not_started"
    if running:
        run_status = "in_progress"
    elif failed:
        run_status = "failed"
    elif isinstance(pages, list):
        run_status = "ready"

    next_action = "configure_seed_urls"
    if capture_status in {"not_started", "not_ready", "failed"} and seed_count:
        next_action = "start_capture"
    elif capture_status == "in_progress":
        next_action = "wait_for_capture"
    elif isinstance(pages, list) and reviewed_count < pages_count:
        next_action = "complete_review"
    elif reviewed_count >= pages_count and not isinstance(rules, list):
        next_action = "save_annotation_rules"
    elif isinstance(rules, list) and not isinstance(dataset, list):
        next_action = "generate_eligible_dataset"
    elif isinstance(dataset, list) and not isinstance(issues, list):
        next_action = "generate_issues"
    elif isinstance(issues, list):
        next_action = "review_issues"

    first_issue_id = ""
    if isinstance(issues, list) and issues:
        first_issue_id = str(sorted([row for row in issues if isinstance(row, dict)], key=_issue_sort_key)[0].get("id", ""))

    run_en_standard_display_name = str((run_meta or {}).get("en_standard_display_name", "")).strip()
    eligible_has_artifact = isinstance(dataset, list)
    eligible_status = _workflow_section_status(has_artifact=eligible_has_artifact, count=dataset_count, pending_on=isinstance(rules, list))
    phase3_job = _latest_phase3_job(domain, run_id)
    phase3_generation_status = str((phase3_job or {}).get("status", "")).strip().lower()
    phase3_generation_error = str((phase3_job or {}).get("error", "")).strip()

    return {
        "state_enum": ["not_started", "in_progress", "ready", "empty", "not_ready", "partial", "failed", "out_of_scope"],
        "seed_urls": {"status": "ready" if seed_count else "empty", "configured": bool(seed_count), "count": seed_count},
        "run": {
            "status": run_status,
            "run_id": run_id,
            "display_name": _normalize_optional_string((run_meta or {}).get("display_name")),
            "domain": domain,
            "jobs_total": len(jobs),
            "jobs_running": len(running),
            "jobs_failed": len(failed),
            "en_standard_display_name": run_en_standard_display_name,
        },
        "capture": {
            "status": capture_status,
            "contexts": pages_count,
            "items": items_count,
            "artifacts_present": isinstance(pages, list),
            "error": str((capture_last_failure or {}).get("error", "")),
            "remediation": [
                "check capture runner prerequisites",
                "see logs",
                "verify env config",
            ] if capture_status == "failed" else [],
        },
        "review": {"status": review_status, "total": pages_count, "reviewed": reviewed_count},
        "annotation": {"status": annotation_status, "rules_count": rules_count},
        "eligible_dataset": {
            "status": eligible_status,
            "ready": eligible_has_artifact,
            "record_count": dataset_count,
            "en_standard_display_name": run_en_standard_display_name,
            "generation_status": phase3_generation_status,
            "generation_error": phase3_generation_error,
        },
        "issues": {"status": _workflow_section_status(has_artifact=isinstance(issues, list), count=issues_count, pending_on=isinstance(dataset, list)), "count": issues_count, "first_issue_id": first_issue_id},
        "next_recommended_action": next_action,
    }



class SkeletonHandler(BaseHTTPRequestHandler):
    def _read_template_cached(self, path: Path) -> str:
        stat = path.stat()
        cached = _template_cache.get(path)
        if cached and cached[0] == stat.st_mtime_ns:
            return cached[1]
        contents = path.read_text(encoding="utf-8")
        _template_cache[path] = (stat.st_mtime_ns, contents)
        return contents

    def _auth_enabled(self) -> bool:
        mode = os.environ.get("AUTH_MODE", AUTH_MODE).strip().upper()
        return mode != "OFF"

    def _is_production(self) -> bool:
        return bool(os.environ.get("K_SERVICE")) or os.environ.get("ENV", "").lower() == "production"

    def _get_cookie(self, key: str) -> str:
        raw_cookie = self.headers.get("Cookie", "")
        for chunk in raw_cookie.split(";"):
            part = chunk.strip()
            if not part or "=" not in part:
                continue
            name, value = part.split("=", 1)
            if name.strip() == key:
                return value.strip()
        return ""

    def _build_cookie_header(self, key: str, value: str, *, max_age: int, http_only: bool) -> str:
        same_site = "Lax"
        # Lax keeps normal same-site UX while reducing CSRF risks for cross-site requests.
        parts = [f"{key}={value}", "Path=/", f"Max-Age={max_age}", f"SameSite={same_site}"]
        if http_only:
            parts.append("HttpOnly")
        if self._is_production():
            parts.append("Secure")
        return "; ".join(parts)

    def _expire_cookie_header(self, key: str, *, http_only: bool) -> str:
        parts = [f"{key}=", "Path=/", "Max-Age=0", "SameSite=Lax"]
        if http_only:
            parts.append("HttpOnly")
        if self._is_production():
            parts.append("Secure")
        return "; ".join(parts)

    def _session_signing_secret(self) -> str:
        return os.environ.get(SESSION_SIGNING_SECRET_ENV, "").strip()

    def _login_password(self) -> str:
        return os.environ.get(WATCHDOG_PASSWORD_ENV, "").strip()

    def _generate_session_token(self) -> str:
        secret = self._session_signing_secret().encode("utf-8")
        nonce = secrets.token_urlsafe(24)
        expires_at = int(time.time()) + SESSION_MAX_AGE_SECONDS
        payload = f"{nonce}:{expires_at}".encode("utf-8")
        sig = hmac.new(secret, payload, hashlib.sha256).hexdigest()
        raw = f"{nonce}:{expires_at}:{sig}".encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("utf-8")

    def _is_authenticated(self) -> bool:
        token = self._get_cookie(SESSION_COOKIE)
        if not token:
            return False
        secret = self._session_signing_secret()
        if not secret:
            return False
        try:
            decoded = base64.urlsafe_b64decode(token.encode("utf-8")).decode("utf-8")
            nonce, expires_raw, signature = decoded.split(":", 2)
            expires_at = int(expires_raw)
        except Exception:
            return False
        expected_sig = hmac.new(secret.encode("utf-8"), f"{nonce}:{expires_at}".encode("utf-8"), hashlib.sha256).hexdigest()
        if not secrets.compare_digest(signature, expected_sig):
            return False
        return expires_at > int(time.time())

    def _require_auth(self, *, api: bool) -> bool:
        if not self._auth_enabled():
            return True
        if self._is_authenticated():
            return True
        if api:
            self._json_response({"error": "unauthorized"}, status=HTTPStatus.UNAUTHORIZED)
        else:
            self.send_response(HTTPStatus.FOUND)
            self.send_header("Location", "/login")
            self.end_headers()
        return False

    def _ensure_csrf_cookie(self) -> str:
        token = self._get_cookie(CSRF_COOKIE)
        if token:
            return token
        return secrets.token_urlsafe(32)

    def _validate_csrf(self, token: str) -> bool:
        if not self._auth_enabled():
            return True
        cookie_token = self._get_cookie(CSRF_COOKIE)
        return bool(cookie_token and token and secrets.compare_digest(cookie_token, token))

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)

        # Health check — must be first to ensure it is always reachable.
        if parsed.path == "/healthz":
            self._json_response({"status": "ok"})
            return

        if parsed.path == "/login":
            if not self._auth_enabled():
                self.send_response(HTTPStatus.FOUND)
                self.send_header("Location", "/")
                self.end_headers()
                return
            if self._is_authenticated():
                self.send_response(HTTPStatus.FOUND)
                self.send_header("Location", "/")
                self.end_headers()
                return
            csrf_token = self._ensure_csrf_cookie()
            self._serve_template("login.html", replacements={"{{error_block}}": "", "{{csrf_token}}": csrf_token}, extra_set_cookies=[self._build_cookie_header(CSRF_COOKIE, csrf_token, max_age=SESSION_MAX_AGE_SECONDS, http_only=False)])
            return

        if parsed.path == "/check-languages":
            if not self._require_auth(api=False):
                return
            self._check_languages_ui().handle_get(parse_qs(parsed.query))
            return
        if parsed.path == "/result-files":
            if not self._require_auth(api=False):
                return
            self._serve_result_files_page(parse_qs(parsed.query))
            return

        page_templates = {
            "/": "index.html",
            "/crawler": "crawler.html",
            "/pulling": "pulling.html",
            "/about": "about.html",
            "/testbench": "testbench.html",
            "/urls": "urls.html",
            "/runs": "runs.html",
            "/workflow": "workflow.html",
            "/contexts": "contexts.html",
        }
        if parsed.path == "/pulls":
            if not self._require_auth(api=False):
                return
            self._serve_pulls_page(parse_qs(parsed.query))
            return
        if parsed.path in page_templates:
            if not self._require_auth(api=False):
                return
            self._serve_template(page_templates[parsed.path])
            return
        if parsed.path == "/watchdog-fixture" or parsed.path.startswith("/watchdog-fixture/"):
            fixture_relative = parsed.path.removeprefix("/watchdog-fixture").lstrip("/")
            self._serve_fixture(fixture_relative)
            return
        if parsed.path in {"/favicon.ico", "/favicon.png"}:
            self._serve_favicon()
            return
        if parsed.path.startswith("/static/"):
            self._serve_static(parsed.path.removeprefix("/static/"))
            return
        if parsed.path == "/api/domains":
            if not self._require_auth(api=True):
                return
            self._json_response({
                "items": _list_domains(),
                "last_used_first_run_domain": _last_used_first_run_domain(),
            })
            return
        if parsed.path == "/api/url-inventory":
            if not self._require_auth(api=True):
                return
            domain = parse_qs(parsed.query).get("domain", [""])[0]
            try:
                valid_domain = validate_domain(_normalize_testsite_domain_key(domain))
                payload = read_seed_urls(valid_domain)
            except ValueError as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            urls = [row.get("url", "") for row in payload.get("urls", []) if isinstance(row, dict)]
            self._json_response({"domain": valid_domain, "urls": sorted(urls)})
            return
        if parsed.path == "/api/page-screenshot":
            if not self._require_auth(api=True):
                return
            query = parse_qs(parsed.query)
            required, missing = _require_query_params(query, "domain", "run_id", "page_id")
            if missing:
                self._json_response(_missing_required_query_params(*missing), status=HTTPStatus.BAD_REQUEST)
                return
            domain = required["domain"]
            try:
                run_id = _validate_run_id(required["run_id"])
            except ValueError as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            page_id = required["page_id"]
            try:
                pages = _read_list_artifact_required(domain, run_id, "page_screenshots.json")
            except ValueError as exc:
                self._json_response({"error": str(exc), "status": "artifact_invalid"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            page = next((row for row in pages if isinstance(row, dict) and str(row.get("page_id", "")) == page_id), None)
            if page is None:
                self._json_response({"error": "page_screenshot_not_found", "status": "not_found"}, status=HTTPStatus.NOT_FOUND)
                return

            storage_uri = str((page or {}).get("storage_uri", "")).strip()
            etag = hashlib.sha1(f"{page_id}|{storage_uri}".encode("utf-8")).hexdigest()
            if_none_match = str(self.headers.get("If-None-Match", "")).strip().strip('"')
            if if_none_match and if_none_match == etag:
                self.send_response(HTTPStatus.NOT_MODIFIED)
                self.send_header("ETag", f'"{etag}"')
                self.send_header("Cache-Control", "private, max-age=300")
                self.end_headers()
                return

            http_uri = _parse_http_uri(storage_uri)
            if http_uri is not None:
                self.send_response(HTTPStatus.FOUND)
                self.send_header("Location", http_uri)
                self.send_header("ETag", f'"{etag}"')
                self.send_header("Cache-Control", "private, max-age=300")
                self.end_headers()
                return

            parsed_uri = _parse_gs_uri(storage_uri)
            if parsed_uri is None:
                self._json_response({"error": "page_screenshot_storage_uri_invalid", "status": "artifact_invalid"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            bucket_name, object_path = parsed_uri
            try:
                from pipeline.storage import _gcs_client

                bucket = _gcs_client().bucket(bucket_name)
                blob = bucket.blob(object_path)
                image_bytes = blob.download_as_bytes()
            except Exception:
                self._json_response({"error": "page_screenshot_unavailable", "status": "not_ready"}, status=HTTPStatus.SERVICE_UNAVAILABLE)
                return
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "image/png")
            self.send_header("Cache-Control", "private, max-age=300")
            self.send_header("ETag", f'"{etag}"')
            self.send_header("Content-Length", str(len(image_bytes)))
            self.end_headers()
            self.wfile.write(image_bytes)
            return
        if parsed.path == "/api/element-type-whitelist":
            if not self._require_auth(api=True):
                return
            query = parse_qs(parsed.query)
            required, missing = _require_query_params(query, "domain")
            if missing:
                self._json_response(_missing_required_query_params(*missing), status=HTTPStatus.BAD_REQUEST)
                return
            try:
                domain = validate_domain(required["domain"])
                values = _load_domain_element_type_whitelist(domain)
            except ValueError as exc:
                self._json_response({"error": str(exc), "status": "artifact_invalid"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            self._json_response({"domain": domain, "entries": values})
            return
        if parsed.path == "/api/pulls":
            if not self._require_auth(api=True):
                return
            query = parse_qs(parsed.query)
            required, missing = _require_query_params(query, "domain", "run_id")
            if missing:
                self._json_response(_missing_required_query_params(*missing), status=HTTPStatus.BAD_REQUEST)
                return
            domain = required["domain"]
            try:
                run_id = _validate_run_id(required["run_id"])
            except ValueError as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            try:
                _require_artifact_exists(domain, run_id, "collected_items.json")
                _require_artifact_exists(domain, run_id, "page_screenshots.json")
                items = _read_list_artifact_required(domain, run_id, "collected_items.json")
                page_screenshots = _read_list_artifact_required(domain, run_id, "page_screenshots.json")
                universal_sections_optional = _read_list_artifact_optional_strict(domain, run_id, "universal_sections.json")
                universal_sections = universal_sections_optional or []
                decisions = _load_phase2_decisions(domain, run_id)
                whitelist = _load_domain_element_type_whitelist(domain)
            except FileNotFoundError:
                if not _artifact_exists(domain, run_id, "collected_items.json"):
                    self._json_response(_not_ready_payload("collected_items"), status=HTTPStatus.NOT_FOUND)
                else:
                    self._json_response(_not_ready_payload("page_screenshots"), status=HTTPStatus.NOT_FOUND)
                return
            except ValueError as exc:
                self._json_response({"error": str(exc), "status": "artifact_invalid"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            pages_by_id = {
                str(row.get("page_id", "")): row
                for row in page_screenshots
                if isinstance(row, dict) and str(row.get("page_id", "")).strip()
            }
            decisions_by_item_url = {(str(row.get("item_id", "")), str(row.get("url", ""))): row for row in decisions}
            url_filter = query.get("url", [""])[0].strip().lower()
            state_filter = query.get("state", [""])[0].strip().lower()
            language_filter = query.get("language", [""])[0].strip().lower()
            viewport_filter = query.get("viewport_kind", [""])[0].strip().lower()
            tier_filter = query.get("user_tier", [""])[0].strip().lower()
            rows = []
            for row in items:
                if not isinstance(row, dict):
                    continue
                if url_filter and url_filter not in str(row.get("url", "")).lower():
                    continue
                if state_filter and state_filter != str(row.get("state", "")).lower():
                    continue
                if language_filter and language_filter != str(row.get("language", "")).lower():
                    continue
                if viewport_filter and viewport_filter != str(row.get("viewport_kind", "")).lower():
                    continue
                if tier_filter and tier_filter != str(row.get("user_tier") or "").lower():
                    continue
                element_type = str(row.get("element_type", "")).strip()
                if element_type.lower() == "script":
                    continue
                decision = decisions_by_item_url.get((str(row.get("item_id", "")), str(row.get("url", ""))), {})
                if _row_matches_whitelist(row, whitelist):
                    if not decision:
                        decision = {"rule_type": "ALWAYS_COLLECT"}
                    continue
                page_id = str(row.get("page_id", ""))
                page_row = pages_by_id.get(page_id, {})
                page_viewport = page_row.get("viewport") if isinstance(page_row.get("viewport"), dict) else None
                rows.append({
                    "item_id": str(row.get("item_id", "")),
                    "page_id": page_id,
                    "capture_context_id": _capture_context_id_from_page(domain, row),
                    "url": str(row.get("url", "")),
                    "state": str(row.get("state", "")),
                    "language": str(row.get("language", "")),
                    "viewport_kind": str(row.get("viewport_kind", "")),
                    "user_tier": _normalize_optional_string(row.get("user_tier")),
                    "element_type": element_type,
                    "text": str(row.get("text", "")),
                    "css_selector": str(row.get("css_selector", "")),
                    "bbox": row.get("bbox") if isinstance(row.get("bbox"), dict) else None,
                    "tag": _normalize_optional_string(row.get("tag")),
                    "attributes": row.get("attributes") if isinstance(row.get("attributes"), dict) else None,
                    "not_found": bool(row.get("not_found", False)),
                    "decision": str(decision.get("rule_type", "")),
                    "screenshot_storage_uri": str(page_row.get("storage_uri", "")),
                    "screenshot_view_url": _page_screenshot_view_url(domain, run_id, page_id) if page_id and page_row else "",
                    "page_viewport": page_viewport,
                })
            for section in universal_sections if isinstance(universal_sections, list) else []:
                if not isinstance(section, dict):
                    continue
                section_id = str(section.get("section_id", "")).strip()
                if not section_id:
                    continue
                rows.append({
                    "item_id": f"universal-{section_id}",
                    "capture_context_id": "",
                    "url": str(section.get("representative_url", "")),
                    "state": "universal",
                    "language": "en",
                    "viewport_kind": "any",
                    "user_tier": None,
                    "element_type": "universal_section",
                    "text": str(section.get("label", "universal section")),
                    "not_found": False,
                    "decision": "",
                })
            rows.sort(key=lambda item: item.get("item_id", ""))
            self._json_response({"rows": rows, "missing_universal_sections": universal_sections_optional is None, "element_whitelist": whitelist})
            return
        if parsed.path == "/api/rules":
            if not self._require_auth(api=True):
                return
            query = parse_qs(parsed.query)
            required, missing = _require_query_params(query, "domain", "run_id")
            if missing:
                self._json_response(_missing_required_query_params(*missing), status=HTTPStatus.BAD_REQUEST)
                return
            try:
                run_id = _validate_run_id(required["run_id"])
                rules = _load_phase2_decisions(required["domain"], run_id)
            except ValueError as exc:
                if str(exc).startswith("run_id"):
                    self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                else:
                    self._json_response({"error": str(exc), "status": "artifact_invalid"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            self._json_response({"rules": rules})
            return
        if parsed.path == "/api/issues/results":
            if not self._require_auth(api=True):
                return
            query = parse_qs(parsed.query)
            required, missing = _require_query_params(query, "domain")
            if missing:
                self._json_response(_missing_required_query_params(*missing), status=HTTPStatus.BAD_REQUEST)
                return
            try:
                domain = validate_domain(_normalize_testsite_domain_key(required["domain"]))
            except ValueError as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            payload = _persisted_issue_results_payload(domain)
            self._json_response(payload)
            return
        if parsed.path in {"/api/issues", "/api/issues/export"}:
            if not self._require_auth(api=True):
                return
            query = parse_qs(parsed.query)
            required, missing = _require_query_params(query, "domain", "run_id")
            if missing:
                self._json_response(_missing_required_query_params(*missing), status=HTTPStatus.BAD_REQUEST)
                return
            try:
                domain = validate_domain(_normalize_testsite_domain_key(required["domain"]))
            except ValueError as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            try:
                run_id = _validate_run_id(required["run_id"])
            except ValueError as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            try:
                _require_artifact_exists(domain, run_id, "issues.json")
                issues = _read_list_artifact_required(domain, run_id, "issues.json")
            except FileNotFoundError:
                self._json_response(_not_ready_payload("issues"), status=HTTPStatus.NOT_FOUND)
                return
            except ValueError as exc:
                self._json_response({"error": str(exc), "status": "artifact_invalid"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            filtered = _filter_issues(issues, query)
            filtered.sort(key=_issue_sort_key)
            response_target_language = _infer_target_language_for_run(domain, run_id, query.get("language", [""])[0])
            if parsed.path.endswith("/export") and query.get("format", ["json"])[0].strip().lower() == "csv":
                encoded = _issues_to_csv(filtered).encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/csv; charset=utf-8")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)
                return
            self._json_response({"issues": filtered, "count": len(filtered), "target_language": response_target_language})
            return
        if parsed.path == "/api/issues/detail":
            if not self._require_auth(api=True):
                return
            query = parse_qs(parsed.query)
            required, missing = _require_query_params(query, "domain", "run_id", "id")
            if missing:
                self._json_response(_missing_required_query_params(*missing), status=HTTPStatus.BAD_REQUEST)
                return
            try:
                domain = validate_domain(_normalize_testsite_domain_key(required["domain"]))
            except ValueError as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            try:
                run_id = _validate_run_id(required["run_id"])
            except ValueError as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            issue_id = required["id"]
            try:
                _require_artifact_exists(domain, run_id, "issues.json")
                issues = _read_list_artifact_required(domain, run_id, "issues.json")
            except FileNotFoundError:
                self._json_response(_not_ready_payload("issues"), status=HTTPStatus.NOT_FOUND)
                return
            except ValueError as exc:
                self._json_response({"error": str(exc), "status": "artifact_invalid"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            issue = next((i for i in issues if isinstance(i, dict) and str(i.get("id", "")) == issue_id), None)
            if issue is None:
                self._json_response({"error": "issue not found"}, status=HTTPStatus.NOT_FOUND)
                return
            evidence = issue.get("evidence", {}) if isinstance(issue.get("evidence"), dict) else {}
            item_id = str(evidence.get("item_id", ""))
            try:
                page_rows_optional = _read_list_artifact_optional_strict(domain, run_id, "page_screenshots.json")
                collected_rows_optional = _read_list_artifact_optional_strict(domain, run_id, "collected_items.json")
            except ValueError as exc:
                self._json_response({"error": str(exc), "status": "artifact_invalid"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            page_rows = page_rows_optional or []
            collected_rows = collected_rows_optional or []
            item = next((r for r in collected_rows if isinstance(r, dict) and str(r.get("item_id", "")) == item_id), None) if item_id else None
            page = None
            if item is not None:
                page = next((p for p in page_rows if isinstance(p, dict) and p.get("page_id") == item.get("page_id")), None)
            missing_refs: list[str] = []
            if not _artifact_exists(domain, run_id, "page_screenshots.json"):
                missing_refs.append("page_screenshots")
            if not _artifact_exists(domain, run_id, "collected_items.json"):
                missing_refs.append("collected_items")
            if item_id and item is None:
                missing_refs.append("element")
            if item is not None and page is None:
                missing_refs.append("page")
            page_id = str((page or {}).get("page_id") or evidence.get("page_id") or "")
            screenshot_uri = str((page or {}).get("storage_uri") or evidence.get("storage_uri", "") or "")
            if not page_id and screenshot_uri:
                matched_page = next((
                    p for p in page_rows
                    if isinstance(p, dict) and str(p.get("storage_uri", "")).strip() == screenshot_uri and str(p.get("page_id", "")).strip()
                ), None)
                if matched_page is not None:
                    page_id = str(matched_page.get("page_id", "")).strip()
            screenshot_view_url = _page_screenshot_view_url(domain, run_id, page_id) if page_id else (_parse_http_uri(screenshot_uri) or "")
            if not screenshot_uri:
                missing_refs.append("screenshot")
            self._json_response({
                "issue": issue,
                "drilldown": {
                    "screenshot_uri": screenshot_uri,
                    "screenshot_view_url": screenshot_view_url,
                    "page": page,
                    "element": item,
                    "artifact_refs": {
                        "issues": f"{domain}/{run_id}/issues.json",
                        "page_screenshots": f"{domain}/{run_id}/page_screenshots.json",
                        "collected_items": f"{domain}/{run_id}/collected_items.json",
                    },
                    "missing_refs": sorted(set(missing_refs)),
                    "partial": bool(missing_refs),
                },
            })
            return

        if parsed.path == "/api/seed-urls":
            if not self._require_auth(api=True):
                return
            domain = parse_qs(parsed.query).get("domain", [""])[0]
            try:
                valid_domain = validate_domain(_normalize_testsite_domain_key(domain))
            except ValueError as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            try:
                payload = read_seed_urls(valid_domain)
            except Exception as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            self._json_response(payload)
            return
        if parsed.path == "/api/testbench/modules":
            if not self._require_auth(api=True):
                return
            self._json_response({"modules": get_modules()})
            return
        if parsed.path == "/api/recipes":
            if not self._require_auth(api=True):
                return
            domain = parse_qs(parsed.query).get("domain", [""])[0]
            try:
                valid_domain = validate_domain(_normalize_testsite_domain_key(domain))
                self._json_response({"recipes": list_recipes(valid_domain)})
            except ValueError as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        # Job status endpoint
        if parsed.path == "/api/capture/runs":
            if not self._require_auth(api=True):
                return
            domain = parse_qs(parsed.query).get("domain", [""])[0]
            try:
                runs_payload = _load_runs(validate_domain(_normalize_testsite_domain_key(domain)))
                runs = runs_payload.get("runs", []) if isinstance(runs_payload, dict) else []
                normalized_runs = []
                for run in _sort_runs_newest_first(runs):
                    if not isinstance(run, dict):
                        continue
                    normalized_run = dict(run)
                    normalized_run["display_name"] = _normalize_optional_string(run.get("display_name"))
                    normalized_runs.append(normalized_run)
                self._json_response({"runs": normalized_runs})
            except ValueError as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        if parsed.path in {"/api/capture/contexts", "/api/capture-contexts"}:
            if not self._require_auth(api=True):
                return
            query = parse_qs(parsed.query)
            required, missing = _require_query_params(query, "domain", "run_id")
            if missing:
                self._json_response(_missing_required_query_params(*missing), status=HTTPStatus.BAD_REQUEST)
                return
            domain = required["domain"]
            try:
                run_id = _validate_run_id(required["run_id"])
            except ValueError as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            language_filter = str(query.get("language", [""])[0]).strip()
            try:
                _require_artifact_exists(domain, run_id, "page_screenshots.json")
                pages = _read_list_artifact_required(domain, run_id, "page_screenshots.json")
                elements_optional = _read_list_artifact_optional_strict(domain, run_id, "collected_items.json")
            except FileNotFoundError:
                self._json_response(_not_ready_payload("page_screenshots"), status=HTTPStatus.NOT_FOUND)
                return
            except ValueError as exc:
                self._json_response({"error": str(exc), "status": "artifact_invalid"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            elements = elements_optional or []
            by_page = {}
            for row in elements:
                page_id = row.get("page_id") if isinstance(row, dict) else None
                if not page_id:
                    continue
                by_page[page_id] = by_page.get(page_id, 0) + 1
            contexts = []
            for page in pages:
                if not isinstance(page, dict):
                    continue
                if language_filter and str(page.get("language", "")).strip() != language_filter:
                    continue
                capture_context_id = _capture_context_id_from_page(domain, page)
                contexts.append({
                    "capture_context_id": capture_context_id,
                    "page_id": str(page.get("page_id", "")),
                    "url": str(page.get("url", "")),
                    "viewport_kind": str(page.get("viewport_kind", "")),
                    "state": str(page.get("state", "")),
                    "language": str(page.get("language", "")),
                    "user_tier": _normalize_optional_string(page.get("user_tier")),
                    "storage_uri": str(page.get("storage_uri", "")),
                    "screenshot_view_url": _page_screenshot_view_url(domain, run_id, str(page.get("page_id", ""))) if str(page.get("page_id", "")) else "",
                    "elements_count": by_page.get(page.get("page_id"), 0),
                })
            reviews_by_key = _load_review_statuses_for_contexts(domain, contexts, language=language_filter)
            for context in contexts:
                context["review_status"] = reviews_by_key.get((str(context.get("capture_context_id", "")), str(context.get("language", ""))))
            contexts.sort(key=lambda row: (str(row.get("capture_context_id", "")), str(row.get("page_id", "")), str(row.get("url", ""))))
            self._json_response({"contexts": contexts})
            return
        if parsed.path == "/api/capture/reviews":
            if not self._require_auth(api=True):
                return
            query = parse_qs(parsed.query)
            required, missing = _require_query_params(query, "domain", "run_id")
            if missing:
                self._json_response(_missing_required_query_params(*missing), status=HTTPStatus.BAD_REQUEST)
                return
            domain = required["domain"]
            try:
                run_id = _validate_run_id(required["run_id"])
            except ValueError as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            language_filter = str(query.get("language", [""])[0]).strip()
            if not _artifact_exists_strict(domain, run_id, "page_screenshots.json"):
                self._json_response({"status": "not_ready", "error": "page_screenshots artifact missing"}, status=HTTPStatus.NOT_FOUND)
                return
            try:
                pages = _read_list_artifact_required(domain, run_id, "page_screenshots.json")
            except ValueError as exc:
                self._json_response({"error": str(exc), "status": "artifact_invalid"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            contexts = [
                {
                    "capture_context_id": _capture_context_id_from_page(domain, page),
                    "language": str(page.get("language", "")),
                }
                for page in pages
                if isinstance(page, dict)
            ]
            reviews = list(_load_review_statuses_for_contexts(domain, contexts, language=language_filter).values())
            reviews.sort(key=lambda row: (str(row.get("capture_context_id", "")), str(row.get("timestamp", ""))))
            self._json_response({"reviews": reviews})
            return
        if parsed.path == "/api/workflow/status":
            if not self._require_auth(api=True):
                return
            query = parse_qs(parsed.query)
            required, missing = _require_query_params(query, "domain", "run_id")
            if missing:
                self._json_response(_missing_required_query_params(*missing), status=HTTPStatus.BAD_REQUEST)
                return
            try:
                payload = _workflow_status_payload(required["domain"], _validate_run_id(required["run_id"]))
            except ValueError as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            self._json_response(payload)
            return

        if parsed.path == "/api/job":
            if not self._require_auth(api=True):
                return
            job_id = parse_qs(parsed.query).get("id", [""])[0]
            if job_id in _jobs:
                self._json_response(_jobs[job_id])
            else:
                self._json_response({"status": "not_found"}, status=HTTPStatus.NOT_FOUND)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def do_PUT(self) -> None:  # noqa: N802
        if not self._require_auth(api=True):
            return
        csrf_header = self.headers.get("X-CSRF-Token", "")
        if not self._validate_csrf(csrf_header):
            self._json_response({"error": "csrf validation failed"}, status=HTTPStatus.FORBIDDEN)
            return

        if self.path == "/api/seed-urls":
            payload = self._read_json_payload()
            domain = str(payload.get("domain", ""))
            urls_multiline = str(payload.get("urls_multiline", ""))
            try:
                valid_domain = validate_domain(_normalize_testsite_domain_key(domain))
                parsed_urls = parse_seed_urls_with_errors(urls_multiline)
                saved = write_seed_urls(valid_domain, parsed_urls["urls"])
                saved["validation_errors"] = parsed_urls["errors"]
                _register_domain(valid_domain)
            except ValueError as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            except Exception as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            self._json_response(saved)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/login":
            if not self._auth_enabled():
                self.send_response(HTTPStatus.FOUND)
                self.send_header("Location", "/")
                self.end_headers()
                return
            form = self._read_form_payload()
            password = str(form.get("password", "")).strip()
            csrf_token = str(form.get("csrf_token", "")).strip()

            if not self._validate_csrf(csrf_token):
                refreshed_csrf = self._ensure_csrf_cookie()
                self._serve_template(
                    "login.html",
                    status=HTTPStatus.FORBIDDEN,
                    replacements={
                        "{{error_block}}": '<div class="error">❌ Security error (CSRF). Please try again.</div>',
                        "{{csrf_token}}": refreshed_csrf,
                    },
                    extra_set_cookies=[self._build_cookie_header(CSRF_COOKIE, refreshed_csrf, max_age=SESSION_MAX_AGE_SECONDS, http_only=False)],
                )
                return

            expected_password = self._login_password()
            signing_secret = self._session_signing_secret()
            if not expected_password or not signing_secret:
                self._json_response(
                    {
                        "error": (
                            f"missing required environment variable: {WATCHDOG_PASSWORD_ENV} or {SESSION_SIGNING_SECRET_ENV}"
                        )
                    },
                    status=HTTPStatus.INTERNAL_SERVER_ERROR,
                )
                return

            if secrets.compare_digest(password, expected_password):
                session_token = self._generate_session_token()
                new_csrf = secrets.token_urlsafe(32)
                self.send_response(HTTPStatus.FOUND)
                self.send_header("Location", "/")
                self.send_header("Set-Cookie", self._build_cookie_header(SESSION_COOKIE, session_token, max_age=SESSION_MAX_AGE_SECONDS, http_only=True))
                self.send_header("Set-Cookie", self._build_cookie_header(CSRF_COOKIE, new_csrf, max_age=SESSION_MAX_AGE_SECONDS, http_only=False))
                self.end_headers()
                return

            refreshed_csrf = self._ensure_csrf_cookie()
            self._serve_template(
                "login.html",
                status=HTTPStatus.UNAUTHORIZED,
                replacements={
                    "{{error_block}}": '<div class="error">❌ Invalid password</div>',
                    "{{csrf_token}}": refreshed_csrf,
                },
                extra_set_cookies=[self._build_cookie_header(CSRF_COOKIE, refreshed_csrf, max_age=SESSION_MAX_AGE_SECONDS, http_only=False)],
            )
            return

        if self.path == "/logout":
            if not self._auth_enabled():
                self._json_response({"status": "auth disabled"})
                return
            if not self._require_auth(api=False):
                return
            csrf_header = self.headers.get("X-CSRF-Token", "")
            if not self._validate_csrf(csrf_header):
                self._json_response({"error": "csrf validation failed"}, status=HTTPStatus.FORBIDDEN)
                return
            self.send_response(HTTPStatus.FOUND)
            self.send_header("Location", "/login")
            self.send_header("Set-Cookie", self._expire_cookie_header(SESSION_COOKIE, http_only=True))
            self.send_header("Set-Cookie", self._expire_cookie_header(CSRF_COOKIE, http_only=False))
            self.end_headers()
            return

        if self.path == "/check-languages":
            if not self._require_auth(api=False):
                return
            form = self._read_form_payload()
            if not self._validate_csrf(str(form.get("csrf_token", "")).strip()):
                self._check_languages_ui().redirect_check_languages(form, message="Security error (CSRF). Please refresh and try again.", level="error")
                return
            self._check_languages_ui().handle_post(form)
            return

        if not self._require_auth(api=True):
            return
        csrf_header = self.headers.get("X-CSRF-Token", "")
        if not self._validate_csrf(csrf_header):
            self._json_response({"error": "csrf validation failed"}, status=HTTPStatus.FORBIDDEN)
            return

        if self.path == "/api/seed-urls/add":
            payload = self._read_json_payload()
            domain = str(payload.get("domain", ""))
            urls_multiline = str(payload.get("urls_multiline", ""))
            try:
                valid_domain = validate_domain(_normalize_testsite_domain_key(domain))
                parsed_urls = parse_seed_urls_with_errors(urls_multiline)
                incoming = parsed_urls["urls"]
                existing = read_seed_urls(valid_domain)
                existing_urls = {str(row.get("url", "")) for row in existing.get("urls", []) if isinstance(row, dict) and row.get("url")}
                merged = sorted(existing_urls | set(incoming))
                saved = write_seed_urls(valid_domain, merged)
                _register_domain(valid_domain)
            except ValueError as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            except Exception as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            saved["validation_errors"] = parsed_urls["errors"]
            self._json_response(saved)
            return

        if self.path == "/api/seed-urls/delete":
            payload = self._read_json_payload()
            domain = str(payload.get("domain", ""))
            try:
                valid_domain = validate_domain(_normalize_testsite_domain_key(domain))
                normalized = normalize_seed_url(str(payload.get("url", "")))
                if normalized is None:
                    raise ValueError("url is required")
                existing = read_seed_urls(valid_domain)
                remaining = [
                    str(row.get("url"))
                    for row in existing.get("urls", [])
                    if isinstance(row, dict) and row.get("url") and str(row.get("url")) != normalized
                ]
                saved = write_seed_urls(valid_domain, remaining)
                _register_domain(valid_domain)
            except ValueError as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            except Exception as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            self._json_response(saved)
            return

        if self.path == "/api/seed-urls/clear":
            payload = self._read_json_payload()
            domain = str(payload.get("domain", ""))
            try:
                valid_domain = validate_domain(_normalize_testsite_domain_key(domain))
                saved = write_seed_urls(valid_domain, [])
                _register_domain(valid_domain)
            except ValueError as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            except Exception as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            self._json_response(saved)
            return


        if self.path == "/api/recipes/upsert":
            payload = self._read_json_payload()
            domain = str(payload.get("domain", ""))
            recipe = payload.get("recipe")
            try:
                valid_domain = validate_domain(_normalize_testsite_domain_key(domain))
                if not isinstance(recipe, dict):
                    raise ValueError("recipe object is required")
                saved = upsert_recipe(valid_domain, recipe)
                _register_domain(valid_domain)
                self._json_response({"recipe": saved, "recipes": list_recipes(valid_domain)})
            except ValueError as exc:
                self._json_response(
                    {
                        "status": "failed",
                        "error": str(exc),
                        "action": "start_capture",
                        "previous_state": "not_started",
                        "resulting_state": "failed",
                        "next_expected_state": "not_started",
                        "remediation": ["check capture runner prerequisites", "see logs", "verify env config"],
                    },
                    status=HTTPStatus.BAD_REQUEST,
                )
            except Exception as exc:
                self._json_response(
                    {
                        "status": "failed",
                        "error": str(exc),
                        "action": "start_capture",
                        "previous_state": "not_started",
                        "resulting_state": "failed",
                        "next_expected_state": "not_started",
                        "remediation": ["check capture runner prerequisites", "see logs", "verify env config"],
                    },
                    status=HTTPStatus.INTERNAL_SERVER_ERROR,
                )
            return

        if self.path == "/api/recipes/upload":
            fields, files = self._read_multipart_form_payload()
            domain = str(fields.get("domain_id", "")).strip()
            attach_to_url = str(fields.get("attach_to_url", "")).strip().lower() in {"1", "true", "yes", "on"}
            overwrite = str(fields.get("overwrite", "")).strip().lower() in {"1", "true", "yes", "on"}
            raw_url = str(fields.get("url", "")).strip()
            recipe_file = files.get("file", {})
            filename = str(recipe_file.get("filename", "")).strip()
            content = recipe_file.get("content", b"")
            recipe_id = ""
            try:
                valid_domain = validate_domain(_normalize_testsite_domain_key(domain))
                if not filename:
                    raise ValueError("file is required")
                if not isinstance(content, (bytes, bytearray)) or not content:
                    raise ValueError("file is empty")
                if not (filename.lower().endswith(".json") or filename.lower().endswith(".json5")):
                    raise ValueError("file must be .json or .json5")
                recipe = _parse_json_or_json5_safe(bytes(content))
                recipe_id = str(recipe.get("recipe_id", "")).strip()
                if not recipe_id:
                    raise ValueError("recipe_id is required in recipe file")
                existing_ids = {str(row.get("recipe_id", "")).strip() for row in list_recipes(valid_domain)}
                already_exists = recipe_id in existing_ids
                if already_exists and not overwrite:
                    self._json_response(
                        {"status": "overwrite_required", "error": f"recipe_id already exists: {recipe_id}", "recipe_id": recipe_id},
                        status=HTTPStatus.CONFLICT,
                    )
                    return
                attached = False
                updated_rows: list[dict] = []
                attach_changed = False
                if attach_to_url:
                    normalized_url = normalize_seed_url(raw_url)
                    if not normalized_url:
                        raise ValueError("url is required when attach_to_url=true")
                    seed_payload = read_seed_urls(valid_domain)
                    rows = [row for row in seed_payload.get("urls", []) if isinstance(row, dict)]
                    match = next((row for row in rows if str(row.get("url", "")) == normalized_url), None)
                    if match is None:
                        raise ValueError("url not found in seed_urls")
                    current_ids = match.get("recipe_ids", [])
                    normalized_ids = list(current_ids) if isinstance(current_ids, list) else []
                    recipe_ids = sorted({str(item).strip() for item in normalized_ids if str(item).strip()} | {recipe_id})
                    updated_rows = [dict(row) for row in rows]
                    for row in updated_rows:
                        if str(row.get("url", "")) == normalized_url:
                            existing_ids = row.get("recipe_ids", [])
                            normalized_existing = list(existing_ids) if isinstance(existing_ids, list) else []
                            canonical_existing = sorted({str(item).strip() for item in normalized_existing if str(item).strip()})
                            if recipe_ids != canonical_existing:
                                attach_changed = True
                            row["recipe_ids"] = recipe_ids
                saved_recipe = upsert_recipe(valid_domain, _compat_recipe_for_storage(recipe))
                if attach_to_url and attach_changed:
                    _write_seed_rows_preserve_order(valid_domain, updated_rows)
                if attach_to_url:
                    attached = True
                _register_domain(valid_domain)
                self._json_response(
                    {
                        "status": "ok",
                        "error": "",
                        "recipe": saved_recipe,
                        "recipe_id": recipe_id,
                        "overwrote": already_exists,
                        "attached_to_url": attached,
                        "recipes": list_recipes(valid_domain),
                    }
                )
            except ValueError as exc:
                self._json_response({"status": "failed", "error": str(exc), "recipe_id": recipe_id}, status=HTTPStatus.BAD_REQUEST)
            except Exception as exc:
                self._json_response({"status": "failed", "error": str(exc), "recipe_id": recipe_id}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if self.path == "/api/recipes/delete":
            payload = self._read_json_payload()
            domain = str(payload.get("domain", ""))
            recipe_id = str(payload.get("recipe_id", "")).strip()
            try:
                valid_domain = validate_domain(_normalize_testsite_domain_key(domain))
                if not recipe_id:
                    raise ValueError("recipe_id is required")
                recipes = delete_recipe(valid_domain, recipe_id)
                seed_payload = read_seed_urls(valid_domain)
                rows = [row for row in seed_payload.get("urls", []) if isinstance(row, dict)]
                merged_rows: list[dict] = []
                changed = False
                for row in rows:
                    next_row = dict(row)
                    current_ids = row.get("recipe_ids", [])
                    normalized_ids = list(current_ids) if isinstance(current_ids, list) else []
                    filtered_ids = [rid for rid in normalized_ids if str(rid).strip() and str(rid).strip() != recipe_id]
                    if filtered_ids != normalized_ids:
                        changed = True
                    next_row["recipe_ids"] = filtered_ids
                    merged_rows.append(next_row)
                saved = _write_seed_rows_preserve_order(valid_domain, merged_rows) if changed else seed_payload
                self._json_response({"status": "ok", "error": "", "recipe_id": recipe_id, "recipes": recipes, "seed_urls": saved})
            except ValueError as exc:
                self._json_response({"status": "failed", "error": str(exc), "recipe_id": recipe_id}, status=HTTPStatus.BAD_REQUEST)
            except Exception as exc:
                self._json_response({"status": "failed", "error": str(exc), "recipe_id": recipe_id}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if self.path == "/api/seed-urls/row-upsert":
            payload = self._read_json_payload()
            domain = str(payload.get("domain", ""))
            row = payload.get("row")
            try:
                valid_domain = validate_domain(_normalize_testsite_domain_key(domain))
                if not isinstance(row, dict):
                    raise ValueError("row object is required")
                existing = read_seed_urls(valid_domain)
                rows = [r for r in existing.get("urls", []) if isinstance(r, dict)]
                normalized_url = normalize_seed_url(str(row.get("url", "")))
                if normalized_url is None:
                    raise ValueError("row.url is required")
                merged = [r for r in rows if str(r.get("url")) != normalized_url]
                merged.append({
                    "url": normalized_url,
                    "description": row.get("description"),
                    "recipe_ids": row.get("recipe_ids", []),
                    "active": bool(row.get("active", True)),
                })
                saved = write_seed_rows(valid_domain, merged)
                _register_domain(valid_domain)
                self._json_response(saved)
            except ValueError as exc:
                self._json_response(
                    {
                        "status": "failed",
                        "error": str(exc),
                        "action": "start_capture",
                        "previous_state": "not_started",
                        "resulting_state": "failed",
                        "next_expected_state": "not_started",
                        "remediation": ["check capture runner prerequisites", "see logs", "verify env config"],
                    },
                    status=HTTPStatus.BAD_REQUEST,
                )
            except Exception as exc:
                self._json_response(
                    {
                        "status": "failed",
                        "error": str(exc),
                        "action": "start_capture",
                        "previous_state": "not_started",
                        "resulting_state": "failed",
                        "next_expected_state": "not_started",
                        "remediation": ["check capture runner prerequisites", "see logs", "verify env config"],
                    },
                    status=HTTPStatus.INTERNAL_SERVER_ERROR,
                )
            return

        if self.path == "/api/capture/plan":
            payload = self._read_json_payload()
            try:
                domain = validate_domain(_normalize_testsite_domain_key(str(payload.get("domain", "")).strip()))
                languages = sorted({str(v).strip() for v in payload.get("languages", []) if str(v).strip()})
                viewports = sorted({str(v).strip() for v in payload.get("viewports", []) if str(v).strip()})
                tiers = sorted({str(v).strip() for v in payload.get("user_tiers", []) if str(v).strip()}) or [""]
                include_recipes = bool(payload.get("include_recipes", False))
                if not languages or not viewports:
                    raise ValueError("languages and viewports are required")
                seed_payload = read_seed_urls(domain)
                planning_rows = []
                for row in seed_payload.get("urls", []):
                    if not isinstance(row, dict) or not row.get("active", True):
                        continue
                    recipe_ids = list(row.get("recipe_ids", [])) if include_recipes else []
                    planning_rows.append({"url": row.get("url"), "recipe_ids": recipe_ids})
                recipes = load_recipes_for_planner(domain)
                output = _expand_capture_plan(domain, planning_rows, languages, viewports, tiers, recipes)
                self._json_response({"jobs": output, "count": len(output)})
            except ValueError as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            except Exception as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if self.path == "/api/capture/start":
            payload = self._read_json_payload()
            domain = str(payload.get("domain", "")).strip()
            try:
                run_id = str(payload.get("run_id", "")).strip() or str(uuid.uuid4())
                run_id = _validate_run_id(run_id)
            except ValueError as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            language = str(payload.get("language", "en")).strip() or "en"
            viewport_kind = str(payload.get("viewport_kind", "desktop")).strip() or "desktop"
            state = str(payload.get("state", "guest")).strip() or "guest"
            user_tier = payload.get("user_tier") or None
            runtime_payload = {"domain": domain, "run_id": run_id, "language": language, "viewport_kind": viewport_kind, "state": state, "user_tier": user_tier}
            try:
                load_phase1_runtime_config(runtime_payload)
                valid_domain = validate_domain(_normalize_testsite_domain_key(domain))
                _register_domain(valid_domain)
                _set_last_used_first_run_domain(valid_domain)
                job_id = f"phase1-{run_id}-{language}-{viewport_kind}-{state}"
                _upsert_job_status(valid_domain, run_id, {"job_id": job_id, "status": "queued", "context": runtime_payload})
                t = threading.Thread(target=_run_phase1_async, args=(job_id, runtime_payload), daemon=True)
                t.start()
                self._json_response({"status": "started", "job_id": job_id, "run_id": run_id})
            except ValueError as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            except Exception as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if self.path in {"/api/capture/review", "/api/capture/reviews"}:
            payload = self._read_json_payload()
            try:
                result = _persist_capture_review(payload)
                self._json_response(result)
            except ValueError as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            except Exception as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if self.path == "/api/capture/rerun":
            payload = self._read_json_payload()
            try:
                runtime_payload = _parse_rerun_payload(payload)
                job_id = f"rerun-{runtime_payload['run_id']}-{runtime_payload['capture_context_id']}-{int(time.time())}"
                _upsert_job_status(runtime_payload["domain"], runtime_payload["run_id"], {"job_id": job_id, "status": "queued", "context": runtime_payload, "type": "rerun"})
                t = threading.Thread(target=_run_rerun_async, args=(job_id, runtime_payload), daemon=True)
                t.start()
                self._json_response({
                    "job_id": job_id,
                    "status": "running",
                    "type": "rerun",
                    "context": {
                        "domain": runtime_payload["domain"],
                        "run_id": runtime_payload["run_id"],
                        "url": runtime_payload["url"],
                        "viewport_kind": runtime_payload["viewport_kind"],
                        "state": runtime_payload["state"],
                        "language": runtime_payload["language"],
                        "user_tier": runtime_payload["user_tier"],
                        "capture_context_id": runtime_payload["capture_context_id"],
                    },
                }, status=HTTPStatus.ACCEPTED)
            except ValueError as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            except Exception as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if self.path in {"/api/element-type-whitelist", "/api/element-type-whitelist/remove"}:
            if not self._require_auth(api=True):
                return
            payload = self._read_json_payload()
            domain = str(payload.get("domain", "")).strip()
            if not domain:
                self._json_response({"status": "error", "message": "domain is required"}, status=HTTPStatus.BAD_REQUEST)
                return
            try:
                domain = validate_domain(_normalize_testsite_domain_key(domain))
                if self.path.endswith("/remove"):
                    signature_key = str(payload.get("signature_key", "")).strip()
                    if not signature_key:
                        self._json_response({"status": "error", "message": "domain and signature_key are required"}, status=HTTPStatus.BAD_REQUEST)
                        return
                    values = _remove_domain_element_type_whitelist(domain, signature_key)
                    added_entry = {}
                else:
                    values, added_entry = _add_domain_element_type_whitelist(domain, payload)
                self._json_response({"status": "ok", "domain": domain, "entries": values, "added_entry": added_entry})
            except ValueError as exc:
                status = HTTPStatus.BAD_REQUEST if str(exc) == "element_signature_requires_specific_attributes" else HTTPStatus.INTERNAL_SERVER_ERROR
                state = "invalid_request" if status == HTTPStatus.BAD_REQUEST else "artifact_invalid"
                self._json_response({"error": str(exc), "status": state}, status=status)
            return

        if self.path == "/api/rules":
            payload = self._read_json_payload()
            domain = str(payload.get("domain", "")).strip()
            run_id = str(payload.get("run_id", "")).strip()
            try:
                if run_id:
                    run_id = _validate_run_id(run_id)
            except ValueError as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            item_id = str(payload.get("item_id", "")).strip()
            url = str(payload.get("url", "")).strip()
            requested_decision = str(payload.get("decision", payload.get("rule_type", ""))).strip()
            rule_type = _to_rule_type(requested_decision)
            allowed = {"IGNORE_ENTIRE_ELEMENT", "MASK_VARIABLE", "ALWAYS_COLLECT"}
            if not domain or not run_id or not item_id or not url or rule_type not in allowed:
                self._json_response({"status": "error", "message": "domain, run_id, item_id, url and valid decision/rule_type required"}, status=HTTPStatus.BAD_REQUEST)
                return
            decision = {
                "capture_context_id": str(payload.get("capture_context_id", "")),
                "item_id": item_id,
                "url": url,
                "state": str(payload.get("state", "")),
                "language": str(payload.get("language", "")),
                "viewport_kind": str(payload.get("viewport_kind", "")),
                "user_tier": payload.get("user_tier"),
                "rule_type": rule_type,
                "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            saved = _upsert_phase2_decision(domain, run_id, decision)
            self._json_response({"status": "ok", "decision": saved, "rule_type": saved.get("rule_type"), "source_ref": {"item_id": item_id, "url": url, "capture_context_id": decision.get("capture_context_id", "")}})
            return

        # Phase 0 trigger — real pipeline
        if self.path == "/api/phase0/run":
            payload = self._read_json_payload()
            domain = payload.get("domain", "").strip()
            if not domain:
                self._json_response({"status": "error", "message": "domain required"}, status=HTTPStatus.BAD_REQUEST)
                return
            try:
                run_id = _validate_run_id(payload.get("run_id") or str(uuid.uuid4()))
            except ValueError as exc:
                self._json_response({"status": "error", "message": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            job_id = f"phase0-{run_id}"
            t = threading.Thread(
                target=_run_phase0_async, args=(job_id, domain, run_id), daemon=True
            )
            t.start()
            self._json_response({"status": "started", "job_id": job_id, "run_id": run_id})
            return

        # Phase 1 trigger — real pipeline
        if self.path == "/api/phase1/run":
            payload = self._read_json_payload()
            domain = payload.get("domain", "").strip()
            run_id = payload.get("run_id", "").strip()
            try:
                if run_id:
                    run_id = _validate_run_id(run_id)
            except ValueError as exc:
                self._json_response({"status": "error", "message": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            if not domain or not run_id:
                self._json_response({"status": "error", "message": "domain and run_id required"}, status=HTTPStatus.BAD_REQUEST)
                return
            runtime_payload = {
                "domain": domain,
                "run_id": run_id,
                "language": payload.get("language", "en"),
                "viewport_kind": payload.get("viewport_kind", "desktop"),
                "state": payload.get("state", "guest"),
                "user_tier": payload.get("user_tier") or None,
            }
            try:
                config = load_phase1_runtime_config(runtime_payload)
            except ValueError as exc:
                self._json_response({"status": "error", "message": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            job_id = f"phase1-{config.run_id}-{config.language}-{config.viewport_kind}-{config.state}"
            _register_domain(domain)
            _upsert_job_status(domain, run_id, {"job_id": job_id, "status": "queued", "context": runtime_payload})
            t = threading.Thread(
                target=_run_phase1_async,
                args=(job_id, runtime_payload),
                daemon=True,
            )
            t.start()
            self._json_response({"status": "started", "job_id": job_id, "run_id": run_id})
            return

        # Phase 2 — save a single template rule to GCS
        if self.path == "/api/phase2/rule":
            payload = self._read_json_payload()
            domain = payload.get("domain", "").strip()
            run_id = payload.get("run_id", "").strip()
            try:
                if run_id:
                    run_id = _validate_run_id(run_id)
            except ValueError as exc:
                self._json_response({"status": "error", "message": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            item_id = payload.get("item_id", "").strip()
            url = payload.get("url", "").strip()
            rule_type = payload.get("rule_type", "").strip()
            note = payload.get("note") or None
            allowed = {"IGNORE_ENTIRE_ELEMENT", "MASK_VARIABLE", "ALWAYS_COLLECT"}
            if not all([domain, run_id, item_id, url]) or rule_type not in allowed:
                self._json_response({"status": "error", "message": "domain, run_id, item_id, url and valid rule_type required"}, status=HTTPStatus.BAD_REQUEST)
                return
            try:
                from pipeline.run_phase2 import run as phase2_run
                rule = phase2_run(domain=domain, run_id=run_id, item_id=item_id, url=url, rule_type=rule_type, note=note)
                self._json_response({"status": "ok", "rule": rule})
            except Exception as exc:
                self._json_response({"status": "error", "message": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        # Testbench module run endpoint
        if self.path == "/api/testbench/run":
            payload = self._read_json_payload()
            module_id = str(payload.get("module_id", "")).strip()
            case_key = payload.get("case_key") or payload.get("case_id")
            inline_payload = payload.get("input") if isinstance(payload.get("input"), dict) else None
            if not module_id:
                self._json_response({"status": "error", "message": "module_id required"}, status=HTTPStatus.BAD_REQUEST)
                return
            result = run_module_test(module_id, case_key if isinstance(case_key, str) else None, inline_payload)
            self._json_response(result)
            return

        if self.path == "/api/workflow/start-capture":
            payload = self._read_json_payload()
            domain = str(payload.get("domain", "")).strip()
            try:
                run_id = str(payload.get("run_id", "")).strip() or str(uuid.uuid4())
                run_id = _validate_run_id(run_id)
            except ValueError as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            requested_display_name = _normalize_optional_string(payload.get("display_name"))
            language = str(payload.get("language", "en")).strip() or "en"
            viewport_kind = str(payload.get("viewport_kind", "desktop")).strip() or "desktop"
            state = str(payload.get("state", "guest")).strip() or "guest"
            user_tier = payload.get("user_tier") or None
            runtime_payload = {"domain": domain, "run_id": run_id, "language": language, "viewport_kind": viewport_kind, "state": state, "user_tier": user_tier}
            try:
                load_phase1_runtime_config(runtime_payload)
                valid_domain = validate_domain(_normalize_testsite_domain_key(domain))
                _register_domain(valid_domain)
                _set_last_used_first_run_domain(valid_domain)
                existing_run = next((row for row in _load_runs(valid_domain).get("runs", []) if str(row.get("run_id", "")).strip() == run_id), None)
                existing_display_name = _normalize_optional_string((existing_run or {}).get("display_name"))
                is_new_run = existing_run is None
                display_name = requested_display_name or existing_display_name
                if display_name is None and is_new_run:
                    display_name = _default_run_display_name()
                job_id = f"phase1-{run_id}-{language}-{viewport_kind}-{state}"
                _upsert_job_status(
                    valid_domain,
                    run_id,
                    {"job_id": job_id, "status": "queued", "context": runtime_payload, "type": "capture", "display_name": display_name},
                )
                t = threading.Thread(target=_run_phase1_async, args=(job_id, runtime_payload), daemon=True)
                t.start()
                self._json_response({
                    "status": "started",
                    "job_id": job_id,
                    "run_id": run_id,
                    "display_name": display_name,
                    "action": "start_capture",
                    "previous_state": "run_not_started",
                    "resulting_state": "phase_in_progress",
                    "next_expected_state": "phase_completed",
                })
            except ValueError as exc:
                self._json_response(
                    {
                        "status": "failed",
                        "error": str(exc),
                        "action": "start_capture",
                        "previous_state": "not_started",
                        "resulting_state": "failed",
                        "next_expected_state": "not_started",
                        "remediation": ["check capture runner prerequisites", "see logs", "verify env config"],
                    },
                    status=HTTPStatus.BAD_REQUEST,
                )
            except Exception as exc:
                self._json_response(
                    {
                        "status": "failed",
                        "error": str(exc),
                        "action": "start_capture",
                        "previous_state": "not_started",
                        "resulting_state": "failed",
                        "next_expected_state": "not_started",
                        "remediation": ["check capture runner prerequisites", "see logs", "verify env config"],
                    },
                    status=HTTPStatus.INTERNAL_SERVER_ERROR,
                )
            return

        if self.path == "/api/workflow/rerun-context":
            payload = self._read_json_payload()
            try:
                runtime_payload = _parse_rerun_payload(payload)
                job_id = f"rerun-{runtime_payload['run_id']}-{runtime_payload['capture_context_id']}-{int(time.time())}"
                _upsert_job_status(runtime_payload["domain"], runtime_payload["run_id"], {"job_id": job_id, "status": "queued", "context": runtime_payload, "type": "rerun"})
                t = threading.Thread(target=_run_rerun_async, args=(job_id, runtime_payload), daemon=True)
                t.start()
                self._json_response({"job_id": job_id, "status": "running", "action": "rerun_context", "type": "rerun", "previous_state": "phase_completed", "resulting_state": "phase_in_progress", "next_expected_state": "phase_completed", "context": runtime_payload}, status=HTTPStatus.ACCEPTED)
            except ValueError as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            except Exception as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if self.path == "/api/workflow/generate-eligible-dataset":
            payload = self._read_json_payload()
            domain = payload.get("domain", "").strip()
            run_id = payload.get("run_id", "").strip()
            try:
                if run_id:
                    run_id = _validate_run_id(run_id)
            except ValueError as exc:
                self._json_response({"status": "error", "message": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            if not domain or not run_id:
                self._json_response({"status": "error", "message": "domain and run_id required"}, status=HTTPStatus.BAD_REQUEST)
                return
            if not _capture_artifacts_ready(domain, run_id):
                self._json_response(
                    _structured_not_ready(
                        "generate_eligible_dataset",
                        "capture artifacts missing: page_screenshots.json and/or collected_items.json",
                        previous_state="capture_not_ready",
                        next_expected_state="capture_ready",
                    ),
                    status=HTTPStatus.CONFLICT,
                )
                return
            job_id = f"phase3-{run_id}"
            _upsert_job_status(domain, run_id, {"job_id": job_id, "status": "queued", "phase": "3", "type": "eligible_dataset"})
            t = threading.Thread(target=_run_phase3_async, args=(job_id, domain, run_id), daemon=True)
            t.start()
            self._json_response({"status": "started", "job_id": job_id, "run_id": run_id, "action": "generate_eligible_dataset", "previous_state": "eligible_dataset_pending", "resulting_state": "in_progress", "next_expected_state": "eligible_dataset_ready"})
            return

        if self.path == "/api/workflow/generate-issues":
            payload = self._read_json_payload()
            domain = str(payload.get("domain", "")).strip()
            try:
                run_id = _validate_run_id(str(payload.get("run_id", "")).strip())
                en_run_id = str(payload.get("en_run_id", "")).strip() or run_id
                en_run_id = _validate_run_id(en_run_id)
            except ValueError as exc:
                self._json_response({"status": "error", "message": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            if not domain or not run_id:
                self._json_response({"status": "error", "message": "domain and run_id required"}, status=HTTPStatus.BAD_REQUEST)
                return
            if not _artifact_exists(domain, run_id, "eligible_dataset.json"):
                self._json_response(
                    _structured_not_ready(
                        "generate_issues",
                        "eligible_dataset artifact missing",
                        previous_state="eligible_dataset_not_ready",
                        next_expected_state="eligible_dataset_ready",
                    ),
                    status=HTTPStatus.CONFLICT,
                )
                return
            job_id = f"phase6-{run_id}"
            _upsert_job_status(domain, run_id, {"job_id": job_id, "status": "queued", "phase": "6", "type": "issues", "en_run_id": en_run_id})
            t = threading.Thread(target=_run_phase6_async, args=(job_id, domain, run_id, en_run_id), daemon=True)
            t.start()
            self._json_response({"status": "started", "job_id": job_id, "run_id": run_id, "en_run_id": en_run_id, "action": "generate_issues", "previous_state": "issue_generation_pending", "resulting_state": "in_progress", "next_expected_state": "issues_ready"})
            return

        # Phase 3 trigger — EN Reference Build
        if self.path == "/api/phase3/run":
            payload = self._read_json_payload()
            domain = payload.get("domain", "").strip()
            run_id = payload.get("run_id", "").strip()
            try:
                if run_id:
                    run_id = _validate_run_id(run_id)
            except ValueError as exc:
                self._json_response({"status": "error", "message": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            if not domain or not run_id:
                self._json_response({"status": "error", "message": "domain and run_id required"}, status=HTTPStatus.BAD_REQUEST)
                return
            job_id = f"phase3-{run_id}"
            t = threading.Thread(
                target=_run_phase3_async, args=(job_id, domain, run_id), daemon=True
            )
            t.start()
            self._json_response({"status": "started", "job_id": job_id, "run_id": run_id})
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")


    def _check_languages_ui(self) -> check_languages_ui.CheckLanguagesUIController:
        return check_languages_ui.CheckLanguagesUIController(
            send_response=self.send_response,
            send_header=self.send_header,
            end_headers=self.end_headers,
            serve_template=self._serve_template,
            ensure_csrf_cookie=self._ensure_csrf_cookie,
            build_cookie_header=self._build_cookie_header,
            default_check_languages_domain=_default_check_languages_domain,
            load_check_language_runs=_load_check_language_runs,
            find_in_progress_check_languages_job=_find_in_progress_check_languages_job,
            latest_check_languages_job=_latest_check_languages_job,
            generate_target_run_id=_generate_target_run_id,
            upsert_job_status=_upsert_job_status,
            prepare_check_languages_async=_prepare_check_languages_async,
            run_check_languages_llm_async=_run_check_languages_llm_async,
            check_languages_llm_preflight_error=_check_languages_llm_preflight_error,
            csrf_cookie_name=CSRF_COOKIE,
            session_max_age_seconds=SESSION_MAX_AGE_SECONDS,
        )

    def _redirect_check_languages(self, payload: dict[str, str], *, message: str = "", level: str = "") -> None:
        self._check_languages_ui().redirect_check_languages(payload, message=message, level=level)

    def _start_check_languages(self, payload: dict[str, str]) -> None:
        self._check_languages_ui().start_check_languages(payload)

    def _serve_check_languages_page(self, query: dict[str, list[str]]) -> None:
        self._check_languages_ui().serve_check_languages_page(query)

    def _serve_result_files_page(self, query: dict[str, list[str]]) -> None:
        domain_options = sorted(
            {_normalize_check_languages_domain(item) for item in _list_domains() if _is_supported_check_languages_domain(item)}
        )
        selected_domain = _normalize_check_languages_domain(str((query.get("domain") or [""])[0]).strip())
        if not selected_domain and domain_options:
            selected_domain = _normalize_check_languages_domain(_default_check_languages_domain())
        if selected_domain and selected_domain not in domain_options:
            domain_options.append(selected_domain)
            domain_options = sorted(set(domain_options))

        runs = _load_check_language_runs(selected_domain) if selected_domain else []
        selected_run_id = str((query.get("run_id") or [""])[0]).strip()
        if not selected_run_id and runs:
            selected_run_id = str(runs[0].get("run_id", "")).strip()

        selected_run: dict[str, Any] | None = None
        run_options: list[str] = []
        for run in runs:
            run_id = str(run.get("run_id", "")).strip()
            run_domain = str(run.get("domain", "")).strip()
            if not run_id or not run_domain:
                continue
            if selected_run is None and run_id == selected_run_id:
                selected_run = run
            selected_attr = ' selected="selected"' if run_id == selected_run_id else ""
            run_options.append(
                f'<option value="{_h(run_id)}"{selected_attr}>{_h(_run_display_label(run))} · {_h(run_domain)}</option>'
            )

        if selected_run is None and runs:
            selected_run = runs[0]
            selected_run_id = str(selected_run.get("run_id", "")).strip()
            run_options = []
            for run in runs:
                run_id = str(run.get("run_id", "")).strip()
                run_domain = str(run.get("domain", "")).strip()
                if not run_id or not run_domain:
                    continue
                selected_attr = ' selected="selected"' if run_id == selected_run_id else ""
                run_options.append(
                    f'<option value="{_h(run_id)}"{selected_attr}>{_h(_run_display_label(run))} · {_h(run_domain)}</option>'
                )

        domain_options_html = "".join(
            f'<option value="{_h(item)}"{" selected=\"selected\"" if item == selected_domain else ""}>{_h(item)}</option>'
            for item in domain_options
        ) or '<option value="">No supported domains found</option>'
        run_options_html = "".join(run_options) or '<option value="">No runs found</option>'

        artifact_sections = [
            ("Request sent to LLM", "check_languages_llm_request.json"),
            ("Raw LLM response", "check_languages_llm_raw_response.json"),
            ("Parsed result", "issues.json"),
        ]
        artifact_sections_html = "<p>No run selected.</p>"
        if selected_run is not None:
            selected_run_domain = str(selected_run.get("domain", "")).strip()
            blocks: list[str] = []
            for label, filename in artifact_sections:
                artifact = _result_file_artifact_status(selected_run_domain, selected_run_id, filename)
                preview = "Unavailable"
                if artifact["status"] == "valid":
                    preview = json.dumps(artifact["payload"], ensure_ascii=False, indent=2)
                status_line = f'<p>Status: <strong>{_h(str(artifact["status"]))}</strong></p>'
                error_line = f"<p>Error: {_h(str(artifact['error']))}</p>" if artifact["error"] else ""
                blocks.append(
                    f"<details>"
                    f"<summary>{_h(label)} ({_h(filename)})</summary>"
                    f"{status_line}"
                    f"<p>Path: <code>{_h(str(artifact['path']))}</code></p>"
                    f"{error_line}"
                    f"<pre>{_h(preview)}</pre>"
                    f"</details>"
                )
            artifact_sections_html = "".join(blocks)

        self._serve_template(
            "result-files.html",
            replacements={
                "{{result_files_domain_options}}": domain_options_html,
                "{{result_files_run_options}}": run_options_html,
                "{{result_files_selected_domain}}": _h(selected_domain or "—"),
                "{{result_files_selected_run_id}}": _h(selected_run_id or "—"),
                "{{result_files_artifacts}}": artifact_sections_html,
            },
        )


    def _serve_pulls_page(self, query: dict[str, list[str]]) -> None:
        domain = _normalize_check_languages_domain(str(query.get("domain", [""])[0]))
        selected_run_id = str(query.get("run_id", [""])[0]).strip()
        selected_en_run_id = str(query.get("en_run_id", [""])[0]).strip()

        domain_options_source = SUPPORTED_CHECK_LANGUAGE_DOMAINS
        if domain and domain not in domain_options_source:
            domain_options_source = [*SUPPORTED_CHECK_LANGUAGE_DOMAINS, domain]
        if not domain:
            domain = _default_check_languages_domain()
        if domain and domain not in domain_options_source:
            domain_options_source = [*domain_options_source, domain]

        first_run_options: list[str] = ['<option value="">Select First Run</option>']
        en_options: list[str] = ['<option value="">Select English reference run</option>']
        try:
            validate_domain(_normalize_testsite_domain_key(domain))
            runs_payload = _load_runs(domain)
            runs = runs_payload.get("runs", []) if isinstance(runs_payload, dict) else []
            sorted_runs = _sort_runs_newest_first(runs)
            if not selected_run_id:
                selected_run_id = str(((sorted_runs[0] if sorted_runs else {}) or {}).get("run_id", "")).strip()
            for run in sorted_runs:
                run_id = str(run.get("run_id", "")).strip()
                if not run_id:
                    continue
                selected_attr = ' selected="selected"' if run_id == selected_run_id else ""
                first_run_options.append(f'<option value="{_h(run_id)}"{selected_attr}>{_h(_run_display_label(run))}</option>')

            check_runs = _load_check_language_runs(domain)
            en_candidates = [row for row in check_runs if _run_is_en_reference_candidate(row)]
            if not selected_en_run_id:
                selected_en_run_id = _latest_successful_en_standard_run_id(domain, en_candidates) or _default_english_reference_run_id(en_candidates)
            for run in sorted(en_candidates, key=lambda row: (row.get("created_at", ""), row.get("run_id", "")), reverse=True):
                run_id = str(run.get("run_id", "")).strip()
                if not run_id:
                    continue
                selected_attr = ' selected="selected"' if run_id == selected_en_run_id else ""
                en_options.append(f'<option value="{_h(run_id)}"{selected_attr}>{_h(_run_display_label(run))}</option>')
            if len(en_options) == 1:
                en_options = ['<option value="">No English runs found</option>']
        except ValueError:
            first_run_options = ['<option value="">No First Runs found</option>']
            en_options = ['<option value="">No English runs found</option>']

        self._serve_template(
            "pulls.html",
            replacements={
                "{{pulls_domain_options}}": "".join(
                    [
                        f'<option value="{_h(item)}"{" selected=\"selected\"" if item == domain else ""}>{_h(item)}</option>'
                        for item in domain_options_source
                    ]
                ),
                "{{pulls_first_run_options}}": "".join(first_run_options),
                "{{pulls_en_run_options}}": "".join(en_options),
            },
        )

    def _serve_template(
        self,
        name: str,
        *,
        status: HTTPStatus = HTTPStatus.OK,
        replacements: dict[str, str] | None = None,
        extra_set_cookies: list[str] | None = None,
    ) -> None:
        path = TEMPLATES_DIR / name
        if not path.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "Template not found")
            return
        html = self._read_template_cached(path)
        html = re.sub(
            r"(<body\b[^>]*>)",
            r"\1\n<script>document.documentElement.classList.add('i18n-loading');</script>",
            html,
            count=1,
            flags=re.IGNORECASE,
        )
        loader_html = '<div class="i18n-loader-overlay" aria-hidden="true"><div class="i18n-loader"></div></div>'
        html = html.replace("</body>", f"  {loader_html}\n</body>", 1)
        header_path = TEMPLATES_DIR / "_header.html"
        header_html = self._read_template_cached(header_path) if header_path.exists() else ""
        html = html.replace("{{header}}", header_html)
        html = html.replace("</head>", '  <link rel="icon" type="image/png" href="/favicon.png" />\n</head>', 1)
        html = html.replace(
            "{{logout_button}}",
            '<button id="logoutButton" type="button" data-i18n="nav.logout">Logout</button>' if self._auth_enabled() else "",
        )
        if replacements:
            for key, value in replacements.items():
                html = html.replace(key, value)
        data = html.encode("utf-8")
        self.send_response(status)
        if extra_set_cookies:
            for set_cookie in extra_set_cookies:
                self.send_header("Set-Cookie", set_cookie)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


    def _serve_favicon(self) -> None:
        path = BASE_DIR / "favicon.png"
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Favicon not found")
            return
        self._send_file(path, "image/png")

    def _serve_static(self, relative_path: str) -> None:
        path = STATIC_DIR / relative_path
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Static file not found")
            return
        content_type = self._get_content_type(path)
        self._send_file(path, content_type)

    def _serve_fixture(self, relative_path: str) -> None:
        normalized = relative_path.strip("/")
        if not normalized:
            normalized = "index.html"
        elif not Path(normalized).suffix:
            normalized = f"{normalized}/index.html"

        path = FIXTURE_DIR / normalized
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Fixture file not found")
            return
        self._send_file(path, self._get_content_type(path))

    def _get_content_type(self, path: Path) -> str:
        content_type = "text/plain; charset=utf-8"
        if path.suffix == ".html":
            content_type = "text/html; charset=utf-8"
        elif path.suffix == ".css":
            content_type = "text/css; charset=utf-8"
        elif path.suffix == ".js":
            content_type = "application/javascript; charset=utf-8"
        elif path.suffix == ".svg":
            content_type = "image/svg+xml"
        elif path.suffix == ".json":
            content_type = "application/json; charset=utf-8"
        elif path.suffix == ".png":
            content_type = "image/png"
        elif path.suffix == ".ico":
            content_type = "image/x-icon"
        return content_type

    def _send_file(self, path: Path, content_type: str) -> None:
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json_response(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _read_json_payload(self) -> dict[str, str]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return {}
        if not isinstance(payload, dict):
            return {}
        return payload

    def _read_form_payload(self) -> dict[str, str]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        parsed = parse_qs(raw, keep_blank_values=True)
        payload: dict[str, str] = {}
        for key, values in parsed.items():
            if not values:
                continue
            chosen = next((value for value in reversed(values) if value != ""), values[-1])
            payload[key] = chosen
        return payload

    def _read_multipart_form_payload(self) -> tuple[dict[str, str], dict[str, dict[str, object]]]:
        content_type = str(self.headers.get("Content-Type", ""))
        if "multipart/form-data" not in content_type.lower():
            return {}, {}
        fields: dict[str, str] = {}
        files: dict[str, dict[str, object]] = {}
        boundary_match = re.search(r'boundary="?([^";]+)"?', content_type, flags=re.IGNORECASE)
        if not boundary_match:
            return fields, files
        boundary = boundary_match.group(1).encode("utf-8")
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return fields, files
        raw = self.rfile.read(length)
        delimiter = b"--" + boundary
        parts = raw.split(delimiter)
        for part in parts:
            if not part:
                continue
            chunk = part
            if chunk.startswith(b"\r\n"):
                chunk = chunk[2:]
            if chunk.endswith(b"--\r\n"):
                chunk = chunk[:-4]
            elif chunk.endswith(b"--"):
                chunk = chunk[:-2]
            elif chunk.endswith(b"\r\n"):
                chunk = chunk[:-2]
            if not chunk:
                continue
            if b"\r\n\r\n" not in chunk:
                continue
            header_block, body = chunk.split(b"\r\n\r\n", 1)
            header_lines = header_block.decode("utf-8", errors="ignore").split("\r\n")
            disposition = next((line for line in header_lines if line.lower().startswith("content-disposition:")), "")
            if not disposition:
                continue
            name_match = re.search(r'name="([^"]+)"', disposition)
            if not name_match:
                continue
            field_name = name_match.group(1)
            file_match = re.search(r'filename="([^"]*)"', disposition)
            content_type_line = next((line for line in header_lines if line.lower().startswith("content-type:")), "")
            part_content_type = content_type_line.split(":", 1)[1].strip() if ":" in content_type_line else ""
            if file_match:
                files[field_name] = {
                    "filename": file_match.group(1),
                    "content_type": part_content_type,
                    "content": bytes(body),
                }
                continue
            decoded = body.decode("utf-8", errors="ignore")
            if field_name not in fields or decoded:
                fields[field_name] = decoded
        return fields, files

    def log_message(self, format, *args):  # noqa: A002
        pass  # suppress default request logging for cleaner Cloud Run logs


def run(host: str = "0.0.0.0", port: int = 8080) -> None:
    server = ThreadingHTTPServer((host, port), SkeletonHandler)
    print(f"Polyglot Watchdog UI running on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    run(port=port)
