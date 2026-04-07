from __future__ import annotations

import os
import time
from typing import Callable


def load_runs(domain: str, *, read_json_safe: Callable[[str, str, str, dict], dict]) -> dict:
    payload = read_json_safe(domain, "manual", "capture_runs.json", {"runs": []})
    if not isinstance(payload, dict) or not isinstance(payload.get("runs"), list):
        return {"runs": []}
    return payload


def sort_runs_newest_first(runs: list[dict], *, parse_utc_timestamp: Callable[[str], float | None]) -> list[dict]:
    def sort_key(run: dict) -> tuple[float, str]:
        created_ts = parse_utc_timestamp(str((run or {}).get("created_at", "")))
        run_id = str((run or {}).get("run_id", ""))
        return (created_ts if created_ts is not None else float("-inf"), run_id)

    return sorted(
        (row for row in runs if isinstance(row, dict)),
        key=sort_key,
        reverse=True,
    )


def save_runs(domain: str, payload: dict, *, write_json_artifact: Callable[[str, str, str, dict], None]) -> None:
    write_json_artifact(domain, "manual", "capture_runs.json", payload)


def upsert_run_metadata(
    domain: str,
    run_id: str,
    metadata: dict,
    *,
    load_runs_fn: Callable[[str], dict],
    save_runs_fn: Callable[[str, dict], None],
    sort_runs_newest_first_fn: Callable[[list[dict]], list[dict]],
) -> None:
    normalized = {str(key).strip(): value for key, value in (metadata or {}).items() if str(key).strip()}
    if not normalized:
        return
    runs_payload = load_runs_fn(domain)
    runs = runs_payload["runs"]
    run = next((r for r in runs if r.get("run_id") == run_id), None)
    if run is None:
        run = {"run_id": run_id, "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "jobs": []}
        runs.append(run)
    for key, value in normalized.items():
        run[key] = value
    save_runs_fn(domain, {"runs": sort_runs_newest_first_fn(runs)})


def upsert_job_status(
    domain: str,
    run_id: str,
    job_record: dict,
    *,
    load_runs_fn: Callable[[str], dict],
    save_runs_fn: Callable[[str, dict], None],
    sort_runs_newest_first_fn: Callable[[list[dict]], list[dict]],
    normalize_optional_string: Callable[[object], str | None],
) -> None:
    runs_payload = load_runs_fn(domain)
    runs = runs_payload["runs"]
    run = next((r for r in runs if r.get("run_id") == run_id), None)
    if run is None:
        run = {"run_id": run_id, "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "jobs": []}
        runs.append(run)
    display_name = normalize_optional_string(job_record.get("display_name"))
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
    save_runs_fn(domain, {"runs": sort_runs_newest_first_fn(runs)})


def is_stale_running_job(job: dict, *, parse_utc_timestamp: Callable[[str], float | None]) -> bool:
    status = str(job.get("status", "")).strip().lower()
    if status not in {"running", "queued"}:
        return False
    stale_after = max(int(os.environ.get("WORKFLOW_STALE_JOB_SECONDS", "180")), 30)
    updated_at = parse_utc_timestamp(str(job.get("updated_at", "")))
    created_at = parse_utc_timestamp(str(job.get("created_at", "")))
    last_seen = updated_at or created_at
    if last_seen is None:
        return False
    return (time.time() - last_seen) > stale_after


def as_stale_failed_job(job: dict) -> dict:
    out = dict(job)
    out["status"] = "failed"
    out["error"] = str(out.get("error") or "capture worker stale: no completion heartbeat")
    out["stale"] = True
    return out


def latest_phase3_job(
    domain: str,
    run_id: str,
    *,
    load_runs_fn: Callable[[str], dict],
    as_stale_failed_job_fn: Callable[[dict], dict],
    is_stale_running_job_fn: Callable[[dict], bool],
) -> dict | None:
    runs_payload = load_runs_fn(domain)
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
            phase3_jobs.append(as_stale_failed_job_fn(job) if is_stale_running_job_fn(job) else dict(job))
    if not phase3_jobs:
        return None
    phase3_jobs.sort(key=lambda row: (str(row.get("updated_at", "")), str(row.get("created_at", "")), str(row.get("job_id", ""))))
    return phase3_jobs[-1]


def latest_phase6_job(
    domain: str,
    run_id: str,
    *,
    load_runs_fn: Callable[[str], dict],
    as_stale_failed_job_fn: Callable[[dict], dict],
    is_stale_running_job_fn: Callable[[dict], bool],
) -> dict | None:
    runs_payload = load_runs_fn(domain)
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
            phase6_jobs.append(as_stale_failed_job_fn(job) if is_stale_running_job_fn(job) else dict(job))
    if not phase6_jobs:
        return None
    phase6_jobs.sort(key=lambda row: (str(row.get("updated_at", "")), str(row.get("created_at", "")), str(row.get("job_id", ""))))
    return phase6_jobs[-1]
