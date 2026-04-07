from __future__ import annotations

import os
from typing import Callable


def run_phase0_async(job_id: str, domain: str, run_id: str, *, jobs: dict[str, dict], upsert_job_status: Callable[[str, str, dict], None]) -> None:
    jobs[job_id] = {"status": "running", "phase": "0", "domain": domain, "run_id": run_id}
    try:
        from pipeline.run_phase0 import run as phase0_run

        phase0_run(domain=domain, run_id=run_id)
        jobs[job_id]["status"] = "done"
        upsert_job_status(domain, run_id, {"job_id": job_id, "status": "succeeded", "phase": "0"})
    except Exception as exc:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(exc)
        upsert_job_status(domain, run_id, {"job_id": job_id, "status": "failed", "error": str(exc), "phase": "0"})


def run_phase1_async(
    job_id: str,
    runtime_payload: dict,
    *,
    jobs: dict[str, dict],
    upsert_job_status: Callable[[str, str, dict], None],
    load_phase1_runtime_config: Callable[[dict], object],
) -> None:
    jobs[job_id] = {"status": "running", "phase": "1", "domain": runtime_payload.get("domain"), "run_id": runtime_payload.get("run_id")}
    upsert_job_status(str(runtime_payload.get("domain")), str(runtime_payload.get("run_id")), {"job_id": job_id, "status": "running", "context": runtime_payload})
    try:
        from pipeline.run_phase1 import run_with_config

        config = load_phase1_runtime_config(runtime_payload)
        run_with_config(config)
        jobs[job_id]["status"] = "done"
        upsert_job_status(str(runtime_payload.get("domain")), str(runtime_payload.get("run_id")), {"job_id": job_id, "status": "succeeded", "context": runtime_payload})
    except Exception as exc:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(exc)
        upsert_job_status(
            str(runtime_payload.get("domain")),
            str(runtime_payload.get("run_id")),
            {"job_id": job_id, "status": "failed", "error": str(exc), "context": runtime_payload, "type": "capture"},
        )


def run_rerun_async(job_id: str, runtime_payload: dict, *, jobs: dict[str, dict], upsert_job_status: Callable[[str, str, dict], None]) -> None:
    jobs[job_id] = {"status": "running", "phase": "rerun", "domain": runtime_payload.get("domain"), "run_id": runtime_payload.get("run_id")}
    upsert_job_status(str(runtime_payload.get("domain")), str(runtime_payload.get("run_id")), {"job_id": job_id, "status": "running", "context": runtime_payload, "type": "rerun"})
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
        jobs[job_id]["status"] = "done"
        upsert_job_status(str(runtime_payload.get("domain")), str(runtime_payload.get("run_id")), {"job_id": job_id, "status": "succeeded", "context": runtime_payload, "type": "rerun"})
    except Exception as exc:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(exc)
        upsert_job_status(str(runtime_payload.get("domain")), str(runtime_payload.get("run_id")), {"job_id": job_id, "status": "failed", "error": str(exc), "context": runtime_payload, "type": "rerun"})


def run_phase3_async(
    job_id: str,
    domain: str,
    run_id: str,
    *,
    jobs: dict[str, dict],
    require_artifact_exists: Callable[[str, str, str], None],
    en_standard_display_name_today: Callable[[], str],
    upsert_job_status: Callable[[str, str, dict], None],
    upsert_run_metadata: Callable[[str, str, dict], None],
) -> None:
    jobs[job_id] = {"status": "running", "phase": "3", "domain": domain, "run_id": run_id}
    try:
        from pipeline.run_phase3 import run as phase3_run

        phase3_run(domain=domain, run_id=run_id)
        require_artifact_exists(domain, run_id, "eligible_dataset.json")
        en_standard_display_name = en_standard_display_name_today()
        jobs[job_id]["status"] = "done"
        upsert_job_status(domain, run_id, {"job_id": job_id, "status": "succeeded", "phase": "3"})
        upsert_run_metadata(domain, run_id, {"en_standard_display_name": en_standard_display_name})
    except Exception as exc:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(exc)
        upsert_job_status(domain, run_id, {"job_id": job_id, "status": "failed", "phase": "3", "error": str(exc)})


def run_phase6_async(job_id: str, domain: str, run_id: str, en_run_id: str, *, jobs: dict[str, dict], upsert_job_status: Callable[[str, str, dict], None]) -> None:
    jobs[job_id] = {"status": "running", "phase": "6", "domain": domain, "run_id": run_id, "en_run_id": en_run_id}
    try:
        from pipeline.run_phase6 import run as phase6_run

        review_mode = os.environ.get("PHASE6_REVIEW_PROVIDER", "").strip()
        if not review_mode:
            raise ValueError("PHASE6_REVIEW_PROVIDER is required for Phase 6 execution")
        phase6_run(domain=domain, en_run_id=en_run_id, target_run_id=run_id, review_mode=review_mode)
        jobs[job_id]["status"] = "done"
        upsert_job_status(domain, run_id, {"job_id": job_id, "status": "succeeded", "phase": "6", "en_run_id": en_run_id})
    except Exception as exc:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(exc)
        upsert_job_status(domain, run_id, {"job_id": job_id, "status": "failed", "phase": "6", "en_run_id": en_run_id, "error": str(exc)})
