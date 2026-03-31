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
    _jobs[job_id] = {
        "status": "running",
        "phase": "check_languages",
        "domain": domain,
        "run_id": target_run_id,
        "en_run_id": en_run_id,
        "target_language": target_language,
        "target_url": target_url,
    }
    from pipeline.run_phase1 import main as phase1_main
    from pipeline.run_phase3 import run as phase3_run

    try:
        _upsert_job_status(domain, target_run_id, {
            "job_id": job_id,
            "status": "running",
            "type": "check_languages",
            "stage": "preparing_payload",
            "workflow_state": "preparing_payload",
            "en_run_id": en_run_id,
            "target_language": target_language,
            "target_url": target_url,
        })
        replay_jobs = _replay_scope_from_reference_run(domain, en_run_id, target_language, target_url)
    except Exception as exc:
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = str(exc)
        _upsert_job_status(domain, target_run_id, {
            "job_id": job_id,
            "status": "failed",
            "type": "check_languages",
            "stage": "preparing_target_run_failed",
            "workflow_state": "failed_before_llm",
            "en_run_id": en_run_id,
            "target_language": target_language,
            "target_url": target_url,
            "error": str(exc),
        })
        return

    try:
        _upsert_job_status(domain, target_run_id, {
            "job_id": job_id,
            "status": "running",
            "type": "check_languages",
            "stage": "running_target_capture",
            "workflow_state": "preparing_payload",
            "en_run_id": en_run_id,
            "target_language": target_language,
            "target_url": target_url,
            "contexts": len(replay_jobs),
        })
        asyncio.run(phase1_main(domain, target_run_id, target_language, "desktop", "baseline", None, jobs_override=replay_jobs, continue_on_error=True))
        _require_artifact_exists(domain, target_run_id, "page_screenshots.json")
        _require_artifact_exists(domain, target_run_id, "collected_items.json")
    except Exception as exc:
        replay_context = _replay_unit_diagnostics(
            exc,
            replay_jobs,
            target_url=target_url,
            en_run_id=en_run_id,
            target_run_id=target_run_id,
            target_language=target_language,
        )
        diagnostics = _build_exception_diagnostics(exc, stage="running_target_capture_failed", substage="phase1_replay", replay_context=replay_context)
        artifact_refs, artifact_error = _persist_check_languages_failure_artifacts_safe(domain, target_run_id, diagnostics)
        error = f"{diagnostics['exception_class']}: {diagnostics['message']}"
        if artifact_error:
            error = f"{error} (failure artifact persistence warning: {artifact_error})"
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["error"] = error
        failed_record = {
            "job_id": job_id,
            "status": "failed",
            "type": "check_languages",
            "stage": "running_target_capture_failed",
            "workflow_state": "failed_before_llm",
            "en_run_id": en_run_id,
            "target_language": target_language,
            "target_url": target_url,
            "error": error,
            "error_details": diagnostics,
            "failure_artifacts": artifact_refs,
        }
        if artifact_error:
            failed_record["failure_artifact_error"] = artifact_error
        _upsert_job_status(domain, target_run_id, failed_record)
        return

    try:
        _upsert_job_status(domain, target_run_id, {
            "job_id": job_id,
            "status": "running",
            "type": "check_languages",
            "stage": "assembling_payload",
            "workflow_state": "preparing_payload",
            "en_run_id": en_run_id,
            "target_language": target_language,
            "target_url": target_url,
        })
        phase3_run(domain=domain, run_id=target_run_id)
        _require_artifact_exists(domain, target_run_id, "eligible_dataset.json")
        payload_status = _check_languages_payload_status(domain, target_run_id)
        if not payload_status.get("ready"):
            raise ValueError("Prepared payload is incomplete or invalid")
        from pipeline.storage import write_json_artifact
        from pipeline.run_phase6 import build_prepared_llm_payload

        llm_input_payload = build_prepared_llm_payload(domain, en_run_id, target_run_id)
        review_contexts = llm_input_payload.get("review_contexts")
        first_review_context = review_contexts[0] if isinstance(review_contexts, list) and review_contexts else None
        llm_input_preview_payload = {
            "target_language": llm_input_payload.get("target_language"),
            "review_context_count": llm_input_payload.get("review_context_count"),
            "blocked_pages": llm_input_payload.get("blocked_pages") if isinstance(llm_input_payload.get("blocked_pages"), list) else [],
            "source_hashes": llm_input_payload.get("source_hashes") if isinstance(llm_input_payload.get("source_hashes"), dict) else {},
            "sample_review_context": first_review_context,
        }
        source_hashes = _check_languages_source_hashes(domain, en_run_id, target_run_id)
        llm_input_artifact_uri = write_json_artifact(domain, target_run_id, "check_languages_llm_input.json", llm_input_payload)
        write_json_artifact(domain, target_run_id, "check_languages_llm_input_preview.json", llm_input_preview_payload)
        write_json_artifact(domain, target_run_id, "check_languages_prepared_payload.json", {
            "en_run_id": en_run_id,
            "target_run_id": target_run_id,
            "target_language": target_language,
            "target_url": target_url,
            "prepared_at": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "payload_files": payload_status.get("files", []),
            "source_hashes": source_hashes,
            "llm_input_artifact": llm_input_artifact_uri,
            "llm_input_count": int(llm_input_payload.get("review_context_count", 0)),
        })
        _jobs[job_id]["status"] = "done"
        _upsert_job_status(domain, target_run_id, {
            "job_id": job_id,
            "status": "succeeded",
            "type": "check_languages",
            "stage": "prepared_for_llm",
            "workflow_state": "prepared_for_llm",
            "en_run_id": en_run_id,
            "target_language": target_language,
            "target_url": target_url,
        })
    except Exception as exc:
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = str(exc)
        _upsert_job_status(domain, target_run_id, {
            "job_id": job_id,
            "status": "failed",
            "type": "check_languages",
            "stage": "preparing_payload_failed",
            "workflow_state": "failed_before_llm",
            "en_run_id": en_run_id,
            "target_language": target_language,
            "target_url": target_url,
            "error": str(exc),
        })


