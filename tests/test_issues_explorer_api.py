from app.skeleton_server import _filter_issues, _issues_to_csv
from app.issues_utils import _summarize_issues_payload


def test_issue_filter_logic():
    issues = [
        {"id": "1", "category": "TRANSLATION_MISMATCH", "message": "foo", "confidence": 0.95, "language": "fr", "state": "baseline", "evidence": {"url": "https://a"}},
        {"id": "2", "category": "FORMATTING_MISMATCH", "message": "bar", "confidence": 0.6, "language": "es", "state": "cart", "evidence": {"url": "https://b"}},
    ]
    out = _filter_issues(issues, {"language": ["fr"], "state": ["baseline"], "type": ["translation_mismatch"]})
    assert [i["id"] for i in out] == ["1"]


def test_issue_filter_domain_substring():
    issues = [{"id": "1", "category": "X", "message": "m", "language": "en", "state": "baseline", "evidence": {"url": "https://shop.example.com/a"}}]
    out = _filter_issues(issues, {"domain_filter": ["shop.example.com"]})
    assert len(out) == 1
    out2 = _filter_issues(issues, {"domain_filter": ["other.example.com"]})
    assert out2 == []


def test_issues_to_csv_handles_quotes_and_commas():
    rows = [{"id": "1", "category": "CAT", "message": "a, b and \"q\"", "language": "fr", "state": "baseline", "evidence": {"url": "https://x"}}]
    csv_text = _issues_to_csv(rows)
    assert csv_text.splitlines()[0] == "id,category,language,state,url,message"
    assert '"a, b and ""q"""' in csv_text


def test_summarize_payload_does_not_include_by_severity():
    issues = [
        {"id": "1", "category": "TRANSLATION_MISMATCH", "language": "fr", "state": "baseline", "evidence": {"url": "https://a"}},
        {"id": "2", "category": "FORMATTING_MISMATCH", "language": "es", "state": "cart", "evidence": {"url": "https://b"}},
    ]

    summary = _summarize_issues_payload(issues)

    assert "by_severity" not in summary
