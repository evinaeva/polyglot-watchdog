from __future__ import annotations

from urllib.parse import parse_qs

from app.artifact_helpers import _not_ready_payload
from app.issues_utils import _filter_issues, _issues_to_csv
from app.repositories import artifacts_repo


def load_issues(domain: str, run_id: str) -> list[dict]:
    artifacts_repo.require_artifact_exists(domain, run_id, "issues.json")
    return artifacts_repo.read_list_required(domain, run_id, "issues.json")


def get_issues(domain: str, run_id: str, query: dict[str, list[str]], issue_sort_key) -> dict:
    issues = load_issues(domain, run_id)
    filtered = _filter_issues(issues, query)
    filtered.sort(key=issue_sort_key)
    return {"issues": filtered, "count": len(filtered)}


def issues_csv(domain: str, run_id: str, query: dict[str, list[str]], issue_sort_key) -> bytes:
    payload = get_issues(domain, run_id, query, issue_sort_key)
    return _issues_to_csv(payload["issues"]).encode("utf-8")