def _run_check_languages_llm_async(job_id: str, domain: str, en_run_id: str, target_language: str, target_run_id: str, target_url: str) -> None:
    from pipeline.run_phase6 import run as phase6_run

    _jobs[job_id] = {"status": "running", "phase": "check_languages_llm", "domain": domain, "run_id": target_run_id}
    try:
        llm_preflight_error = _check_languages_llm_preflight_error()
        if llm_preflight_error:
            raise _CheckLanguagesLlmPreflightError(llm_preflight_error)
        prepared = _read_json_safe(domain, target_run_id, "check_languages_prepared_payload.json", None)
        if not isinstance(prepared, dict):
            raise ValueError("Prepared payload missing. Run Prepare language check payload first.")
        llm_input_artifact = str(prepared.get("llm_input_artifact", "")).strip()
        if llm_input_artifact:
            llm_input_payload = _read_json_artifact_from_gs_uri(llm_input_artifact)
        else:
            llm_input_payload = _read_json_safe(domain, target_run_id, "check_languages_llm_input.json", None)
        if not isinstance(llm_input_payload, dict):
            raise ValueError("Prepared LLM input payload is missing or invalid. Re-run preparation.")
        expected_hashes = prepared.get("source_hashes") if isinstance(prepared.get("source_hashes"), dict) else {}
        actual_hashes = _check_languages_source_hashes(domain, en_run_id, target_run_id)
        if expected_hashes and expected_hashes != actual_hashes:
            raise ValueError("Prepared payload is stale: source artifacts changed. Re-run preparation.")
        _upsert_job_status(domain, target_run_id, {
            "job_id": job_id,
            "status": "running",
            "type": "check_languages",
            "stage": "running_llm_review",
            "workflow_state": "running_llm_review",
            "en_run_id": en_run_id,
            "target_language": target_language,
            "target_url": target_url,
        })
        review_mode = os.environ.get("PHASE6_REVIEW_PROVIDER", "").strip()
        phase6_run(domain=domain, en_run_id=en_run_id, target_run_id=target_run_id, review_mode=review_mode, prepared_llm_payload=llm_input_payload)
        _require_artifact_exists(domain, target_run_id, "issues.json")
        _jobs[job_id]["status"] = "done"
        _upsert_job_status(domain, target_run_id, {
            "job_id": job_id,
            "status": "succeeded",
            "type": "check_languages",
            "stage": "completed",
            "workflow_state": "completed",
            "en_run_id": en_run_id,
            "target_language": target_language,
            "target_url": target_url,
        })
    except Exception as exc:
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = str(exc)
        stage = "running_llm_review_failed"
        workflow_state = "failed_during_llm"
        if isinstance(exc, _CheckLanguagesLlmPreflightError):
            stage = "llm_preflight_failed"
            workflow_state = "failed_before_llm"
        _upsert_job_status(domain, target_run_id, {
            "job_id": job_id,
            "status": "failed",
            "type": "check_languages",
            "stage": stage,
            "workflow_state": workflow_state,
            "en_run_id": en_run_id,
            "target_language": target_language,
            "target_url": target_url,
            "error": str(exc),
        })


def _check_languages_llm_preflight_error() -> str | None:
    review_mode = os.environ.get("PHASE6_REVIEW_PROVIDER", "").strip()
    if not review_mode:
        return "LLM review cannot start: PHASE6_REVIEW_PROVIDER is not configured."
    return None


class _CheckLanguagesLlmPreflightError(ValueError):
    """Raised when LLM stage launch preflight fails before Phase 6 execution."""


