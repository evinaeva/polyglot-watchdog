from __future__ import annotations

import csv
import io

from app.server_utils import _issue_sort_key


def _estimate_severity(issue: dict) -> str:
    explicit = str(issue.get("severity", "")).strip().lower()
    if explicit in {"high", "medium", "low"}:
        return explicit
    confidence = float(issue.get("confidence", 0) or 0)
    if confidence >= 0.9:
        return "high"
    if confidence >= 0.7:
        return "medium"
    return "low"


def _issues_to_csv(issues: list[dict]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "category", "severity", "language", "state", "url", "message"])
    for issue in issues:
        evidence = issue.get("evidence", {}) if isinstance(issue.get("evidence"), dict) else {}
        writer.writerow([
            str(issue.get("id", "")),
            str(issue.get("category", "")),
            _estimate_severity(issue),
            str(issue.get("language", "")),
            str(issue.get("state", "")),
            str(evidence.get("url", "")),
            str(issue.get("message", "")).replace("\n", " "),
        ])
    return output.getvalue()


def _filter_issues(issues: list[dict], query: dict[str, list[str]]) -> list[dict]:
    q = query.get("q", [""])[0].strip().lower()
    issue_type = query.get("type", [""])[0].strip().lower()
    language = query.get("language", [""])[0].strip().lower()
    severity = query.get("severity", [""])[0].strip().lower()
    state = query.get("state", [""])[0].strip().lower()
    url_filter = query.get("url", [""])[0].strip().lower()
    domain_filter = query.get("domain_filter", [""])[0].strip().lower()

    filtered = []
    for issue in issues:
        evidence = issue.get("evidence", {}) if isinstance(issue.get("evidence"), dict) else {}
        issue_url = str(evidence.get("url", ""))
        derived = {
            "language": str(issue.get("language", "")).lower(),
            "severity": _estimate_severity(issue),
            "type": str(issue.get("category", "")).lower(),
            "state": str(issue.get("state", "")).lower(),
            "url": issue_url.lower(),
        }
        if issue_type and derived["type"] != issue_type:
            continue
        if language and derived["language"] != language:
            continue
        if severity and derived["severity"] != severity:
            continue
        if state and derived["state"] != state:
            continue
        if domain_filter and domain_filter not in derived["url"]:
            continue
        if url_filter and url_filter not in derived["url"]:
            continue
        if q and q not in str(issue.get("category", "")).lower() and q not in str(issue.get("message", "")).lower() and q not in derived["url"]:
            continue
        filtered.append(issue)
    return sorted(filtered, key=_issue_sort_key)


def _summarize_issues_payload(issues: list[dict]) -> dict:
    summary = {
        "total": len(issues),
        "by_category": {},
        "by_severity": {},
        "by_language": {},
        "by_state": {},
    }
    for row in issues:
        if not isinstance(row, dict):
            continue
        for key, issue_field in (("by_category", "category"), ("by_language", "language"), ("by_state", "state")):
            value = str(row.get(issue_field, "")).strip() or "unknown"
            summary[key][value] = summary[key].get(value, 0) + 1
        severity = _estimate_severity(row)
        summary["by_severity"][severity] = summary["by_severity"].get(severity, 0) + 1
    return summary


def _format_summary_pairs(summary_map: dict) -> str:
    pairs = [f"{key}: {summary_map[key]}" for key in sorted(summary_map.keys())]
    return ", ".join(pairs) if pairs else "—"
