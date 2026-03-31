from __future__ import annotations

import datetime
import json
import re
import sys
import traceback
from urllib.parse import urlparse, urlunparse

from app.artifact_helpers import (
    _artifact_exists,
    _artifact_exists_strict,
    _parse_gs_uri,
    _read_json_safe,
    _read_list_artifact_required,
)
from app.server_utils import _stable_json_hash
from pipeline import storage

CANONICAL_TARGET_LANGUAGES = [
    "ar", "az", "bg", "cs", "da", "de", "el", "es", "et", "fi", "fr", "he", "hi", "hr", "hu", "hy", "it", "ja", "ka", "kk",
    "ko", "lt", "lv", "mk", "nl", "no", "pl", "pt", "ro", "ru", "sk", "sl", "sr", "sv", "tr", "uk", "zh",
]
GITHUB_PAGES_TESTSITE_CANONICAL_DOMAIN = "https://evinaeva.github.io/polyglot-watchdog-testsite/en/index.html"
GITHUB_PAGES_TESTSITE_LEGACY_ROOT_DOMAIN = "https://evinaeva.github.io/"
GITHUB_PAGES_TESTSITE_PROJECT_PREFIX = "/polyglot-watchdog-testsite"
TARGET_LANGUAGE_ALIASES = {
    "cz": "cs",
    "dk": "da",
    "gr": "el",
    "ee": "et",
    "jp": "ja",
    "kr": "ko",
}
SUPPORTED_CHECK_LANGUAGE_DOMAINS = [
    "https://bongacams.com/",
    "https://bongamodels.com/",
    "https://bongacash.com/",
    GITHUB_PAGES_TESTSITE_CANONICAL_DOMAIN,
]
NORMAL_CHECK_LANGUAGE_DOMAINS = tuple(SUPPORTED_CHECK_LANGUAGE_DOMAINS[:3])


def _normalize_optional_string(value):
    text = str(value).strip() if value is not None else ""
    if not text or text.lower() in {"none", "null"}:
        return None
    return text


def _is_english_language(value: str) -> bool:
    normalized = str(value or "").strip().lower()
    return normalized in {"en", "en-us", "en-gb", "english"}


def _normalize_target_language(value: str) -> str:
    normalized = str(value or "").strip().lower()
    return TARGET_LANGUAGE_ALIASES.get(normalized, normalized)


def _is_github_pages_testsite_alias(value: str) -> bool:
    normalized = str(value or "").strip()
    if not normalized:
        return False
    if normalized == GITHUB_PAGES_TESTSITE_LEGACY_ROOT_DOMAIN:
        return True
    parsed = urlparse(normalized)
    if parsed.scheme != "https" or parsed.netloc != "evinaeva.github.io":
        return False
    if parsed.params or parsed.query or parsed.fragment:
        return False
    return (parsed.path or "").startswith(GITHUB_PAGES_TESTSITE_PROJECT_PREFIX)


