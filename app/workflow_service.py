from __future__ import annotations

from typing import Any, Callable


def workflow_section_status(*, has_artifact: bool, count: int | None = None, pending_on: bool = False) -> str:
    if has_artifact:
        if count is not None and count == 0:
            return "empty"
        return "ready"
    if pending_on:
        return "not_ready"
    return "not_started"


def workflow_status_payload(
    domain: str,
    run_id: str,
    *,
    read_json_safe: Callable[[str, str, str, Any], Any],
    capture_context_id_from_page: Callable[[str, dict], str],
    load_review_statuses_for_contexts: Callable[[str, list[dict]], dict],
    load_runs: Callable[[str], dict],
    as_stale_failed_job: Callable[[dict], dict],
    is_stale_running_job: Callable[[dict], bool],
    issue_sort_key: Callable[[dict], Any],
    normalize_optional_string: Callable[[object], str | None],
    latest_phase3_job: Callable[[str, str], dict | None],
    workflow_section_status_fn: Callable[..., str],
) -> dict:
    seed_payload = read_json_safe(domain, "manual", "seed_urls.json", {"urls": []})
    seed_urls = seed_payload.get("urls") if isinstance(seed_payload, dict) else []
    seed_count = len([row for row in seed_urls if isinstance(row, dict) and str(row.get("url", "")).strip() and bool(row.get("active", True))])

    pages = read_json_safe(domain, run_id, "page_screenshots.json", None)
    items = read_json_safe(domain, run_id, "collected_items.json", None)
    rules = read_json_safe(domain, run_id, "template_rules.json", None)
    dataset = read_json_safe(domain, run_id, "eligible_dataset.json", None)
    issues = read_json_safe(domain, run_id, "issues.json", None)

    pages_count = len(pages) if isinstance(pages, list) else 0
    items_count = len(items) if isinstance(items, list) else 0
    rules_count = len(rules) if isinstance(rules, list) else 0
    dataset_count = len(dataset) if isinstance(dataset, list) else 0
    issues_count = len(issues) if isinstance(issues, list) else 0

    contexts = [{"capture_context_id": capture_context_id_from_page(domain, row), "language": str(row.get("language", ""))} for row in (pages or []) if isinstance(row, dict)]
    reviews = list(load_review_statuses_for_contexts(domain, contexts).values()) if contexts else []
    reviewed_count = len(reviews)

    run_meta = next((row for row in load_runs(domain).get("runs", []) if str(row.get("run_id", "")) == run_id), None)
    jobs = run_meta.get("jobs", []) if isinstance(run_meta, dict) else []
    effective_jobs = [as_stale_failed_job(j) if is_stale_running_job(j) else j for j in jobs]
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

    annotation_status = workflow_section_status_fn(
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
        first_issue_id = str(sorted([row for row in issues if isinstance(row, dict)], key=issue_sort_key)[0].get("id", ""))

    run_en_standard_display_name = str((run_meta or {}).get("en_standard_display_name", "")).strip()
    eligible_has_artifact = isinstance(dataset, list)
    eligible_status = workflow_section_status_fn(has_artifact=eligible_has_artifact, count=dataset_count, pending_on=isinstance(rules, list))
    phase3_job = latest_phase3_job(domain, run_id)
    phase3_generation_status = str((phase3_job or {}).get("status", "")).strip().lower()
    phase3_generation_error = str((phase3_job or {}).get("error", "")).strip()

    return {
        "state_enum": ["not_started", "in_progress", "ready", "empty", "not_ready", "partial", "failed", "out_of_scope"],
        "seed_urls": {"status": "ready" if seed_count else "empty", "configured": bool(seed_count), "count": seed_count},
        "run": {
            "status": run_status,
            "run_id": run_id,
            "display_name": normalize_optional_string((run_meta or {}).get("display_name")),
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
        "issues": {"status": workflow_section_status_fn(has_artifact=isinstance(issues, list), count=issues_count, pending_on=isinstance(dataset, list)), "count": issues_count, "first_issue_id": first_issue_id},
        "next_recommended_action": next_action,
    }
