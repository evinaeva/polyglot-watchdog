"""Check-languages UI slice extracted from skeleton_server."""

from __future__ import annotations

import asyncio
import datetime
import json
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from http import HTTPStatus
from urllib.parse import urlencode

from app.artifact_helpers import (
    _artifact_exists,
    _read_json_artifact_from_gs_uri,
    _read_json_safe,
    _require_artifact_exists,
)
from app.check_languages_presenter import _h, _llm_review_display
from app.check_languages_service import (
    SUPPORTED_CHECK_LANGUAGE_DOMAINS,
    _build_check_languages_target_url,
    _build_exception_diagnostics,
    _check_languages_llm_input_artifact_status,
    _check_languages_llm_request_artifact_status,
    _check_languages_llm_review_telemetry_status,
    _check_languages_payload_status,
    _check_languages_source_hashes,
    _default_english_reference_run_id,
    _is_english_language,
    _is_supported_check_languages_domain,
    _latest_successful_en_standard_run_id,
    _load_target_languages,
    _normalize_check_languages_domain,
    _normalize_testsite_domain_key,
    _normalize_target_language,
    _parse_gs_uri_safe,
    _persist_check_languages_failure_artifacts_safe,
    _phase6_artifact_readiness,
    _replay_scope_from_reference_run,
    _replay_unit_diagnostics,
    _resolve_check_languages_domain,
    _run_display_label,
    _run_is_en_reference_candidate,
)
from app.issues_utils import _format_summary_pairs, _summarize_issues_payload
from app.server_utils import _as_bool, _as_int, _parse_utc_timestamp, _validate_run_id
from app.seed_urls import validate_domain
from pipeline import storage