def _normalize_testsite_domain_key(value: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        return ""
    if _is_github_pages_testsite_alias(normalized):
        return GITHUB_PAGES_TESTSITE_CANONICAL_DOMAIN
    return normalized


def _normalize_check_languages_domain(value: str) -> str:
    return _normalize_testsite_domain_key(str(value or "").strip())


def _resolve_check_languages_domain(payload: dict[str, str]) -> str:
    return _normalize_check_languages_domain(str(payload.get("selected_domain", "")) or str(payload.get("domain", "")))


def _parse_github_pages_project_language_url(value: str) -> dict | None:
    parsed = urlparse(str(value or "").strip())
    if parsed.scheme != "https" or parsed.netloc != "evinaeva.github.io":
        return None
    if parsed.params or parsed.query or parsed.fragment:
        return None
    match = re.match(r"^(/[^/]+)/([a-z]{2}(?:-[a-z]{2})?)/(.*)$", parsed.path or "", flags=re.IGNORECASE)
    if not match:
        return None
    project_prefix, language, page_tail = match.groups()
    if not page_tail:
        return None
    return {
        "scheme": parsed.scheme,
        "host": parsed.netloc,
        "project_prefix": project_prefix,
        "language": _normalize_target_language(language),
        "page_tail": page_tail,
    }


def _is_supported_check_languages_domain(value: str) -> bool:
    domain = _normalize_check_languages_domain(value)
    return domain in SUPPORTED_CHECK_LANGUAGE_DOMAINS or _parse_github_pages_project_language_url(domain) is not None


def _is_special_check_languages_test_domain(domain: str) -> bool:
    normalized = _normalize_check_languages_domain(domain)
    if not normalized:
        return False
    if normalized == GITHUB_PAGES_TESTSITE_CANONICAL_DOMAIN:
        return True
    parsed = _parse_github_pages_project_language_url(normalized)
    return parsed is not None and parsed.get("project_prefix") == GITHUB_PAGES_TESTSITE_PROJECT_PREFIX


def _build_language_subdomain_domain(domain: str, language: str) -> str:
    parsed = urlparse(domain)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("Selected domain is unsupported.")
    return f"{parsed.scheme}://{language}.{parsed.netloc}/"


def _check_languages_site_family_key(value: str) -> str:
    domain = _normalize_check_languages_domain(value)
    github_pages = _parse_github_pages_project_language_url(domain)
    if github_pages is None:
        return domain
    return f"{github_pages['scheme']}://{github_pages['host']}{github_pages['project_prefix']}"


def _check_languages_run_domains(value: str, list_domains) -> list[str]:
    domain = _normalize_check_languages_domain(value)
    if not domain:
        return []
    if domain in NORMAL_CHECK_LANGUAGE_DOMAINS:
        return [domain]
    if not _is_special_check_languages_test_domain(domain):
        return [domain]
    out = {
        domain,
        GITHUB_PAGES_TESTSITE_CANONICAL_DOMAIN,
        GITHUB_PAGES_TESTSITE_LEGACY_ROOT_DOMAIN,
    }
    try:
        domain_rows = list_domains()
    except Exception:
        domain_rows = []
    for item in domain_rows:
        normalized_item = _normalize_check_languages_domain(item)
        if _is_special_check_languages_test_domain(normalized_item):
            out.add(normalized_item)
    return sorted(out)


def _build_check_languages_target_url(selected_domain: str, target_language: str) -> str:
    if selected_domain in NORMAL_CHECK_LANGUAGE_DOMAINS:
        return _build_language_subdomain_domain(selected_domain, target_language)
    github_pages = _parse_github_pages_project_language_url(selected_domain)
    if github_pages is not None:
        return f"{github_pages['scheme']}://{github_pages['host']}{github_pages['project_prefix']}/{target_language}/{github_pages['page_tail']}"
    raise ValueError("Selected domain is unsupported.")


def _target_capture_url_from_reference_url(reference_url: str, selected_domain: str, generated_target_url: str) -> str:
    source = urlparse(reference_url)
    if not source.scheme or not source.netloc:
        raise ValueError("reference run scope contains invalid URL")
    target = urlparse(generated_target_url)
    if not target.scheme or not target.netloc:
        raise ValueError("generated target URL is invalid")
    if selected_domain in NORMAL_CHECK_LANGUAGE_DOMAINS:
        return urlunparse((target.scheme, target.netloc, source.path, source.params, source.query, source.fragment))
    github_pages = _parse_github_pages_project_language_url(selected_domain)
    if github_pages is not None:
        target_parts = _parse_github_pages_project_language_url(generated_target_url)
        if target_parts is None:
            raise ValueError("generated target URL is invalid")
        source_parts = _parse_github_pages_project_language_url(urlunparse((source.scheme, source.netloc, source.path, "", "", "")))
        page_tail = github_pages["page_tail"]
        if source_parts is not None and source_parts["project_prefix"] == github_pages["project_prefix"]:
            page_tail = source_parts["page_tail"]
        target_path = f"{github_pages['project_prefix']}/{target_parts['language']}/{page_tail}"
        return urlunparse((target.scheme, target.netloc, target_path, source.params, source.query, source.fragment))
    raise ValueError("Selected domain is unsupported.")


def _phase6_artifact_readiness(domain: str, run_id: str) -> dict:
    required = ["eligible_dataset.json", "collected_items.json", "page_screenshots.json"]
    missing: list[str] = []
    read_error: str = ""
    for filename in required:
        try:
            if not _artifact_exists_strict(domain, run_id, filename):
                missing.append(filename)
        except ValueError as exc:
            read_error = str(exc)
            break
    return {"required": required, "missing": missing, "read_error": read_error, "ready": (not missing and not read_error)}


def _run_languages(domain: str, run_id: str) -> set[str]:
    languages: set[str] = set()
    pages = _read_json_safe(domain, run_id, "page_screenshots.json", None)
    if isinstance(pages, list):
        for row in pages:
            if isinstance(row, dict):
                language = str(row.get("language", "")).strip().lower()
                if language:
                    languages.add(language)
    if languages:
        return languages
    dataset = _read_json_safe(domain, run_id, "eligible_dataset.json", None)
    if isinstance(dataset, list):
        for row in dataset:
            if isinstance(row, dict):
                language = str(row.get("language", "")).strip().lower()
                if language:
                    languages.add(language)
    return languages


def _load_check_language_runs(domain: str, *, load_runs, list_domains) -> list[dict]:
    out_map: dict[tuple[str, str], dict] = {}
    for run_domain in _check_languages_run_domains(domain, list_domains):
        try:
            runs_payload = load_runs(run_domain)
        except Exception:
            continue
        runs = runs_payload.get("runs", []) if isinstance(runs_payload, dict) else []
        for row in runs:
            if not isinstance(row, dict):
                continue
            run_id = str(row.get("run_id", "")).strip()
            if not run_id:
                continue
            key = (run_domain, run_id)
            if key in out_map:
                continue
            languages = sorted(_run_languages(run_domain, run_id))
            has_english = any(_is_english_language(lang) for lang in languages)
            has_non_english = any(not _is_english_language(lang) for lang in languages)
            out_map[key] = {
                "domain": run_domain,
                "site_family_key": _check_languages_site_family_key(run_domain),
                "run_id": run_id,
                "created_at": str(row.get("created_at", "")).strip(),
                "display_name": _normalize_optional_string(row.get("display_name")) or "",
                "en_standard_display_name": _normalize_optional_string(row.get("en_standard_display_name")) or "",
                "metadata": row.get("metadata") if isinstance(row.get("metadata"), dict) else {},
                "languages": languages,
                "has_english": has_english,
                "has_non_english": has_non_english,
            }
    out = list(out_map.values())
    out.sort(key=lambda run: (run.get("created_at", ""), run.get("run_id", "")), reverse=True)
    return out


def _load_target_languages(runs: list[dict]) -> list[str]:
    _ = runs
    return [language for language in CANONICAL_TARGET_LANGUAGES if not _is_english_language(language)]


def _run_is_english_only(run: dict) -> bool:
    languages = [str(language).strip().lower() for language in run.get("languages", []) if str(language).strip()]
    return bool(languages) and all(_is_english_language(language) for language in languages)


def _run_has_en_standard_success_marker(run: dict) -> bool:
    if bool(run.get("en_standard_success", False)):
        return True
    metadata = run.get("metadata") if isinstance(run.get("metadata"), dict) else {}
    if not isinstance(metadata, dict):
        return False
    if bool(metadata.get("en_standard_success", False)):
        return True
    status = str(metadata.get("en_standard_status", "")).strip().lower()
    return status in {"success", "succeeded", "ready"}


def _run_is_explicit_en_reference(run: dict) -> bool:
    metadata = run.get("metadata") if isinstance(run.get("metadata"), dict) else {}
    if _normalize_optional_string(run.get("en_standard_display_name")):
        return True
    if isinstance(metadata, dict) and _normalize_optional_string(metadata.get("en_standard_display_name")):
        return True
    return _run_has_en_standard_success_marker(run)


def _run_is_en_reference_candidate(run: dict) -> bool:
    return _run_is_explicit_en_reference(run) or _run_is_english_only(run)


def _default_english_reference_run_id(en_candidates: list[dict]) -> str:
    ordered = sorted(en_candidates, key=lambda row: (row.get("created_at", ""), row.get("run_id", "")), reverse=True)
    explicit = [run for run in ordered if _run_is_explicit_en_reference(run)]
    if explicit:
        return str(explicit[0].get("run_id", "")).strip()
    first_run_english = [
        run
        for run in ordered
        if _run_is_english_only(run) and (_normalize_optional_string(run.get("display_name")) or "").startswith("First_run_")
    ]
    if first_run_english:
        return str(first_run_english[0].get("run_id", "")).strip()
    english_only = [run for run in ordered if _run_is_english_only(run)]
    return str((english_only[0] or {}).get("run_id", "")).strip() if english_only else ""


def _run_display_label(run: dict) -> str:
    metadata = run.get("metadata") if isinstance(run.get("metadata"), dict) else {}
    display = ""
    if isinstance(run, dict):
        display = (
            _normalize_optional_string(run.get("en_standard_display_name"))
            or _normalize_optional_string(run.get("display_label"))
            or _normalize_optional_string(run.get("display_name"))
            or ""
        )
    if isinstance(metadata, dict):
        display = (
            display
            or _normalize_optional_string(metadata.get("en_standard_display_name"))
            or _normalize_optional_string(metadata.get("display_label"))
            or _normalize_optional_string(metadata.get("display_name"))
            or ""
        )
    return display or str(run.get("run_id", "")).strip()


def _latest_successful_en_standard_run_id(domain: str, en_candidates: list[dict]) -> str:
    for run in sorted(en_candidates, key=lambda row: (row.get("created_at", ""), row.get("run_id", "")), reverse=True):
        run_id = str(run.get("run_id", "")).strip()
        if not run_id:
            continue
        run_domain = str(run.get("domain", "")).strip() or domain
        readiness = _phase6_artifact_readiness(run_domain, run_id)
        if readiness.get("ready") or _run_has_en_standard_success_marker(run):
            return run_id
    return ""


def _replay_scope_from_reference_run(domain: str, en_run_id: str, target_language: str, target_url: str) -> list[dict]:
    from pipeline.run_phase1 import build_exact_context_job

    pages = _read_list_artifact_required(domain, en_run_id, "page_screenshots.json")
    unique_contexts: dict[tuple[str, str, str, str | None, str | None, str | None], dict] = {}
    for row in pages:
        if not isinstance(row, dict):
            continue
        language = str(row.get("language", "")).strip()
        if not _is_english_language(language):
            continue
        reference_url = str(row.get("url", "")).strip()
        viewport_kind = str(row.get("viewport_kind", "")).strip()
        state = str(row.get("state", "")).strip()
        user_tier_raw = row.get("user_tier")
        user_tier = str(user_tier_raw).strip() if user_tier_raw not in (None, "") else None
        recipe_id = _normalize_optional_string(row.get("recipe_id"))
        capture_point_id = _normalize_optional_string(row.get("capture_point_id"))
        if not reference_url or not viewport_kind or not state:
            raise ValueError("reference run scope is incomplete in page_screenshots.json")
        url = _target_capture_url_from_reference_url(reference_url, domain, target_url)
        key = (url, viewport_kind, state, user_tier, recipe_id, capture_point_id)
        unique_contexts[key] = {
            "url": url,
            "viewport_kind": viewport_kind,
            "state": state,
            "user_tier": user_tier,
            "recipe_id": recipe_id,
            "capture_point_id": capture_point_id,
        }
    if not unique_contexts:
        raise ValueError("reference run has no English capture scope to replay")
    jobs: list[dict] = []
    for key in sorted(unique_contexts.keys()):
        context = unique_contexts[key]
        jobs.append(
            build_exact_context_job(
                domain,
                context["url"],
                target_language,
                context["viewport_kind"],
                context["state"],
                context["user_tier"],
                recipe_id=context.get("recipe_id"),
                capture_point_id=context.get("capture_point_id"),
            )
        )
    return jobs


def _generate_target_run_id(domain: str, en_run_id: str, target_language: str, *, load_runs, list_domains) -> str:
    existing: set[str] = set()
    for run_domain in _check_languages_run_domains(domain, list_domains):
        try:
            runs_payload = load_runs(run_domain)
        except Exception:
            continue
        runs = runs_payload.get("runs", []) if isinstance(runs_payload, dict) else []
        existing.update({str(row.get("run_id", "")).strip() for row in runs if isinstance(row, dict)})
    base = f"{en_run_id}-check-{target_language}"
    candidate = base
    suffix = 1
    while candidate in existing:
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def _find_in_progress_check_languages_job(
    domain: str,
    en_run_id: str,
    target_language: str,
    *,
    load_runs,
    list_domains,
    as_stale_failed_job,
    is_stale_running_job,
) -> dict | None:
    for run_domain in _check_languages_run_domains(domain, list_domains):
        try:
            runs_payload = load_runs(run_domain)
        except Exception:
            continue
        runs = runs_payload.get("runs", []) if isinstance(runs_payload, dict) else []
        for run in runs:
            if not isinstance(run, dict):
                continue
            for job in run.get("jobs", []):
                if not isinstance(job, dict):
                    continue
                effective_job = as_stale_failed_job(job) if is_stale_running_job(job) else dict(job)
                status = str(effective_job.get("status", "")).strip().lower()
                if status not in {"running", "queued"}:
                    continue
                if str(effective_job.get("type", "")).strip() != "check_languages":
                    continue
                if str(effective_job.get("en_run_id", "")).strip() != en_run_id:
                    continue
                if _normalize_target_language(str(effective_job.get("target_language", ""))) != target_language:
                    continue
                found = dict(effective_job)
                found["domain"] = run_domain
                return found
    return None


def _latest_check_languages_job(domain: str, run_id: str, *, load_runs, list_domains, as_stale_failed_job, is_stale_running_job) -> dict | None:
    candidates: list[dict] = []
    for run_domain in _check_languages_run_domains(domain, list_domains):
        try:
            runs_payload = load_runs(run_domain)
        except Exception:
            continue
        runs = runs_payload.get("runs", []) if isinstance(runs_payload, dict) else []
        run = next((row for row in runs if isinstance(row, dict) and str(row.get("run_id", "")).strip() == run_id), None)
        if not isinstance(run, dict):
            continue
        jobs = run.get("jobs", []) if isinstance(run.get("jobs", []), list) else []
        for index, job in enumerate(jobs):
            if not isinstance(job, dict) or str(job.get("type", "")).strip() != "check_languages":
                continue
            item = as_stale_failed_job(job) if is_stale_running_job(job) else dict(job)
            item["domain"] = run_domain
            item["_job_index"] = index
            candidates.append(item)
    if not candidates:
        return None
    candidates.sort(key=lambda row: (str(row.get("updated_at", "")), str(row.get("created_at", "")), int(row.get("_job_index", -1))))
    latest = dict(candidates[-1])
    latest.pop("_job_index", None)
    return latest


def _check_languages_source_hashes(domain: str, en_run_id: str, target_run_id: str) -> dict[str, str]:
    return {
        "en_eligible_dataset_sha256": _stable_json_hash(_read_json_safe(domain, en_run_id, "eligible_dataset.json", [])),
        "target_eligible_dataset_sha256": _stable_json_hash(_read_json_safe(domain, target_run_id, "eligible_dataset.json", [])),
        "en_collected_items_sha256": _stable_json_hash(_read_json_safe(domain, en_run_id, "collected_items.json", [])),
        "target_collected_items_sha256": _stable_json_hash(_read_json_safe(domain, target_run_id, "collected_items.json", [])),
        "en_page_screenshots_sha256": _stable_json_hash(_read_json_safe(domain, en_run_id, "page_screenshots.json", [])),
        "target_page_screenshots_sha256": _stable_json_hash(_read_json_safe(domain, target_run_id, "page_screenshots.json", [])),
    }


def _check_languages_payload_status(domain: str, run_id: str) -> dict:
    files = ["eligible_dataset.json", "collected_items.json", "page_screenshots.json"]
    rows: list[dict] = []
    all_present = True
    for filename in files:
        exists = _artifact_exists(domain, run_id, filename)
        payload = _read_json_safe(domain, run_id, filename, None) if exists else None
        valid = isinstance(payload, list)
        stale = isinstance(payload, list) and len(payload) == 0
        status = "present"
        if not exists:
            status = "missing"
            all_present = False
        elif not valid:
            status = "invalid"
            all_present = False
        elif stale:
            status = "stale"
        rows.append({"filename": filename, "path": f"{domain}/{run_id}/{filename}", "status": status, "payload": payload if isinstance(payload, list) else payload})
    return {"ready": all_present, "files": rows}


def _is_missing_artifact_error(exc: Exception) -> bool:
    if isinstance(exc, FileNotFoundError):
        return True
    if isinstance(exc, KeyError):
        return True
    class_name = exc.__class__.__name__.strip().lower()
    if class_name == "notfound":
        return True
    text = str(exc).strip().lower()
    return "not found" in text or "404" in text


def _check_languages_llm_input_artifact_status(domain: str, run_id: str) -> dict:
    preview_filename = "check_languages_llm_input_preview.json"
    try:
        preview_payload = storage.read_json_artifact(domain, run_id, preview_filename)
    except json.JSONDecodeError as exc:
        print(f"[storage] read malformed_json domain={domain} run_id={run_id} file={preview_filename}: {exc}", file=sys.stderr)
        return {"status": "malformed_json", "exists": True, "payload": None, "error": str(exc)}
    except Exception as exc:
        preview_status = "missing" if _is_missing_artifact_error(exc) else "read_error"
        print(f"[storage] read {preview_status} domain={domain} run_id={run_id} file={preview_filename}: {exc}", file=sys.stderr)
        if preview_status != "missing":
            return {"status": preview_status, "exists": True, "payload": None, "error": str(exc)}
        # Backward compatibility for older runs that do not have the lightweight preview artifact yet.
        try:
            preview_payload = storage.read_json_artifact(domain, run_id, "check_languages_llm_input.json")
        except json.JSONDecodeError as fallback_exc:
            print(f"[storage] read malformed_json domain={domain} run_id={run_id} file=check_languages_llm_input.json: {fallback_exc}", file=sys.stderr)
            return {"status": "malformed_json", "exists": True, "payload": None, "error": str(fallback_exc)}
        except Exception as fallback_exc:
            status = "missing" if _is_missing_artifact_error(fallback_exc) else "read_error"
            print(f"[storage] read {status} domain={domain} run_id={run_id} file=check_languages_llm_input.json: {fallback_exc}", file=sys.stderr)
            return {"status": status, "exists": status != "missing", "payload": None, "error": str(fallback_exc)}
    if not isinstance(preview_payload, dict):
        return {"status": "invalid_payload", "exists": True, "payload": None, "error": "expected object"}
    sample_review_context = preview_payload.get("sample_review_context")
    review_contexts = preview_payload.get("review_contexts")
    if sample_review_context is None and isinstance(review_contexts, list) and review_contexts:
        sample_review_context = review_contexts[0]
    normalized_preview_payload = {
        "target_language": preview_payload.get("target_language"),
        "review_context_count": preview_payload.get("review_context_count"),
        "blocked_pages": preview_payload.get("blocked_pages") if isinstance(preview_payload.get("blocked_pages"), list) else [],
        "source_hashes": preview_payload.get("source_hashes") if isinstance(preview_payload.get("source_hashes"), dict) else {},
        "review_contexts": [sample_review_context] if sample_review_context is not None else [],
    }
    return {"status": "valid", "exists": True, "payload": normalized_preview_payload, "error": ""}


def _check_languages_llm_review_telemetry_status(domain: str, run_id: str) -> dict:
    try:
        payload = storage.read_json_artifact(domain, run_id, "llm_review_stats.json")
    except json.JSONDecodeError as exc:
        print(f"[storage] read malformed_json domain={domain} run_id={run_id} file=llm_review_stats.json: {exc}", file=sys.stderr)
        return {"status": "malformed_json", "exists": True, "payload": None, "error": str(exc)}
    except Exception as exc:
        status = "missing" if _is_missing_artifact_error(exc) else "read_error"
        print(f"[storage] read {status} domain={domain} run_id={run_id} file=llm_review_stats.json: {exc}", file=sys.stderr)
        return {"status": status, "exists": status != "missing", "payload": None, "error": str(exc)}
    if not isinstance(payload, dict):
        return {"status": "invalid_payload", "exists": True, "payload": None, "error": "expected object"}
    return {"status": "valid", "exists": True, "payload": payload, "error": ""}


def _check_languages_llm_request_artifact_status(domain: str, run_id: str) -> dict:
    filename = "check_languages_llm_request.json"
    try:
        payload = storage.read_json_artifact(domain, run_id, filename)
    except json.JSONDecodeError as exc:
        print(f"[storage] read malformed_json domain={domain} run_id={run_id} file={filename}: {exc}", file=sys.stderr)
        return {"status": "malformed_json", "exists": True, "payload": None, "error": str(exc)}
    except Exception as exc:
        status = "missing" if _is_missing_artifact_error(exc) else "read_error"
        print(f"[storage] read {status} domain={domain} run_id={run_id} file={filename}: {exc}", file=sys.stderr)
        return {"status": status, "exists": status != "missing", "payload": None, "error": str(exc)}
    if not isinstance(payload, dict):
        return {"status": "invalid_payload", "exists": True, "payload": None, "error": "expected object"}
    return {"status": "valid", "exists": True, "payload": payload, "error": ""}


def _parse_gs_uri_safe(uri: str) -> tuple[str, str, str, str] | None:
    parsed = _parse_gs_uri(uri)
    if not parsed:
        return None
    bucket, path = parsed
    normalized_path = str(path or "").strip("/")
    if not normalized_path:
        return None
    try:
        domain, run_id, filename = normalized_path.rsplit("/", 2)
    except ValueError:
        return None
    if not bucket or not domain or not run_id or not filename:
        return None
    return bucket, domain, run_id, filename


def _build_exception_diagnostics(exc: Exception, *, stage: str, substage: str, replay_context: dict | None = None) -> dict:
    root = exc
    if isinstance(exc, SystemExit) and exc.__cause__ is not None:
        cause = exc.__cause__
        if isinstance(cause, Exception):
            root = cause
    diag = {
        "stage": stage,
        "substage": substage,
        "exception_class": root.__class__.__name__,
        "message": str(root),
        "traceback": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
        "failure_timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if replay_context:
        diag["replay_context"] = replay_context
    return diag


def _persist_check_languages_failure_artifacts(domain: str, run_id: str, diagnostics: dict) -> dict:
    from pipeline.storage import BUCKET_NAME, write_json_artifact, write_text_artifact

    failure_uri = write_json_artifact(domain, run_id, "check_languages_replay_failure.json", diagnostics)
    traceback_uri = write_text_artifact(domain, run_id, "check_languages_replay_failure.traceback.txt", str(diagnostics.get("traceback", "")))
    return {
        "failure_json": failure_uri,
        "traceback": traceback_uri,
        "failure_json_path": f"{domain}/{run_id}/check_languages_replay_failure.json",
        "traceback_path": f"{domain}/{run_id}/check_languages_replay_failure.traceback.txt",
        "bucket": BUCKET_NAME,
    }


def _persist_check_languages_failure_artifacts_safe(domain: str, run_id: str, diagnostics: dict) -> tuple[dict, str | None]:
    try:
        return _persist_check_languages_failure_artifacts(domain, run_id, diagnostics), None
    except Exception as artifact_exc:
        return {}, str(artifact_exc)


def _replay_unit_diagnostics(exc: Exception, replay_jobs: list[dict], *, target_url: str, en_run_id: str, target_run_id: str, target_language: str) -> dict:
    message = str(exc)
    matched_job: dict | None = None
    for job in replay_jobs:
        ctx = getattr(job, "context", None)
        job_url = str(getattr(ctx, "url", "")) if ctx is not None else ""
        if job_url and job_url in message:
            matched_job = job
            break
    if matched_job is None and replay_jobs:
        matched_job = replay_jobs[0]
    ctx = getattr(matched_job, "context", None) if matched_job is not None else None
    recipe_id = _normalize_optional_string(getattr(matched_job, "recipe_id", None)) if matched_job is not None else None
    capture_point_id = _normalize_optional_string(getattr(matched_job, "capture_point_id", None)) if matched_job is not None else None
    unit = {
        "reference_url": str(getattr(ctx, "url", "")) if ctx is not None else "",
        "target_url": str(getattr(ctx, "url", "")) if ctx is not None else target_url,
        "state": str(getattr(ctx, "state", "")) if ctx is not None else "baseline",
        "recipe_id": recipe_id or "",
        "capture_point_id": capture_point_id or "",
        "run_id": en_run_id,
        "target_run_id": target_run_id,
        "target_language": target_language,
        "page_classification": "scripted" if recipe_id else "baseline",
        "replay_unit_id": f"{str(getattr(ctx, 'url', ''))}|{str(getattr(ctx, 'state', ''))}|{recipe_id or 'baseline'}",
        "failing_url": str(getattr(ctx, "url", "")) if ctx is not None else "",
        "screenshot_path": None,
        "html_dump_path": None,
        "artifact_capture_note": "No browser page object available at orchestration layer for failed replay unit.",
    }
    return unit
