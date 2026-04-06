from app.skeleton_server import _estimate_severity, _filter_issues, _issues_to_csv


def test_issue_filter_logic():
    issues = [
        {"id": "1", "category": "TRANSLATION_MISMATCH", "message": "foo", "confidence": 0.95, "language": "fr", "state": "baseline", "evidence": {"url": "https://a"}},
        {"id": "2", "category": "FORMATTING_MISMATCH", "message": "bar", "confidence": 0.6, "language": "es", "state": "cart", "evidence": {"url": "https://b"}},
    ]
    out = _filter_issues(issues, {"language": ["fr"], "state": ["baseline"], "type": ["translation_mismatch"]})
    assert [i["id"] for i in out] == ["1"]


def test_explicit_severity_takes_precedence_over_confidence():
    issue = {"id": "1", "confidence": 0.95, "severity": "low"}
    assert _estimate_severity(issue) == "low"


def test_issue_filter_domain_substring():
    issues = [{"id": "1", "category": "X", "message": "m", "language": "en", "state": "baseline", "evidence": {"url": "https://shop.example.com/a"}}]
    out = _filter_issues(issues, {"domain_filter": ["shop.example.com"]})
    assert len(out) == 1
    out2 = _filter_issues(issues, {"domain_filter": ["other.example.com"]})
    assert out2 == []


def test_issues_to_csv_handles_quotes_and_commas():
    rows = [{"id": "1", "category": "CAT", "message": "a, b and \"q\"", "language": "fr", "state": "baseline", "evidence": {"url": "https://x"}}]
    csv_text = _issues_to_csv(rows)
    assert "id,category,language,state,url,message" in csv_text
    assert '"a, b and ""q"""' in csv_text