def prepare_check_languages_async(job_id: str, domain: str, en_run_id: str, target_language: str, target_run_id: str, target_url: str, *, jobs: dict[str, dict], upsert_job_status: Callable[[str, str, dict], None]) -> None:
    jobs[job_id] = {
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
        upsert_job_status(domain, target_run_id, {
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
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(exc)
        upsert_job_status(domain, target_run_id, {
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
        upsert_job_status(domain, target_run_id, {
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
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = error
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
        upsert_job_status(domain, target_run_id, failed_record)
        return

    try:
        upsert_job_status(domain, target_run_id, {
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
        jobs[job_id]["status"] = "done"
        upsert_job_status(domain, target_run_id, {
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
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(exc)
        upsert_job_status(domain, target_run_id, {
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


def run_check_languages_llm_async(job_id: str, domain: str, en_run_id: str, target_language: str, target_run_id: str, target_url: str, *, jobs: dict[str, dict], upsert_job_status: Callable[[str, str, dict], None]) -> None:
    from pipeline.run_phase6 import run as phase6_run

    jobs[job_id] = {"status": "running", "phase": "check_languages_llm", "domain": domain, "run_id": target_run_id}
    try:
        llm_preflight_error = check_languages_llm_preflight_error()
        if llm_preflight_error:
            raise CheckLanguagesLlmPreflightError(llm_preflight_error)
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
        upsert_job_status(domain, target_run_id, {
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
        jobs[job_id]["status"] = "done"
        upsert_job_status(domain, target_run_id, {
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
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(exc)
        stage = "running_llm_review_failed"
        workflow_state = "failed_during_llm"
        if isinstance(exc, CheckLanguagesLlmPreflightError):
            stage = "llm_preflight_failed"
            workflow_state = "failed_before_llm"
        upsert_job_status(domain, target_run_id, {
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


def check_languages_llm_preflight_error() -> str | None:
    review_mode = os.environ.get("PHASE6_REVIEW_PROVIDER", "").strip()
    if not review_mode:
        return "LLM review cannot start: PHASE6_REVIEW_PROVIDER is not configured."
    return None


class CheckLanguagesLlmPreflightError(ValueError):
    """Raised when LLM stage launch preflight fails before Phase 6 execution."""


# Legacy combined prepare+LLM flow retained intentionally for non-UI and test utility paths.
# The UI handler path currently runs prepare_check_languages_async and
# run_check_languages_llm_async as separate stages instead of calling this wrapper.
def run_check_languages_async(job_id: str, domain: str, en_run_id: str, target_language: str, target_run_id: str, target_url: str, *, jobs: dict[str, dict], upsert_job_status: Callable[[str, str, dict], None], latest_check_languages_job: Callable[[str, str], dict | None]) -> None:
    """Backward-compatible composed flow: prepare payload, then run LLM review."""
    prepare_check_languages_async(job_id, domain, en_run_id, target_language, target_run_id, target_url, jobs=jobs, upsert_job_status=upsert_job_status)
    latest = latest_check_languages_job(domain, target_run_id)
    if not isinstance(latest, dict):
        return
    if str(latest.get("workflow_state", "")).strip().lower() != "prepared_for_llm":
        return
    llm_preflight_error = check_languages_llm_preflight_error()
    if llm_preflight_error:
        upsert_job_status(domain, target_run_id, {
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
    run_check_languages_llm_async(llm_job_id, domain, en_run_id, target_language, target_run_id, target_url, jobs=jobs, upsert_job_status=upsert_job_status)


@dataclass
class CheckLanguagesUIController:
    send_response: Callable[[HTTPStatus], None]
    send_header: Callable[[str, str], None]
    end_headers: Callable[[], None]
    serve_template: Callable[..., None]
    ensure_csrf_cookie: Callable[[], str]
    build_cookie_header: Callable[..., str]
    default_check_languages_domain: Callable[[], str]
    load_check_language_runs: Callable[[str], list[dict]]
    find_in_progress_check_languages_job: Callable[[str, str, str], dict | None]
    latest_check_languages_job: Callable[[str, str], dict | None]
    generate_target_run_id: Callable[[str, str, str], str]
    upsert_job_status: Callable[[str, str, dict], None]
    prepare_check_languages_async: Callable[[str, str, str, str, str, str], None]
    run_check_languages_llm_async: Callable[[str, str, str, str, str, str], None]
    check_languages_llm_preflight_error: Callable[[], str | None]
    csrf_cookie_name: str
    session_max_age_seconds: int

    def handle_get(self, query: dict[str, list[str]]) -> None:
        self.serve_check_languages_page(query)

    def handle_post(self, payload: dict[str, str]) -> None:
        self.start_check_languages(payload)

    def redirect_check_languages(self, payload: dict[str, str], *, message: str = "", level: str = "") -> None:
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

    def start_check_languages(self, payload: dict[str, str]) -> None:
        action = str(payload.get("action", "prepare_payload")).strip() or "prepare_payload"
        domain = _resolve_check_languages_domain(payload)
        en_run_id = str(payload.get("en_run_id", "")).strip()
        target_language = _normalize_target_language(str(payload.get("target_language", "")))
        if action == "recompute_gate":
            redirect_payload = dict(payload)
            redirect_payload["selected_domain"] = domain
            redirect_payload["show_gate_diagnostics"] = "1"
            self.redirect_check_languages(
                redirect_payload,
                message="LLM gate diagnostics recomputed from current artifacts.",
                level="ok",
            )
            return
        if action == "refresh_llm_status":
            redirect_payload = dict(payload)
            redirect_payload["selected_domain"] = domain
            redirect_payload["show_gate_diagnostics"] = "1"
            self.redirect_check_languages(
                redirect_payload,
                message="LLM review status refreshed from current job and telemetry artifacts.",
                level="ok",
            )
            return

        if not domain:
            self.redirect_check_languages(payload, message="Domain is required.", level="error")
            return
        if not en_run_id:
            self.redirect_check_languages(payload, message="English reference run is required.", level="error")
            return
        try:
            en_run_id = _validate_run_id(en_run_id)
        except ValueError as exc:
            self.redirect_check_languages(payload, message=str(exc), level="error")
            return
        if not target_language:
            self.redirect_check_languages(payload, message="Target language is required.", level="error")
            return
        if _is_english_language(target_language):
            self.redirect_check_languages(payload, message="Target language must be non-English.", level="error")
            return

        try:
            validate_domain(_normalize_testsite_domain_key(domain))
            generated_target_url = _build_check_languages_target_url(domain, target_language)
        except ValueError as exc:
            self.redirect_check_languages(payload, message=str(exc), level="error")
            return

        runs = self.load_check_language_runs(domain)
        run_map = {str(row.get("run_id", "")): row for row in runs}
        en_run = run_map.get(en_run_id)
        if en_run is None:
            self.redirect_check_languages(payload, message="Selected English reference run is invalid for this domain.", level="error")
            return
        if not _run_is_en_reference_candidate(en_run):
            self.redirect_check_languages(payload, message="Selected reference run is not a valid English baseline.", level="error")
            return
        run_domain = str(en_run.get("domain", "")).strip() or domain

        en_readiness = _phase6_artifact_readiness(run_domain, en_run_id)
        if not en_readiness.get("ready"):
            self.redirect_check_languages(payload, message="English reference run is not ready for comparison prerequisites.", level="error")
            return

        available_languages = set(_load_target_languages(runs))
        if target_language not in available_languages:
            self.redirect_check_languages(payload, message="Selected target language is invalid for this domain.", level="error")
            return

        in_progress = self.find_in_progress_check_languages_job(run_domain, en_run_id, target_language)
        if in_progress:
            existing_payload = dict(payload)
            existing_payload["target_run_id"] = str(in_progress.get("run_id", ""))
            self.redirect_check_languages(existing_payload, message="Language check is already in progress for this selection.", level="warning")
            return

        selected_run_candidates: list[dict[str, object]] = []
        for row in runs:
            if not isinstance(row, dict):
                continue
            row_run_id = str(row.get("run_id", "")).strip()
            if not row_run_id:
                continue
            row_latest_job = self.latest_check_languages_job(run_domain, row_run_id)
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
                self.redirect_check_languages(payload, message=str(exc), level="error")
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
            target_run_id = self.generate_target_run_id(run_domain, en_run_id, target_language)
        if action == "prepare_payload":
            latest_selected_job = self.latest_check_languages_job(run_domain, target_run_id)
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
                self.redirect_check_languages(
                    payload,
                    message=f"LLM review is already in progress for run {target_run_id}.",
                    level="warning",
                )
                return
        if action == "run_llm_review":
            prepared = _read_json_safe(run_domain, target_run_id, "check_languages_prepared_payload.json", None)
            if not isinstance(prepared, dict):
                self.redirect_check_languages(payload, message="Prepared payload is missing or invalid. Run preparation first.", level="error")
                return
            llm_preflight_error = self.check_languages_llm_preflight_error()
            if llm_preflight_error:
                self.redirect_check_languages(payload, message=llm_preflight_error, level="error")
                return
            expected_hashes = prepared.get("source_hashes") if isinstance(prepared.get("source_hashes"), dict) else {}
            if expected_hashes and expected_hashes != _check_languages_source_hashes(run_domain, en_run_id, target_run_id):
                self.redirect_check_languages(payload, message="Prepared payload is stale. Re-run preparation before LLM review.", level="error")
                return
            job_id = f"check-languages-llm-{target_run_id}-{int(time.time())}"
            self.upsert_job_status(run_domain, target_run_id, {
                "job_id": job_id,
                "status": "queued",
                "type": "check_languages",
                "stage": "queued_llm_review",
                "workflow_state": "prepared_for_llm",
                "en_run_id": en_run_id,
                "target_language": target_language,
                "target_url": generated_target_url,
            })
            t = threading.Thread(target=self.run_check_languages_llm_async, args=(job_id, run_domain, en_run_id, target_language, target_run_id, generated_target_url), daemon=True)
            t.start()
            ok_message = "LLM review started from prepared payload."
        else:
            job_id = f"check-languages-prepare-{target_run_id}-{int(time.time())}"
            self.upsert_job_status(run_domain, target_run_id, {
                "job_id": job_id,
                "status": "queued",
                "type": "check_languages",
                "stage": "queued_preparation",
                "workflow_state": "idle",
                "en_run_id": en_run_id,
                "target_language": target_language,
                "target_url": generated_target_url,
            })
            t = threading.Thread(target=self.prepare_check_languages_async, args=(job_id, run_domain, en_run_id, target_language, target_run_id, generated_target_url), daemon=True)
            t.start()
            ok_message = "Language check payload preparation started."

        redirect_payload = dict(payload)
        redirect_payload["selected_domain"] = domain
        redirect_payload["target_run_id"] = target_run_id
        redirect_payload["generated_target_url"] = generated_target_url
        self.redirect_check_languages(redirect_payload, message=ok_message, level="ok")

    def serve_check_languages_page(self, query: dict[str, list[str]]) -> None:
        domain = _normalize_check_languages_domain(str(query.get("selected_domain", [""])[0]) or str(query.get("domain", [""])[0]))
        if not domain:
            domain = self.default_check_languages_domain()
        selected_en_run_id = str(query.get("en_run_id", [""])[0]).strip()
        en_run_id_from_query = bool(selected_en_run_id)
        target_language = _normalize_target_language(str(query.get("target_language", [""])[0]))
        target_run_id = str(query.get("target_run_id", [""])[0]).strip()
        generated_target_url = str(query.get("generated_target_url", [""])[0]).strip()
        message = str(query.get("message", [""])[0]).strip()
        level = str(query.get("level", [""])[0]).strip().lower()
        show_gate_diagnostics = _as_bool(str(query.get("show_gate_diagnostics", [""])[0]).strip())
        csrf_token = self.ensure_csrf_cookie()

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
            runs = self.load_check_language_runs(domain)
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
                job = self.latest_check_languages_job(domain, run_id)
                if not isinstance(job, dict):
                    continue
                if str(job.get("en_run_id", "")) == selected_en_run_id and _normalize_target_language(str(job.get("target_language", ""))) == target_language:
                    target_run_id = run_id
                    break

        if selected_en_run_id and target_language and target_run_id and not errors:
            latest_job = self.latest_check_languages_job(domain, target_run_id)
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
                f"<li>latest_job_selection_source: <strong>self.latest_check_languages_job(domain, target_run_id)</strong></li>"
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

        self.serve_template(
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
            extra_set_cookies=[self.build_cookie_header(self.csrf_cookie_name, csrf_token, max_age=self.session_max_age_seconds, http_only=False)],
        )