# Legacy combined prepare+LLM flow retained intentionally for non-UI and test utility paths.
# The UI handler path currently runs _prepare_check_languages_async and
# _run_check_languages_llm_async as separate stages instead of calling this wrapper.
def _run_check_languages_async(job_id: str, domain: str, en_run_id: str, target_language: str, target_run_id: str, target_url: str) -> None:
    """Backward-compatible composed flow: prepare payload, then run LLM review."""
    _prepare_check_languages_async(job_id, domain, en_run_id, target_language, target_run_id, target_url)
    latest = _latest_check_languages_job(domain, target_run_id)
    if not isinstance(latest, dict):
        return
    if str(latest.get("workflow_state", "")).strip().lower() != "prepared_for_llm":
        return
    llm_preflight_error = _check_languages_llm_preflight_error()
    if llm_preflight_error:
        _upsert_job_status(domain, target_run_id, {
            "job_id": f"{job_id}-llm-preflight",
            "status": "failed",
            "type": "check_languages",
            "stage": "llm_preflight_failed",
            "workflow_state": "failed_before_llm",
            "en_run_id": en_run_id,
            "target_language": target_language,
            "target_url": target_url,
            "error": llm_preflight_error,
        })
        return
    llm_job_id = f"{job_id}-llm"
    _run_check_languages_llm_async(llm_job_id, domain, en_run_id, target_language, target_run_id, target_url)

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
            self._serve_check_languages_page(parse_qs(parsed.query))
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
            "/issues/detail": "issues/detail.html",
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
        if parsed.path in {"/api/issues", "/api/issues/export"}:
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
            if parsed.path.endswith("/export") and query.get("format", ["json"])[0].strip().lower() == "csv":
                encoded = _issues_to_csv(filtered).encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/csv; charset=utf-8")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)
                return
            self._json_response({"issues": filtered, "count": len(filtered)})
            return
        if parsed.path == "/api/issues/detail":
            if not self._require_auth(api=True):
                return
            query = parse_qs(parsed.query)
            required, missing = _require_query_params(query, "domain", "run_id", "id")
            if missing:
                self._json_response(_missing_required_query_params(*missing), status=HTTPStatus.BAD_REQUEST)
                return
            domain = required["domain"]
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
            screenshot_uri = str((page or {}).get("storage_uri") or evidence.get("storage_uri", "") or "")
            if not screenshot_uri:
                missing_refs.append("screenshot")
            self._json_response({
                "issue": issue,
                "drilldown": {
                    "screenshot_uri": screenshot_uri,
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
                self._redirect_check_languages(form, message="Security error (CSRF). Please refresh and try again.", level="error")
                return
            self._start_check_languages(form)
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

    def _redirect_check_languages(self, payload: dict[str, str], *, message: str = "", level: str = "") -> None:
        selected_domain = _resolve_check_languages_domain(payload)
        query = {
            "selected_domain": selected_domain,
            "en_run_id": str(payload.get("en_run_id", "")).strip(),
            "target_language": _normalize_target_language(str(payload.get("target_language", ""))),
            "target_run_id": str(payload.get("target_run_id", "")).strip(),
            "generated_target_url": str(payload.get("generated_target_url", "")).strip(),
            "show_gate_diagnostics": _as_bool(payload.get("show_gate_diagnostics", "")),
        }
        if message:
            query["message"] = message
        if level:
            query["level"] = level
        location = f"/check-languages?{urlencode({k: v for k, v in query.items() if v})}"
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", location)
        self.end_headers()

    def _start_check_languages(self, payload: dict[str, str]) -> None:
        action = str(payload.get("action", "prepare_payload")).strip() or "prepare_payload"
        domain = _resolve_check_languages_domain(payload)
        en_run_id = str(payload.get("en_run_id", "")).strip()
        target_language = _normalize_target_language(str(payload.get("target_language", "")))
        if action == "recompute_gate":
            redirect_payload = dict(payload)
            redirect_payload["selected_domain"] = domain
            redirect_payload["show_gate_diagnostics"] = "1"
            self._redirect_check_languages(
                redirect_payload,
                message="LLM gate diagnostics recomputed from current artifacts.",
                level="ok",
            )
            return
        if action == "refresh_llm_status":
            redirect_payload = dict(payload)
            redirect_payload["selected_domain"] = domain
            redirect_payload["show_gate_diagnostics"] = "1"
            self._redirect_check_languages(
                redirect_payload,
                message="LLM review status refreshed from current job and telemetry artifacts.",
                level="ok",
            )
            return

        if not domain:
            self._redirect_check_languages(payload, message="Domain is required.", level="error")
            return
        if not en_run_id:
            self._redirect_check_languages(payload, message="English reference run is required.", level="error")
            return
        try:
            en_run_id = _validate_run_id(en_run_id)
        except ValueError as exc:
            self._redirect_check_languages(payload, message=str(exc), level="error")
            return
        if not target_language:
            self._redirect_check_languages(payload, message="Target language is required.", level="error")
            return
        if _is_english_language(target_language):
            self._redirect_check_languages(payload, message="Target language must be non-English.", level="error")
            return

        try:
            validate_domain(_normalize_testsite_domain_key(domain))
            generated_target_url = _build_check_languages_target_url(domain, target_language)
        except ValueError as exc:
            self._redirect_check_languages(payload, message=str(exc), level="error")
            return

        runs = _load_check_language_runs(domain)
        run_map = {str(row.get("run_id", "")): row for row in runs}
        en_run = run_map.get(en_run_id)
        if en_run is None:
            self._redirect_check_languages(payload, message="Selected English reference run is invalid for this domain.", level="error")
            return
        if not _run_is_en_reference_candidate(en_run):
            self._redirect_check_languages(payload, message="Selected reference run is not a valid English baseline.", level="error")
            return
        run_domain = str(en_run.get("domain", "")).strip() or domain

        en_readiness = _phase6_artifact_readiness(run_domain, en_run_id)
        if not en_readiness.get("ready"):
            self._redirect_check_languages(payload, message="English reference run is not ready for comparison prerequisites.", level="error")
            return

        available_languages = set(_load_target_languages(runs))
        if target_language not in available_languages:
            self._redirect_check_languages(payload, message="Selected target language is invalid for this domain.", level="error")
            return

        in_progress = _find_in_progress_check_languages_job(run_domain, en_run_id, target_language)
        if in_progress:
            existing_payload = dict(payload)
            existing_payload["target_run_id"] = str(in_progress.get("run_id", ""))
            self._redirect_check_languages(existing_payload, message="Language check is already in progress for this selection.", level="warning")
            return

        selected_run_candidates: list[dict[str, object]] = []
        for row in runs:
            if not isinstance(row, dict):
                continue
            row_run_id = str(row.get("run_id", "")).strip()
            if not row_run_id:
                continue
            row_latest_job = _latest_check_languages_job(run_domain, row_run_id)
            if not isinstance(row_latest_job, dict):
                continue
            if str(row_latest_job.get("en_run_id", "")).strip() != en_run_id:
                continue
            if _normalize_target_language(str(row_latest_job.get("target_language", ""))) != target_language:
                continue
            selected_run_candidates.append({
                "run_id": row_run_id,
                "created_ts": _parse_utc_timestamp(str(row.get("created_at", "")).strip()),
            })

        requested_target_run_id = str(payload.get("target_run_id", "")).strip()
        if requested_target_run_id:
            try:
                target_run_id = _validate_run_id(requested_target_run_id)
            except ValueError as exc:
                self._redirect_check_languages(payload, message=str(exc), level="error")
                return
        elif selected_run_candidates:
            canonical_base_run_id = f"{en_run_id}-check-{target_language}"
            candidate_run_ids = {str(item.get("run_id", "")).strip() for item in selected_run_candidates}
            if canonical_base_run_id in candidate_run_ids:
                target_run_id = canonical_base_run_id
            else:
                def _selection_sort_key(item: dict[str, object]) -> tuple[int, float, str]:
                    created_ts = item.get("created_ts")
                    run_id = str(item.get("run_id", "")).strip()
                    if isinstance(created_ts, (int, float)):
                        return (0, -float(created_ts), run_id)
                    return (1, 0.0, run_id)

                best_candidate = sorted(selected_run_candidates, key=_selection_sort_key)[0]
                target_run_id = str(best_candidate.get("run_id", "")).strip()
        else:
            target_run_id = _generate_target_run_id(run_domain, en_run_id, target_language)
        if action == "prepare_payload":
            latest_selected_job = _latest_check_languages_job(run_domain, target_run_id)
            latest_status = str((latest_selected_job or {}).get("status", "")).strip().lower()
            latest_workflow_state = str((latest_selected_job or {}).get("workflow_state", "")).strip().lower()
            latest_stage = str((latest_selected_job or {}).get("stage", "")).strip().lower()
            llm_review_active = (
                latest_status in {"running", "queued"}
                and (
                    latest_workflow_state in {"queued_llm_review", "running_llm_review"}
                    or latest_stage in {"queued_llm_review", "running_llm_review"}
                )
            )
            if llm_review_active:
                self._redirect_check_languages(
                    payload,
                    message=f"LLM review is already in progress for run {target_run_id}.",
                    level="warning",
                )
                return
        if action == "run_llm_review":
            prepared = _read_json_safe(run_domain, target_run_id, "check_languages_prepared_payload.json", None)
            if not isinstance(prepared, dict):
                self._redirect_check_languages(payload, message="Prepared payload is missing or invalid. Run preparation first.", level="error")
                return
            llm_preflight_error = _check_languages_llm_preflight_error()
            if llm_preflight_error:
                self._redirect_check_languages(payload, message=llm_preflight_error, level="error")
                return
            expected_hashes = prepared.get("source_hashes") if isinstance(prepared.get("source_hashes"), dict) else {}
            if expected_hashes and expected_hashes != _check_languages_source_hashes(run_domain, en_run_id, target_run_id):
                self._redirect_check_languages(payload, message="Prepared payload is stale. Re-run preparation before LLM review.", level="error")
                return
            job_id = f"check-languages-llm-{target_run_id}-{int(time.time())}"
            _upsert_job_status(run_domain, target_run_id, {
                "job_id": job_id,
                "status": "queued",
                "type": "check_languages",
                "stage": "queued_llm_review",
                "workflow_state": "prepared_for_llm",
                "en_run_id": en_run_id,
                "target_language": target_language,
                "target_url": generated_target_url,
            })
            t = threading.Thread(target=_run_check_languages_llm_async, args=(job_id, run_domain, en_run_id, target_language, target_run_id, generated_target_url), daemon=True)
            t.start()
            ok_message = "LLM review started from prepared payload."
        else:
            job_id = f"check-languages-prepare-{target_run_id}-{int(time.time())}"
            _upsert_job_status(run_domain, target_run_id, {
                "job_id": job_id,
                "status": "queued",
                "type": "check_languages",
                "stage": "queued_preparation",
                "workflow_state": "idle",
                "en_run_id": en_run_id,
                "target_language": target_language,
                "target_url": generated_target_url,
            })
            t = threading.Thread(target=_prepare_check_languages_async, args=(job_id, run_domain, en_run_id, target_language, target_run_id, generated_target_url), daemon=True)
            t.start()
            ok_message = "Language check payload preparation started."

        redirect_payload = dict(payload)
        redirect_payload["selected_domain"] = domain
        redirect_payload["target_run_id"] = target_run_id
        redirect_payload["generated_target_url"] = generated_target_url
        self._redirect_check_languages(redirect_payload, message=ok_message, level="ok")

    def _serve_check_languages_page(self, query: dict[str, list[str]]) -> None:
        domain = _normalize_check_languages_domain(str(query.get("selected_domain", [""])[0]) or str(query.get("domain", [""])[0]))
        if not domain:
            domain = _default_check_languages_domain()
        selected_en_run_id = str(query.get("en_run_id", [""])[0]).strip()
        en_run_id_from_query = bool(selected_en_run_id)
        target_language = _normalize_target_language(str(query.get("target_language", [""])[0]))
        target_run_id = str(query.get("target_run_id", [""])[0]).strip()
        generated_target_url = str(query.get("generated_target_url", [""])[0]).strip()
        message = str(query.get("message", [""])[0]).strip()
        level = str(query.get("level", [""])[0]).strip().lower()
        show_gate_diagnostics = _as_bool(str(query.get("show_gate_diagnostics", [""])[0]).strip())
        csrf_token = self._ensure_csrf_cookie()

        errors: list[str] = []
        runs: list[dict] = []
        en_candidates: list[dict] = []
        target_languages: list[str] = []
        issues_summary = None
        issues_exists = False
        issues_missing_after_completion = False
        latest_job = None
        target_run_domain_for_page = domain
        prepared_manifest_for_page = None
        manifest_domain_for_page = ""
        manifest_llm_input_artifact_for_page = ""
        llm_input_exists_for_page = False
        hashes_ok_for_page = False
        llm_running = False
        llm_input_artifact_status_for_page = "missing"
        llm_input_payload = None
        llm_input_status = "missing"
        llm_request_artifact_status_for_page = "missing"
        llm_request_payload = None
        llm_request_preview = "—"
        llm_request_path = ""
        llm_status_note = ""
        payload_prepared_evidence = False
        llm_review_block = "<p>LLM telemetry is not available for this selection yet.</p>"
        llm_launch_status_block = "<p>No LLM execution telemetry available yet.</p>"
        payload_preview_block = "<p>Payload not prepared yet.</p>"
        gate_diagnostics_block = "<p>Use “Recompute LLM gate diagnostics” to refresh gate details from storage.</p>"
        page_state = "input_incomplete"
        en_readiness = {"required": [], "missing": [], "read_error": "", "ready": False}
        stale = False
        llm_input_path = None
        llm_lookup_bucket = str(getattr(storage, "BUCKET_NAME", "") or "")
        llm_lookup_domain = ""
        llm_lookup_run_id = ""
        llm_lookup_filename = "check_languages_llm_input.json"
        llm_lookup_path = ""
        llm_telemetry_lookup_domain = ""
        llm_telemetry_lookup_run_id = ""
        llm_telemetry_lookup_filename = "llm_review_stats.json"
        llm_telemetry_lookup_path = ""
        llm_telemetry_read_status = "not_evaluated"
        llm_telemetry_error_summary = ""
        llm_telemetry_valid_for_ui = False
        llm_telemetry_state_for_ui = "not_evaluated"
        llm_telemetry_state_reason_for_ui = "not_evaluated"
        llm_telemetry_final_label = "Telemetry not evaluated yet."
        llm_review_debug_block = ""
        llm_review_debug_relevant = False
        llm_display: dict[str, str] = {}
        llm_preview = "—"
        failure_payload = None

        if target_run_id:
            target_run_id = target_run_id.strip().strip("/")
            if target_run_id:
                try:
                    target_run_id = _validate_run_id(target_run_id)
                except ValueError as exc:
                    errors.append(str(exc))
                    target_run_id = ""
            else:
                target_run_id = ""

        source_hashes_by_args: dict[tuple[str, str, str], dict] = {}

        def _source_hashes_for_render(run_domain: str, en_run_id: str, run_id: str) -> dict:
            cache_key = (run_domain, en_run_id, run_id)
            if cache_key not in source_hashes_by_args:
                source_hashes_by_args[cache_key] = _check_languages_source_hashes(run_domain, en_run_id, run_id)
            return source_hashes_by_args[cache_key]

        def _derive_llm_input_status(current_page_state: str) -> tuple[str, str, bool, str]:
            payload_ready = isinstance(prepared_manifest_for_page, dict) and isinstance(llm_input_payload, dict) and hashes_ok_for_page
            next_page_state = current_page_state
            if payload_ready and next_page_state in {"queued", "preparing_payload"}:
                next_page_state = "prepared_for_llm"
            if llm_input_artifact_status_for_page == "missing":
                next_status = "pending" if next_page_state in {"preparing_payload", "running_target_capture", "preparing_target_run"} else "missing"
            elif llm_input_artifact_status_for_page == "valid":
                next_status = "stale" if stale else "valid"
            else:
                next_status = llm_input_artifact_status_for_page
            note = ""
            if next_status == "pending":
                note = "Will be created after target capture and payload preparation complete."
            elif next_status == "read_error":
                note = "Artifact exists but could not be read from storage."
            elif next_status == "malformed_json":
                note = "Artifact exists but contains malformed JSON."
            elif next_status == "invalid_payload":
                note = "Artifact JSON parsed, but payload is not an object."
            return next_status, note, payload_ready, next_page_state

        try:
            validate_domain(_normalize_testsite_domain_key(domain))
            if not _is_supported_check_languages_domain(domain):
                raise ValueError("Selected domain is unsupported.")
            runs = _load_check_language_runs(domain)
        except ValueError as exc:
            errors.append(str(exc))

        run_map = {str(row.get("run_id", "")): row for row in runs}
        en_candidates = [row for row in runs if _run_is_en_reference_candidate(row)]
        target_languages = _load_target_languages(runs)
        if not selected_en_run_id:
            selected_en_run_id = _latest_successful_en_standard_run_id(domain, en_candidates) or _default_english_reference_run_id(en_candidates)

        if selected_en_run_id and selected_en_run_id not in run_map:
            errors.append("Selected English reference run is invalid for this domain.")
        elif selected_en_run_id and selected_en_run_id in run_map and not _run_is_en_reference_candidate(run_map[selected_en_run_id]):
            errors.append("Selected reference run is not a valid English baseline.")
        elif selected_en_run_id and selected_en_run_id in run_map:
            en_run_domain = str(run_map[selected_en_run_id].get("domain", "")).strip() or domain
            en_readiness = _phase6_artifact_readiness(en_run_domain, selected_en_run_id)

        if target_language:
            if _is_english_language(target_language):
                errors.append("Target language must be non-English.")
            elif target_language not in target_languages:
                errors.append("Selected target language is invalid for this domain.")
            elif not generated_target_url:
                try:
                    generated_target_url = _build_check_languages_target_url(domain, target_language)
                except ValueError as exc:
                    errors.append(str(exc))

        if selected_en_run_id and not en_readiness.get("ready") and not any("Selected English reference run is invalid" in e or "not a valid English baseline" in e for e in errors):
            errors.append("English reference run is not ready for comparison prerequisites.")

        if selected_en_run_id and target_language and not target_run_id:
            for run in runs:
                run_id = str(run.get("run_id", ""))
                job = _latest_check_languages_job(domain, run_id)
                if not isinstance(job, dict):
                    continue
                if str(job.get("en_run_id", "")) == selected_en_run_id and _normalize_target_language(str(job.get("target_language", ""))) == target_language:
                    target_run_id = run_id
                    break

        if selected_en_run_id and target_language and target_run_id and not errors:
            latest_job = _latest_check_languages_job(domain, target_run_id)
            target_run_domain = str((run_map.get(target_run_id) or {}).get("domain", "")).strip() or str((latest_job or {}).get("domain", "")).strip() or domain
            target_run_domain_for_page = target_run_domain
            issues_exists = _artifact_exists(target_run_domain, target_run_id, "issues.json")
            llm_telemetry_lookup_domain = target_run_domain
            llm_telemetry_lookup_run_id = target_run_id
            try:
                llm_telemetry_lookup_path = f"gs://{llm_lookup_bucket}/{storage.artifact_path(llm_telemetry_lookup_domain, llm_telemetry_lookup_run_id, llm_telemetry_lookup_filename)}"
            except Exception:
                llm_telemetry_lookup_path = ""
            llm_stats_diag = _check_languages_llm_review_telemetry_status(llm_telemetry_lookup_domain, llm_telemetry_lookup_run_id)
            llm_telemetry_read_status = str(llm_stats_diag.get("status", "missing"))
            llm_stats_exists = bool(llm_stats_diag.get("exists"))
            llm_stats_payload = llm_stats_diag.get("payload") if llm_telemetry_read_status == "valid" else None
            llm_telemetry_error_summary = str(llm_stats_diag.get("error", "")).strip()
            workflow_state = str((latest_job or {}).get("workflow_state", "")).strip().lower()
            latest_status = str((latest_job or {}).get("status", "")).strip().lower()
            stage = str((latest_job or {}).get("stage", "")).strip().lower()
            llm_running = (
                latest_status in {"running", "queued"}
                and (
                    workflow_state in {"queued_llm_review", "running_llm_review"}
                    or stage in {"queued_llm_review", "running_llm_review"}
                )
            )
            if not workflow_state:
                stage_state_map = {
                    "queued_preparation": "idle",
                    "preparing_target_run": "preparing_payload",
                    "running_target_capture": "preparing_payload",
                    "assembling_payload": "preparing_payload",
                    "prepared_for_llm": "prepared_for_llm",
                    "running_llm_review": "running_llm_review",
                    "completed": "completed",
                    "running_target_capture_failed": "failed_before_llm",
                    "preparing_payload_failed": "failed_before_llm",
                    "llm_preflight_failed": "failed_before_llm",
                    "running_llm_review_failed": "failed_during_llm",
                }
                workflow_state = stage_state_map.get(str((latest_job or {}).get("stage", "")).strip().lower(), "")
            llm_display = _llm_review_display(latest_job, llm_stats_payload, llm_stats_exists, workflow_state or page_state)
            llm_telemetry_valid_for_ui = isinstance(llm_stats_payload, dict)
            llm_telemetry_state_for_ui = str(llm_display.get("state", "")).strip() or "unknown"
            llm_telemetry_state_reason_for_ui = str(llm_display.get("state_reason", "")).strip() or "unknown"
            llm_telemetry_final_label = llm_telemetry_state_for_ui
            llm_stage_set = {"queued_llm_review", "running_llm_review", "running_llm_review_failed", "completed", "llm_preflight_failed"}
            llm_workflow_state_set = {
                "queued_llm_review",
                "running_llm_review",
                "failed_during_llm",
                "completed",
                "running_llm_review_failed",
                "llm_preflight_failed",
            }
            llm_review_debug_relevant = (
                llm_stats_exists
                or bool(llm_telemetry_valid_for_ui)
                or stage in llm_stage_set
                or workflow_state in llm_workflow_state_set
            )
            warning_html = f'<p class="warning">{_h(llm_display["warning"])}</p>' if llm_display["warning"] else ""
            llm_review_block = (
                f"<p>{_h(llm_display['process_summary'])}</p>"
                f"{warning_html}"
                f"<ul>"
                f"<li>State: <strong>{_h(llm_display['state'])}</strong></li>"
                f"<li>State reason: <code>{_h(llm_display['state_reason'])}</code></li>"
                f"<li>Review mode: {_h(llm_display['review_mode'])}</li>"
                f"<li>Provider type: {_h(llm_display['provider_type'])}</li>"
                f"<li>Configured provider/model: {_h(llm_display['configured_provider'])} / {_h(llm_display['configured_model'])}</li>"
                f"<li>Effective provider/model: {_h(llm_display['effective_provider'])} / {_h(llm_display['effective_model'])}</li>"
                f"<li>LLM request flag: {_h(llm_display['llm_requested'])}</li>"
                f"<li>Batches attempted/succeeded/failed: {_h(llm_display['batches_attempted'])} / {_h(llm_display['batches_succeeded'])} / {_h(llm_display['batches_failed'])}</li>"
                f"<li>Responses received: {_h(llm_display['responses_received'])}</li>"
                f"<li>Fallback batches/items: {_h(llm_display['fallback_batches'])} / {_h(llm_display['fallback_items'])}</li>"
                f"<li>Fallback status: {_h(llm_display['fallback_state'])}</li>"
                f"<li>Estimated tokens (prompt/completion/total): {_h(llm_display['estimated_tokens'])}</li>"
                f"<li>Actual tokens (prompt/completion/total): {_h(llm_display['actual_tokens'])}</li>"
                f"<li>Cost used: {_h(llm_display['cost_display'])}</li>"
                f"<li>Operator notes: {_h(llm_display['operator_notes'])}</li>"
                f"</ul>"
            )
            if issues_exists:
                issues_payload = _read_json_safe(target_run_domain, target_run_id, "issues.json", None)
                if isinstance(issues_payload, list):
                    issues_summary = _summarize_issues_payload(issues_payload)
                else:
                    errors.append("issues.json is malformed.")

            if workflow_state:
                page_state = workflow_state
            elif latest_status in {"failed", "error"}:
                page_state = "failed_before_llm"
            elif latest_status in {"queued"} or stage == "queued":
                page_state = "queued"
            elif stage == "preparing_target_run":
                page_state = "preparing_target_run"
            elif stage == "running_target_capture":
                page_state = "running_target_capture"
            elif stage == "running_comparison":
                page_state = "running_comparison"
            elif issues_summary is not None:
                page_state = "completed_with_zero_issues" if issues_summary["total"] == 0 else "completed_with_issues"
            elif latest_status == "succeeded":
                page_state = "completed"
                issues_missing_after_completion = True
            else:
                page_state = "ready_to_start"

            prepared_manifest = _read_json_safe(target_run_domain, target_run_id, "check_languages_prepared_payload.json", None)
            if isinstance(prepared_manifest, dict):
                manifest_llm_input_artifact_for_page = str(prepared_manifest.get("llm_input_artifact", "")).strip()
                candidate_manifest_domain = str(prepared_manifest.get("domain", "")).strip()
                if not candidate_manifest_domain and manifest_llm_input_artifact_for_page:
                    parsed_artifact = _parse_gs_uri_safe(manifest_llm_input_artifact_for_page)
                    if parsed_artifact is not None:
                        _, parsed_domain, parsed_run_id, _ = parsed_artifact
                        if parsed_run_id == target_run_id:
                            candidate_manifest_domain = parsed_domain
                if candidate_manifest_domain:
                    manifest_domain_for_page = candidate_manifest_domain
                    if candidate_manifest_domain != target_run_domain:
                        target_run_domain = candidate_manifest_domain
                        target_run_domain_for_page = candidate_manifest_domain
                        corrected_manifest = _read_json_safe(target_run_domain, target_run_id, "check_languages_prepared_payload.json", None)
                        if isinstance(corrected_manifest, dict):
                            prepared_manifest = corrected_manifest
                            manifest_llm_input_artifact_for_page = str(prepared_manifest.get("llm_input_artifact", "")).strip()
            prepared_manifest_for_page = prepared_manifest
            llm_lookup_domain = target_run_domain
            llm_lookup_run_id = target_run_id
            try:
                llm_lookup_path = f"gs://{llm_lookup_bucket}/{storage.artifact_path(llm_lookup_domain, llm_lookup_run_id, llm_lookup_filename)}"
            except Exception:
                llm_lookup_path = ""
            llm_input_diagnostics = _check_languages_llm_input_artifact_status(target_run_domain, target_run_id)
            llm_input_artifact_status_for_page = str(llm_input_diagnostics.get("status", "missing"))
            llm_input_payload = llm_input_diagnostics.get("payload") if llm_input_artifact_status_for_page == "valid" else None
            llm_input_exists = llm_input_artifact_status_for_page == "valid"
            llm_input_exists_for_page = llm_input_exists
            llm_request_diagnostics = _check_languages_llm_request_artifact_status(target_run_domain, target_run_id)
            llm_request_artifact_status_for_page = str(llm_request_diagnostics.get("status", "missing"))
            llm_request_payload = (
                llm_request_diagnostics.get("payload")
                if llm_request_artifact_status_for_page == "valid"
                else None
            )
            try:
                llm_request_path = f"gs://{llm_lookup_bucket}/{storage.artifact_path(target_run_domain, target_run_id, 'check_languages_llm_request.json')}"
            except Exception:
                llm_request_path = ""
            if isinstance(llm_request_payload, dict):
                llm_request_preview = json.dumps(llm_request_payload, ensure_ascii=False, indent=2)
            source_hashes = prepared_manifest.get("source_hashes") if isinstance(prepared_manifest, dict) and isinstance(prepared_manifest.get("source_hashes"), dict) else {}
            has_hashes = bool(source_hashes)
            stale = bool(source_hashes and source_hashes != _source_hashes_for_render(target_run_domain, selected_en_run_id, target_run_id))
            hashes_ok_for_page = has_hashes and not stale
            if isinstance(llm_input_payload, dict):
                manifest_artifact_uri = (
                    prepared_manifest.get("llm_input_artifact")
                    if isinstance(prepared_manifest, dict) and str(prepared_manifest.get("llm_input_artifact", "")).strip()
                    else None
                )
                if manifest_artifact_uri:
                    llm_input_path = str(manifest_artifact_uri)
                else:
                    try:
                        from pipeline.storage import BUCKET_NAME, artifact_path

                        llm_input_path = f"gs://{BUCKET_NAME}/{artifact_path(target_run_domain, target_run_id, 'check_languages_llm_input.json')}"
                    except Exception:
                        llm_input_path = None
                preview_payload = {
                    "target_language": llm_input_payload.get("target_language"),
                    "review_context_count": llm_input_payload.get("review_context_count"),
                    "blocked_pages_count": len(llm_input_payload.get("blocked_pages", [])) if isinstance(llm_input_payload.get("blocked_pages"), list) else 0,
                    "source_hashes": llm_input_payload.get("source_hashes", {}),
                    "sample_review_context": (llm_input_payload.get("review_contexts") or [None])[0],
                }
                llm_preview = json.dumps(preview_payload, ensure_ascii=False, indent=2)
            failure_payload = _read_json_safe(target_run_domain, target_run_id, "check_languages_replay_failure.json", None)
        elif selected_en_run_id and target_language:
            page_state = "ready_to_start"

        if selected_en_run_id and not target_language and en_run_id_from_query:
            errors.append("Target language is required.")
        if target_language and not selected_en_run_id:
            errors.append("English reference run is required.")

        def _run_option(run: dict, selected: bool) -> str:
            label = _run_display_label(run)
            selected_attr = ' selected="selected"' if selected else ""
            return f'<option value="{_h(run.get("run_id", ""))}"{selected_attr}>{_h(label)}</option>'

        def _language_option(language: str, selected: bool) -> str:
            selected_attr = ' selected="selected"' if selected else ""
            return f'<option value="{_h(language)}"{selected_attr}>{_h(language)}</option>'

        if en_candidates:
            en_options = ['<option value="">Select English reference run</option>'] + [_run_option(run, str(run.get("run_id", "")) == selected_en_run_id) for run in sorted(en_candidates, key=lambda row: (row.get("created_at", ""), row.get("run_id", "")), reverse=True)]
        else:
            en_options = ['<option value="">No English runs found</option>']
        language_options = ['<option value="">Select target language</option>'] + [_language_option(language, language == target_language) for language in target_languages]

        issue_summary_block = "<p>Issues output: missing.</p>"
        stale_summary = bool(issues_summary is not None and str((latest_job or {}).get("status", "")).strip().lower() in {"failed", "error"})
        if issues_summary is not None:
            issue_summary_block = (
                f"<p>Issues output: present.</p>"
                f"<ul>"
                f"<li>Total: <strong>{issues_summary['total']}</strong></li>"
                f"<li>By category: {_h(_format_summary_pairs(issues_summary['by_category']))}</li>"
                f"<li>By severity: {_h(_format_summary_pairs(issues_summary['by_severity']))}</li>"
                f"<li>By language: {_h(_format_summary_pairs(issues_summary['by_language']))}</li>"
                f"<li>By state: {_h(_format_summary_pairs(issues_summary['by_state']))}</li>"
                f"</ul>"
            )
            if stale_summary:
                issue_summary_block += '<p class="warning">Summary shown from existing issues.json and may be stale from a previous successful run.</p>'
        if issues_missing_after_completion:
            issue_summary_block += '<p class="error">Job completed but issues.json is missing.</p>'

        latest_job_block = "<p>No composed language-check job has been started yet.</p>"
        if isinstance(latest_job, dict):
            details_block = ""
            if isinstance(latest_job.get("error_details"), dict):
                details_block = (
                    "<details><summary>Failure diagnostics</summary>"
                    f"<pre>{_h(json.dumps(latest_job.get('error_details'), ensure_ascii=False, indent=2))}</pre>"
                    "</details>"
                )
            latest_job_block = (
                f"<p>Latest job: {_h(latest_job.get('job_id', ''))}</p>"
                f"<p>Status: <strong>{_h(latest_job.get('status', ''))}</strong></p>"
                f"<p>Stage: <strong>{_h(latest_job.get('stage', ''))}</strong></p>"
                f"<p>Workflow state: <strong>{_h(latest_job.get('workflow_state', page_state))}</strong></p>"
                f"<p>English run: {_h(latest_job.get('en_run_id', ''))}</p>"
                f"<p>Target language: {_h(latest_job.get('target_language', ''))}</p>"
                f"<p>Target URL used: {_h(latest_job.get('target_url', generated_target_url))}</p>"
                f"<p>Error: {_h(latest_job.get('error', '')) or '—'}</p>"
                f"{details_block}"
            )

        run_query = urlencode({"domain": domain, "run_id": target_run_id}) if domain and target_run_id else ""
        issues_link = f"/?{run_query}" if run_query else "#"
        issues_api_link = f"/api/issues?{run_query}" if run_query else "#"

        notices: list[str] = []
        if message:
            css = "ok" if level == "ok" else "warning" if level == "warning" else "error"
            notices.append(f'<li class="{css}">{_h(message)}</li>')
        if target_run_id:
            prepared_manifest_notice = prepared_manifest_for_page if isinstance(prepared_manifest_for_page, dict) else _read_json_safe(target_run_domain_for_page, target_run_id, "check_languages_prepared_payload.json", None)
            if isinstance(prepared_manifest_notice, dict):
                expected_notice = prepared_manifest_notice.get("source_hashes") if isinstance(prepared_manifest_notice.get("source_hashes"), dict) else {}
                if expected_notice and selected_en_run_id and expected_notice != _source_hashes_for_render(target_run_domain_for_page, selected_en_run_id, target_run_id):
                    notices.append('<li class="warning">Prepared payload is stale and LLM review is disabled. Re-run preparation.</li>')
        notices.extend([f'<li class="error">{_h(err)}</li>' for err in errors])
        notices_html = f"<ul>{''.join(notices)}</ul>" if notices else "<p>—</p>"

        prepare_enabled = bool(domain and selected_en_run_id and target_language and not errors and str((latest_job or {}).get("status", "")).lower() not in {"running", "queued"})
        prepare_disabled_attr = "" if prepare_enabled else ' disabled="disabled"'
        if target_run_id and not isinstance(prepared_manifest_for_page, dict):
            prepared_manifest_for_page = _read_json_safe(target_run_domain_for_page, target_run_id, "check_languages_prepared_payload.json", None)
        if target_run_id and not llm_input_exists_for_page:
            llm_lookup_domain = target_run_domain_for_page
            llm_lookup_run_id = target_run_id
            try:
                llm_lookup_path = f"gs://{llm_lookup_bucket}/{storage.artifact_path(llm_lookup_domain, llm_lookup_run_id, llm_lookup_filename)}"
            except Exception:
                llm_lookup_path = ""
            _fb_llm_diag = _check_languages_llm_input_artifact_status(target_run_domain_for_page, target_run_id)
            llm_input_artifact_status_for_page = str(_fb_llm_diag.get("status", llm_input_artifact_status_for_page))
            _fb_llm_payload = _fb_llm_diag.get("payload") if llm_input_artifact_status_for_page == "valid" else None
            if isinstance(_fb_llm_payload, dict):
                llm_input_exists_for_page = True
                llm_input_artifact_status_for_page = "valid"
                if not isinstance(llm_input_payload, dict):
                    llm_input_payload = _fb_llm_payload
                if not llm_input_path:
                    llm_input_path = f"gs://{storage.BUCKET_NAME}/{storage.artifact_path(target_run_domain_for_page, target_run_id, 'check_languages_llm_input.json')}"
                preview_payload = {
                    "target_language": llm_input_payload.get("target_language"),
                    "review_context_count": llm_input_payload.get("review_context_count"),
                    "blocked_pages_count": len(llm_input_payload.get("blocked_pages", [])) if isinstance(llm_input_payload.get("blocked_pages"), list) else 0,
                    "source_hashes": llm_input_payload.get("source_hashes", {}),
                    "sample_review_context": (llm_input_payload.get("review_contexts") or [None])[0],
                }
                llm_preview = json.dumps(preview_payload, ensure_ascii=False, indent=2)
        if target_run_id and isinstance(prepared_manifest_for_page, dict) and not hashes_ok_for_page:
            expected = prepared_manifest_for_page.get("source_hashes") if isinstance(prepared_manifest_for_page.get("source_hashes"), dict) else {}
            hashes_ok_for_page = bool(expected) and expected == _source_hashes_for_render(target_run_domain_for_page, selected_en_run_id, target_run_id)
            stale = bool(expected) and not hashes_ok_for_page
        if target_run_id:
            llm_input_status, llm_status_note, payload_prepared_evidence, page_state = _derive_llm_input_status(page_state)
            llm_path_block = f"path: <code>{_h(llm_input_path)}</code>" if llm_input_path else ""
            llm_note_block = f"<br/><em>{_h(llm_status_note)}</em>" if llm_status_note else ""
            llm_preview_block = f"<details><summary>Preview</summary><pre>{_h(llm_preview)}</pre></details>" if isinstance(llm_input_payload, dict) else ""
            llm_request_preview_block = (
                f"<details><summary>Preview</summary><pre>{_h(llm_request_preview)}</pre></details>"
                if isinstance(llm_request_payload, dict)
                else ""
            )
            payload_preview_block = (
                "<ul>"
                f"<li><strong>check_languages_llm_input.json</strong> — status: <strong>{_h(llm_input_status)}</strong><br/>"
                f"{llm_path_block}"
                f"{llm_note_block}"
                f"{llm_preview_block}</li>"
                f"<li><strong>check_languages_llm_request.json</strong> — status: <strong>{_h(llm_request_artifact_status_for_page)}</strong><br/>"
                f"path: <code>{_h(llm_request_path)}</code>"
                f"{llm_request_preview_block}</li>"
                "</ul>"
            )
            if isinstance(failure_payload, dict):
                payload_preview_block += (
                    "<p class=\"error\">Preparation failure:</p>"
                    f"<pre>{_h(json.dumps(failure_payload, ensure_ascii=False, indent=2))}</pre>"
                )
        llm_enabled = bool(
            domain
            and selected_en_run_id
            and target_language
            and target_run_id
            and not errors
            and llm_input_exists_for_page
            and hashes_ok_for_page
            and not llm_running
        )
        if show_gate_diagnostics:
            gate_diagnostics_block = (
                "<ul>"
                f"<li>domain present: <strong>{_h(str(bool(domain)).lower())}</strong></li>"
                f"<li>selected_en_run_id present: <strong>{_h(str(bool(selected_en_run_id)).lower())}</strong></li>"
                f"<li>target_language present: <strong>{_h(str(bool(target_language)).lower())}</strong></li>"
                f"<li>target_run_id present: <strong>{_h(str(bool(target_run_id)).lower())}</strong></li>"
                f"<li>errors empty: <strong>{_h(str(not errors).lower())}</strong></li>"
                f"<li>llm_input_exists_for_page: <strong>{_h(str(llm_input_exists_for_page).lower())}</strong></li>"
                f"<li>hashes_ok_for_page: <strong>{_h(str(hashes_ok_for_page).lower())}</strong></li>"
                f"<li>llm_running: <strong>{_h(str(llm_running).lower())}</strong></li>"
                f"<li>check_languages_llm_input.json read status: <strong>{_h(llm_input_artifact_status_for_page)}</strong></li>"
                f"<li>manifest_domain: <strong>{_h(manifest_domain_for_page or '—')}</strong></li>"
                f"<li>resolved_target_run_domain: <strong>{_h(target_run_domain_for_page or '—')}</strong></li>"
                f"<li>llm_input_artifact: <strong>{_h(manifest_llm_input_artifact_for_page or '—')}</strong></li>"
                f"<li>lookup_bucket: <strong>{_h(llm_lookup_bucket or '—')}</strong></li>"
                f"<li>lookup_domain: <strong>{_h(llm_lookup_domain or '—')}</strong></li>"
                f"<li>lookup_run_id: <strong>{_h(llm_lookup_run_id or '—')}</strong></li>"
                f"<li>lookup_filename: <strong>{_h(llm_lookup_filename or '—')}</strong></li>"
                f"<li>actual_llm_input_lookup_path: <strong>{_h(llm_lookup_path or '—')}</strong></li>"
                f"<li>latest_job_status: <strong>{_h(str((latest_job or {}).get('status', '') or '—'))}</strong></li>"
                f"<li>latest_job_id: <strong>{_h(str((latest_job or {}).get('job_id', '') or '—'))}</strong></li>"
                f"<li>latest_job_type: <strong>{_h(str((latest_job or {}).get('type', '') or '—'))}</strong></li>"
                f"<li>latest_job_stage: <strong>{_h(str((latest_job or {}).get('stage', '') or '—'))}</strong></li>"
                f"<li>latest_job_workflow_state: <strong>{_h(str((latest_job or {}).get('workflow_state', page_state) or '—'))}</strong></li>"
                f"<li>latest_job_used_for_ui: <strong>{_h(str(bool(latest_job)).lower())}</strong></li>"
                f"<li>latest_job_selection_source: <strong>_latest_check_languages_job(domain, target_run_id)</strong></li>"
                f"<li>latest_job_is_llm_stage_job: <strong>{_h(str(str((latest_job or {}).get('stage', '')).strip().lower() in {'queued_llm_review', 'running_llm_review', 'running_llm_review_failed', 'completed'}).lower())}</strong></li>"
                f"<li>final llm_enabled: <strong>{_h(str(llm_enabled).lower())}</strong></li>"
                "</ul>"
            )
            if llm_review_debug_relevant:
                llm_review_debug_block = (
                    "<ul>"
                    f"<li>telemetry_state_used_by_ui: <strong>{_h(llm_telemetry_state_for_ui or '—')}</strong></li>"
                    f"<li>telemetry_state_reason_used_by_ui: <strong>{_h(llm_telemetry_state_reason_for_ui or '—')}</strong></li>"
                    f"<li>final_ui_label_for_llm_review: <strong>{_h(llm_telemetry_final_label or '—')}</strong></li>"
                    f"<li>telemetry_lookup_domain: <strong>{_h(llm_telemetry_lookup_domain or '—')}</strong></li>"
                    f"<li>telemetry_lookup_run_id: <strong>{_h(llm_telemetry_lookup_run_id or '—')}</strong></li>"
                    f"<li>telemetry_lookup_filename: <strong>{_h(llm_telemetry_lookup_filename or '—')}</strong></li>"
                    f"<li>telemetry_lookup_bucket: <strong>{_h(llm_lookup_bucket or '—')}</strong></li>"
                    f"<li>telemetry_actual_lookup_path: <strong>{_h(llm_telemetry_lookup_path or '—')}</strong></li>"
                    f"<li>telemetry_read_status: <strong>{_h(llm_telemetry_read_status or '—')}</strong></li>"
                    f"<li>telemetry_short_error_summary: <strong>{_h(llm_telemetry_error_summary or '—')}</strong></li>"
                    f"<li>telemetry_payload_valid_for_ui: <strong>{_h(str(bool(llm_telemetry_valid_for_ui)).lower())}</strong></li>"
                    "</ul>"
                )
            else:
                llm_review_debug_block = "<p>LLM review diagnostics will appear after LLM review starts.</p>"
        launch_attempted = (
            bool(latest_job)
            and (
                str((latest_job or {}).get("workflow_state", "")).strip().lower() in {"queued_llm_review", "running_llm_review", "failed_during_llm", "completed", "running_llm_review_failed", "llm_preflight_failed"}
                or str((latest_job or {}).get("stage", "")).strip().lower() in {"queued_llm_review", "running_llm_review", "running_llm_review_failed", "completed", "llm_preflight_failed"}
            )
        ) or llm_telemetry_read_status == "valid"
        llm_stage_value = str((latest_job or {}).get("workflow_state", "")).strip() or str((latest_job or {}).get("stage", "")).strip() or page_state
        llm_result_summary = str(llm_display.get("state", "")).strip() or "Not started"
        llm_failure_reason = str((latest_job or {}).get("error", "")).strip() or llm_telemetry_error_summary
        llm_provider_model = "—"
        if llm_display:
            llm_provider_model = f"{str(llm_display.get('effective_provider', '—')).strip() or '—'} / {str(llm_display.get('effective_model', '—')).strip() or '—'}"
        llm_step_lines: list[str] = []
        llm_step_lines.append("payload prepared" if payload_prepared_evidence or page_state in {"prepared_for_llm", "running_llm_review", "completed", "failed_during_llm"} else "payload pending")
        if page_state in {"preparing_target_run", "running_target_capture", "preparing_payload"}:
            llm_step_lines.append(f"target capture stage: {page_state}")
        if page_state in {"prepared_for_llm", "running_llm_review", "completed", "failed_during_llm"}:
            llm_step_lines.append("prepared for llm")
        if llm_running:
            llm_step_lines.append("llm started")
        if llm_display:
            attempted = _as_int(llm_display.get("batches_attempted"), 0)
            received = _as_int(llm_display.get("responses_received"), 0)
            if attempted > 0:
                llm_step_lines.append(f"batch sent ({attempted})")
            if received > 0:
                llm_step_lines.append(f"response received ({received})")
        if page_state in {"completed", "completed_with_issues", "completed_with_zero_issues"}:
            llm_step_lines.append("completed")
        if page_state in {"failed_during_llm", "running_llm_review_failed", "failed_before_llm"}:
            llm_step_lines.append(f"failed: {llm_failure_reason or 'unknown reason'}")
        llm_step_lines = llm_step_lines[:10]
        llm_step_items = "".join(f"<li>{_h(step)}</li>" for step in llm_step_lines)
        short_result = llm_result_summary
        if llm_failure_reason and page_state in {"failed_during_llm", "running_llm_review_failed", "failed_before_llm"}:
            short_result = f"{llm_result_summary} ({llm_failure_reason})"
        llm_launch_status_block = (
            "<ul>"
            f"<li>Launch attempted: <strong>{_h('yes' if launch_attempted else 'no')}</strong></li>"
            f"<li>Current step: <strong>{_h(llm_stage_value or '—')}</strong></li>"
            f"<li>LLM request started: <strong>{_h(llm_display.get('llm_requested', 'unknown'))}</strong></li>"
            f"<li>Provider/model: <strong>{_h(llm_provider_model)}</strong></li>"
            f"<li>Result: <strong>{_h(short_result or '—')}</strong></li>"
            f"<li>Failure reason: <strong>{_h(llm_failure_reason or '—')}</strong></li>"
            "</ul>"
            + (f"<p>Recent steps</p><ul>{llm_step_items}</ul>" if llm_step_items else "<p>No LLM execution telemetry available yet.</p>")
        )

        llm_disabled_attr = "" if llm_enabled else ' disabled="disabled"'
        llm_review_debug_section = ""
        if show_gate_diagnostics:
            llm_review_debug_section = (
                "<section>"
                "<h2>LLM review diagnostics</h2>"
                f"{llm_review_debug_block}"
                "</section>"
            )

        self._serve_template(
            "check-languages.html",
            replacements={
                "{{csrf_token}}": _h(csrf_token),
                "{{domain}}": _h(domain),
                "{{domain_options}}": "".join(
                    [
                        f'<option value="{_h(item)}"{" selected=\"selected\"" if item == domain else ""}>{_h(item)}</option>'
                        for item in (SUPPORTED_CHECK_LANGUAGE_DOMAINS if not domain or domain in SUPPORTED_CHECK_LANGUAGE_DOMAINS else [*SUPPORTED_CHECK_LANGUAGE_DOMAINS, domain])
                    ]
                ),
                "{{selected_en_run_id}}": _h(selected_en_run_id),
                "{{target_language}}": _h(target_language),
                "{{target_run_id}}": _h(target_run_id),
                "{{generated_target_url}}": _h(generated_target_url),
                "{{notices}}": notices_html,
                "{{en_options}}": "".join(en_options),
                "{{target_language_options}}": "".join(language_options),
                "{{page_state}}": _h(page_state),
                "{{issues_exists}}": _h("present" if issues_exists else "missing"),
                "{{en_required}}": _h(", ".join(en_readiness.get("required", [])) or "—"),
                "{{en_missing}}": _h(", ".join(en_readiness.get("missing", [])) or "—"),
                "{{en_read_error}}": _h(en_readiness.get("read_error", "") or "—"),
                "{{en_ready}}": _h("ready" if en_readiness.get("ready") else "not_ready"),
                "{{issues_summary}}": issue_summary_block,
                "{{latest_job}}": latest_job_block,
                "{{llm_review}}": llm_review_block,
                "{{llm_launch_status}}": llm_launch_status_block,
                "{{issues_link}}": _h(issues_link),
                "{{issues_api_link}}": _h(issues_api_link),
                "{{prepare_disabled}}": prepare_disabled_attr,
                "{{run_llm_disabled}}": llm_disabled_attr,
                "{{payload_preview}}": payload_preview_block,
                "{{gate_diagnostics}}": gate_diagnostics_block,
                "{{llm_review_diagnostics}}": llm_review_debug_section,
            },
            extra_set_cookies=[self._build_cookie_header(CSRF_COOKIE, csrf_token, max_age=SESSION_MAX_AGE_SECONDS, http_only=False)],
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
