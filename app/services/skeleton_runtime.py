from __future__ import annotations

import asyncio
import datetime
import os
from typing import Any, Callable

jobs_store: dict[str, dict] = {}


def upsert_job_status(
    domain: str,
    run_id: str,
    job_record: dict,
    *,
    load_runs: Callable[[str], dict],
    save_runs: Callable[[str, dict], None],
    sort_runs_newest_first: Callable[[list[dict]], list[dict]],
    normalize_optional_string: Callable[[Any], str | None],
    time_module: Any,
) -> None:
    runs_payload = load_runs(domain)
    runs = runs_payload["runs"]
    run = next((r for r in runs if r.get("run_id") == run_id), None)
    if run is None:
        run = {"run_id": run_id, "created_at": time_module.strftime("%Y-%m-%dT%H:%M:%SZ", time_module.gmtime()), "jobs": []}
        runs.append(run)
    display_name = normalize_optional_string(job_record.get("display_name"))
    if display_name is not None:
        run["display_name"] = display_name
    elif "display_name" not in run and "display_name" in job_record:
        run["display_name"] = None
    prior_job = next((j for j in run.get("jobs", []) if j.get("job_id") == job_record.get("job_id")), None)
    normalized_job = dict(job_record)
    normalized_job.pop("display_name", None)
    now = time_module.strftime("%Y-%m-%dT%H:%M:%SZ", time_module.gmtime())
    normalized_job["updated_at"] = now
    normalized_job["created_at"] = str((prior_job or {}).get("created_at") or now)
    jobs = [j for j in run.get("jobs", []) if j.get("job_id") != normalized_job.get("job_id")]
    jobs.append(normalized_job)
    jobs.sort(key=lambda r: r.get("job_id", ""))
    run["jobs"] = jobs
    save_runs(domain, {"runs": sort_runs_newest_first(runs)})


def prepare_check_languages_async(
    job_id: str,
    domain: str,
    en_run_id: str,
    target_language: str,
    target_run_id: str,
    target_url: str,
    *,
    upsert_job_status: Callable[[str, str, dict], None],
    replay_scope_from_reference_run: Callable[[str, str, str, str], list[str]],
    require_artifact_exists: Callable[[str, str, str], None],
    replay_unit_diagnostics: Callable[..., dict],
    build_exception_diagnostics: Callable[..., dict],
    persist_check_languages_failure_artifacts: Callable[[str, str, dict], tuple[dict, str | None]],
    check_languages_payload_status: Callable[[str, str], dict],
    check_languages_source_hashes: Callable[[str, str, str], dict],
) -> None:
    jobs_store[job_id] = {
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
        replay_jobs = replay_scope_from_reference_run(domain, en_run_id, target_language, target_url)
    except Exception as exc:
        jobs_store[job_id]["status"] = "error"
        jobs_store[job_id]["error"] = str(exc)
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
        require_artifact_exists(domain, target_run_id, "page_screenshots.json")
        require_artifact_exists(domain, target_run_id, "collected_items.json")
    except Exception as exc:
        replay_context = replay_unit_diagnostics(
            exc,
            replay_jobs,
            target_url=target_url,
            en_run_id=en_run_id,
            target_run_id=target_run_id,
            target_language=target_language,
        )
        diagnostics = build_exception_diagnostics(exc, stage="running_target_capture_failed", substage="phase1_replay", replay_context=replay_context)
        persist_result = persist_check_languages_failure_artifacts(domain, target_run_id, diagnostics)
        if isinstance(persist_result, tuple) and len(persist_result) == 2:
            artifact_refs, artifact_error = persist_result
        else:
            artifact_refs = persist_result if isinstance(persist_result, dict) else {}
            artifact_error = None
        error = f"{diagnostics['exception_class']}: {diagnostics['message']}"
        if artifact_error:
            error = f"{error} (failure artifact persistence warning: {artifact_error})"
        jobs_store[job_id]["status"] = "failed"
        jobs_store[job_id]["error"] = error
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
        require_artifact_exists(domain, target_run_id, "eligible_dataset.json")
        payload_status = check_languages_payload_status(domain, target_run_id)
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
        source_hashes = check_languages_source_hashes(domain, en_run_id, target_run_id)
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
        jobs_store[job_id]["status"] = "done"
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
        jobs_store[job_id]["status"] = "error"
        jobs_store[job_id]["error"] = str(exc)
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


def run_check_languages_llm_async(
    job_id: str,
    domain: str,
    en_run_id: str,
    target_language: str,
    target_run_id: str,
    target_url: str,
    *,
    check_languages_llm_preflight_error: Callable[[], str | None],
    preflight_error_cls: type[Exception],
    read_json_safe: Callable[[str, str, str, Any], Any],
    read_json_artifact_from_gs_uri: Callable[[str], Any],
    check_languages_source_hashes: Callable[[str, str, str], dict],
    upsert_job_status: Callable[[str, str, dict], None],
    require_artifact_exists: Callable[[str, str, str], None],
) -> None:
    from pipeline.run_phase6 import run as phase6_run

    jobs_store[job_id] = {"status": "running", "phase": "check_languages_llm", "domain": domain, "run_id": target_run_id}
    try:
        llm_preflight_error = check_languages_llm_preflight_error()
        if llm_preflight_error:
            raise preflight_error_cls(llm_preflight_error)
        prepared = read_json_safe(domain, target_run_id, "check_languages_prepared_payload.json", None)
        if not isinstance(prepared, dict):
            raise ValueError("Prepared payload missing. Run Prepare language check payload first.")
        llm_input_artifact = str(prepared.get("llm_input_artifact", "")).strip()
        if llm_input_artifact:
            llm_input_payload = read_json_artifact_from_gs_uri(llm_input_artifact)
        else:
            llm_input_payload = read_json_safe(domain, target_run_id, "check_languages_llm_input.json", None)
        if not isinstance(llm_input_payload, dict):
            raise ValueError("Prepared LLM input payload is missing or invalid. Re-run preparation.")
        expected_hashes = prepared.get("source_hashes") if isinstance(prepared.get("source_hashes"), dict) else {}
        actual_hashes = check_languages_source_hashes(domain, en_run_id, target_run_id)
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
        require_artifact_exists(domain, target_run_id, "issues.json")
        jobs_store[job_id]["status"] = "done"
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
        jobs_store[job_id]["status"] = "error"
        jobs_store[job_id]["error"] = str(exc)
        stage = "running_llm_review_failed"
        workflow_state = "failed_during_llm"
        if isinstance(exc, preflight_error_cls):
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


def run_check_languages_async(
    job_id: str,
    domain: str,
    en_run_id: str,
    target_language: str,
    target_run_id: str,
    target_url: str,
    *,
    prepare_check_languages_async: Callable[[str, str, str, str, str, str], None],
    latest_check_languages_job: Callable[[str, str], dict | None],
    check_languages_llm_preflight_error: Callable[[], str | None],
    upsert_job_status: Callable[[str, str, dict], None],
    run_check_languages_llm_async: Callable[[str, str, str, str, str, str], None],
) -> None:
    prepare_check_languages_async(job_id, domain, en_run_id, target_language, target_run_id, target_url)
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
    run_check_languages_llm_async(llm_job_id, domain, en_run_id, target_language, target_run_id, target_url)


def workflow_section_status(*, has_artifact: bool, count: int | None = None, pending_on: bool = False) -> str:
    if has_artifact:
        if count is not None and count == 0:
            return "empty"
        return "ready"
    if pending_on:
        return "not_ready"
    return "not_started"
