from app.skeleton_server import _estimate_severity, _filter_issues


def test_issue_filter_logic():
    issues = [
        {"id": "1", "category": "TRANSLATION_MISMATCH", "message": "foo", "confidence": 0.95, "language": "fr", "state": "baseline", "evidence": {"url": "https://a"}},
        {"id": "2", "category": "FORMATTING_MISMATCH", "message": "bar", "confidence": 0.6, "language": "es", "state": "cart", "evidence": {"url": "https://b"}},
    ]
    out = _filter_issues(issues, {"severity": ["high"], "language": ["fr"], "state": ["baseline"], "type": ["translation_mismatch"]})
    assert [i["id"] for i in out] == ["1"]


def test_explicit_severity_takes_precedence_over_confidence():
    issue = {"id": "1", "confidence": 0.95, "severity": "low"}
    assert _estimate_severity(issue) == "low"
