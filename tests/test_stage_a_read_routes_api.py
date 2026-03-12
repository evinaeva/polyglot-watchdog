import csv
import http.client
import io
import json
import threading
from dataclasses import dataclass
from http import HTTPStatus
from http.server import ThreadingHTTPServer

import pytest

from app.skeleton_server import SkeletonHandler
from pipeline import storage


@dataclass
class _BlobMeta:
    name: str


class _FakeBlob:
    def __init__(self, objects: dict[tuple[str, str], bytes], bucket: str, path: str):
        self._objects = objects
        self._bucket = bucket
        self._path = path

    def upload_from_string(self, content, content_type=None):
        if isinstance(content, str):
            payload = content.encode("utf-8")
        else:
            payload = bytes(content)
        self._objects[(self._bucket, self._path)] = payload

    def download_as_text(self, encoding="utf-8"):
        payload = self._objects[(self._bucket, self._path)]
        return payload.decode(encoding)

    def download_as_bytes(self):
        return self._objects[(self._bucket, self._path)]


class _FakeBucket:
    def __init__(self, objects: dict[tuple[str, str], bytes], name: str):
        self._objects = objects
        self._name = name

    def blob(self, path: str):
        return _FakeBlob(self._objects, self._name, path)

    def list_blobs(self, prefix: str):
        names = sorted(path for (bucket, path) in self._objects if bucket == self._name and path.startswith(prefix))
        return [_BlobMeta(name=n) for n in names]


class _FakeClient:
    def __init__(self, objects: dict[tuple[str, str], bytes]):
        self._objects = objects

    def bucket(self, name: str):
        return _FakeBucket(self._objects, name)


def _request(port: int, path: str):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", path)
    response = conn.getresponse()
    body = response.read()
    headers = dict(response.getheaders())
    conn.close()
    return response.status, headers, body


def _request_with_payload(port: int, method: str, path: str, payload: dict):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    body = json.dumps(payload)
    conn.request(method, path, body=body, headers={"Content-Type": "application/json"})
    response = conn.getresponse()
    raw = response.read()
    headers = dict(response.getheaders())
    conn.close()
    return response.status, headers, raw


@pytest.fixture
def api_env(monkeypatch):
    objects: dict[tuple[str, str], bytes] = {}
    monkeypatch.setenv("AUTH_MODE", "OFF")
    monkeypatch.setattr(storage, "BUCKET_NAME", "test-bucket")
    monkeypatch.setattr(storage, "validate", lambda *args, **kwargs: None)
    monkeypatch.setattr(storage, "_gcs_client", lambda: _FakeClient(objects))

    server = ThreadingHTTPServer(("127.0.0.1", 0), SkeletonHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        thread.join(timeout=2)


def _write(domain: str, run_id: str, filename: str, payload):
    storage.write_json_artifact(domain, run_id, filename, payload)


def test_pulls_happy_path_with_universal_and_decisions(api_env):
    domain = "example.com"
    run_id = "run-1"
    _write(domain, run_id, "collected_items.json", [{"item_id": "i1", "page_id": "p1", "url": "https://a", "state": "baseline", "language": "fr", "viewport_kind": "desktop", "user_tier": "guest", "element_type": "button", "css_selector": "button.buy", "bbox": {"x": 10, "y": 20, "width": 30, "height": 40}, "text": "Acheter", "tag": "button", "attributes": {"class": "buy"}, "visible": True, "not_found": False}])
    _write(domain, run_id, "page_screenshots.json", [{"page_id": "p1", "url": "https://a", "state": "baseline", "language": "fr", "viewport_kind": "desktop", "user_tier": "guest", "screenshot_id": "s1", "storage_uri": "gs://test-bucket/example.com/run-1/screenshots/p1.png", "captured_at": "2026-01-01T00:00:00Z", "viewport": {"width": 1280, "height": 2200}}])
    _write(domain, run_id, "universal_sections.json", [{"section_id": "header", "label": "Header", "representative_url": "https://a"}])
    _write(domain, run_id, "template_rules.json", [{"item_id": "i1", "url": "https://a", "rule_type": "MASK_VARIABLE", "created_at": "t1"}])

    status, _, body = _request(api_env, f"/api/pulls?domain={domain}&run_id={run_id}")
    payload = json.loads(body)

    assert status == HTTPStatus.OK
    assert payload["missing_universal_sections"] is False
    assert [r["item_id"] for r in payload["rows"]] == ["i1", "universal-header"]
    row = payload["rows"][0]
    assert row["decision"] == "MASK_VARIABLE"
    assert row["user_tier"] == "guest"
    assert row["page_id"] == "p1"
    assert row["bbox"] == {"x": 10, "y": 20, "width": 30, "height": 40}
    assert row["page_viewport"] == {"width": 1280, "height": 2200}
    assert row["screenshot_storage_uri"] == "gs://test-bucket/example.com/run-1/screenshots/p1.png"
    assert row["screenshot_view_url"] == "/api/page-screenshot?domain=example.com&run_id=run-1&page_id=p1"
    universal = payload["rows"][1]
    assert universal == {
        "item_id": "universal-header",
        "capture_context_id": "",
        "url": "https://a",
        "state": "universal",
        "language": "en",
        "viewport_kind": "any",
        "user_tier": None,
        "element_type": "universal_section",
        "text": "Header",
        "not_found": False,
        "decision": "",
    }


def test_pulls_not_ready_and_filters(api_env):
    domain = "example.com"
    run_id = "run-2"
    status, _, body = _request(api_env, f"/api/pulls?domain={domain}&run_id={run_id}")
    assert status == HTTPStatus.NOT_FOUND
    assert json.loads(body) == {"error": "collected_items artifact missing", "status": "not_ready"}

    _write(domain, run_id, "collected_items.json", [
        {"item_id": "i1", "page_id": "p1", "url": "https://a/path", "state": "baseline", "language": "fr", "viewport_kind": "desktop", "user_tier": "guest", "element_type": "button", "css_selector": "button", "bbox": {"x": 0, "y": 0, "width": 1, "height": 1}, "text": "x", "visible": True},
        {"item_id": "i2", "page_id": "p2", "url": "https://b/path", "state": "logged_in", "language": "de", "viewport_kind": "mobile", "user_tier": "pro", "element_type": "link", "css_selector": "a", "bbox": {"x": 0, "y": 0, "width": 1, "height": 1}, "text": "y", "visible": True},
        {"item_id": "i3", "page_id": "p3", "url": "https://c/path", "state": "baseline", "language": "fr", "viewport_kind": "desktop", "user_tier": "guest", "element_type": "script", "css_selector": "script", "bbox": {"x": 0, "y": 0, "width": 1, "height": 1}, "text": "var x=1", "visible": True},
    ])
    _write(domain, run_id, "page_screenshots.json", [
        {"page_id": "p1", "url": "https://a/path", "state": "baseline", "language": "fr", "viewport_kind": "desktop", "user_tier": "guest", "screenshot_id": "s1", "storage_uri": "gs://test-bucket/example.com/run-2/screenshots/p1.png", "captured_at": "2026-01-01T00:00:00Z", "viewport": {"width": 100, "height": 100}},
        {"page_id": "p2", "url": "https://b/path", "state": "logged_in", "language": "de", "viewport_kind": "mobile", "user_tier": "pro", "screenshot_id": "s2", "storage_uri": "gs://test-bucket/example.com/run-2/screenshots/p2.png", "captured_at": "2026-01-01T00:00:00Z", "viewport": {"width": 100, "height": 100}},
        {"page_id": "p3", "url": "https://c/path", "state": "baseline", "language": "fr", "viewport_kind": "desktop", "user_tier": "guest", "screenshot_id": "s3", "storage_uri": "gs://test-bucket/example.com/run-2/screenshots/p3.png", "captured_at": "2026-01-01T00:00:00Z", "viewport": {"width": 100, "height": 100}},
    ])
    _write(domain, run_id, "template_rules.json", [])

    status2, _, body2 = _request(api_env, f"/api/pulls?domain={domain}&run_id={run_id}&url=a/path&state=baseline&language=fr&viewport_kind=desktop&user_tier=guest")
    payload2 = json.loads(body2)
    assert status2 == HTTPStatus.OK
    assert payload2["missing_universal_sections"] is True
    assert [r["item_id"] for r in payload2["rows"]] == ["i1"]

    status3, _, body3 = _request(api_env, f"/api/pulls?domain={domain}&run_id={run_id}")
    payload3 = json.loads(body3)
    assert status3 == HTTPStatus.OK
    assert [r["item_id"] for r in payload3["rows"]] == ["i1", "i2"]


def test_page_screenshot_proxy_reads_png(api_env):
    domain = "example.com"
    run_id = "run-shot"
    _write(domain, run_id, "page_screenshots.json", [
        {"page_id": "p1", "url": "https://a/path", "state": "baseline", "language": "fr", "viewport_kind": "desktop", "user_tier": "guest", "screenshot_id": "s1", "storage_uri": "gs://test-bucket/example.com/run-shot/screenshots/p1.png", "captured_at": "2026-01-01T00:00:00Z", "viewport": {"width": 100, "height": 100}},
    ])
    client = storage._gcs_client()
    blob = client.bucket("test-bucket").blob("example.com/run-shot/screenshots/p1.png")
    blob.upload_from_string(b"\x89PNG\r\n\x1a\n", content_type="image/png")

    status, headers, body = _request(api_env, f"/api/page-screenshot?domain={domain}&run_id={run_id}&page_id=p1")
    assert status == HTTPStatus.OK
    assert headers["Content-Type"] == "image/png"
    assert body == b"\x89PNG\r\n\x1a\n"


def test_page_screenshot_redirects_http_storage_uri(api_env):
    domain = "example.com"
    run_id = "run-shot-http"
    uri = "https://cdn.example.com/screenshots/p1.png"
    _write(domain, run_id, "page_screenshots.json", [
        {"page_id": "p1", "url": "https://a/path", "state": "baseline", "language": "fr", "viewport_kind": "desktop", "user_tier": "guest", "screenshot_id": "s1", "storage_uri": uri, "captured_at": "2026-01-01T00:00:00Z", "viewport": {"width": 100, "height": 100}},
    ])

    status, headers, body = _request(api_env, f"/api/page-screenshot?domain={domain}&run_id={run_id}&page_id=p1")
    assert status == HTTPStatus.FOUND
    assert headers["Location"] == uri
    assert body == b""


def test_page_screenshot_missing_blob_returns_not_ready(api_env):
    domain = "example.com"
    run_id = "run-shot-missing"
    _write(domain, run_id, "page_screenshots.json", [
        {"page_id": "p1", "url": "https://a/path", "state": "baseline", "language": "fr", "viewport_kind": "desktop", "user_tier": "guest", "screenshot_id": "s1", "storage_uri": "gs://test-bucket/example.com/run-shot-missing/screenshots/p1.png", "captured_at": "2026-01-01T00:00:00Z", "viewport": {"width": 100, "height": 100}},
    ])

    status, _, body = _request(api_env, f"/api/page-screenshot?domain={domain}&run_id={run_id}&page_id=p1")
    assert status == HTTPStatus.SERVICE_UNAVAILABLE
    assert json.loads(body) == {"error": "page_screenshot_unavailable", "status": "not_ready"}


def test_rules_missing_required_and_fail_closed_on_corruption(api_env):
    status, _, body = _request(api_env, "/api/rules?domain=example.com")
    assert status == HTTPStatus.BAD_REQUEST
    assert json.loads(body) == {"error": "missing_required_query_params", "missing": ["run_id"]}

    _write("example.com", "r-ok", "template_rules.json", [])
    status2, _, body2 = _request(api_env, "/api/rules?domain=example.com&run_id=r-ok")
    assert status2 == HTTPStatus.OK
    assert json.loads(body2) == {"rules": []}

    from pipeline.storage import _gcs_client, artifact_path

    blob = _gcs_client().bucket(storage.BUCKET_NAME).blob(artifact_path("example.com", "r-bad", "template_rules.json"))
    blob.upload_from_string('{"bad":"shape"}')

    status3, _, body3 = _request(api_env, "/api/rules?domain=example.com&run_id=r-bad")
    payload3 = json.loads(body3)
    assert status3 == HTTPStatus.INTERNAL_SERVER_ERROR
    assert payload3 == {"error": "template_rules.json artifact_invalid", "status": "artifact_invalid"}




def test_rules_fail_closed_on_malformed_row_entries(api_env):
    domain = "example.com"
    _write(domain, "r-bad-row", "template_rules.json", [{"item_id": "i1", "url": "https://a"}])
    status, _, body = _request(api_env, f"/api/rules?domain={domain}&run_id=r-bad-row")
    assert status == HTTPStatus.INTERNAL_SERVER_ERROR
    assert json.loads(body) == {"error": "template_rules.json artifact_invalid", "status": "artifact_invalid"}

    _write(domain, "r-bad-type", "template_rules.json", ["bad-row"])
    status2, _, body2 = _request(api_env, f"/api/rules?domain={domain}&run_id=r-bad-type")
    assert status2 == HTTPStatus.INTERNAL_SERVER_ERROR
    assert json.loads(body2) == {"error": "template_rules.json artifact_invalid", "status": "artifact_invalid"}

def test_issues_filters_json_csv_and_contract(api_env):
    domain = "example.com"
    run_id = "run-issues"
    _write(domain, run_id, "issues.json", [
        {"id": "2", "category": "layout", "language": "de", "state": "logged_in", "message": "line\nbreak", "evidence": {"url": "https://shop.example.com/b"}, "severity": "low"},
        {"id": "1", "category": "translation_mismatch", "language": "fr", "state": "baseline", "message": "bonjour", "evidence": {"url": "https://shop.example.com/a"}, "severity": "high"},
    ])

    status, _, body = _request(api_env, f"/api/issues?domain={domain}&run_id={run_id}&language=fr&type=translation_mismatch&state=baseline&url=/a&domain_filter=shop.example.com&q=bonjour")
    payload = json.loads(body)
    assert status == HTTPStatus.OK
    assert payload["count"] == 1
    assert [i["id"] for i in payload["issues"]] == ["1"]

    status_csv, headers_csv, csv_body = _request(api_env, f"/api/issues/export?domain={domain}&run_id={run_id}&language=fr&type=translation_mismatch&state=baseline&url=/a&domain_filter=shop.example.com&q=bonjour&format=csv")
    assert status_csv == HTTPStatus.OK
    assert headers_csv["Content-Type"] == "text/csv; charset=utf-8"
    csv_text = csv_body.decode("utf-8")
    reader = list(csv.reader(io.StringIO(csv_text)))
    assert reader[0] == ["id", "category", "severity", "language", "state", "url", "message"]
    assert reader[1] == ["1", "translation_mismatch", "high", "fr", "baseline", "https://shop.example.com/a", "bonjour"]
    assert len(reader) == 2

    status_csv_all, _, csv_body_all = _request(api_env, f"/api/issues/export?domain={domain}&run_id={run_id}&format=csv")
    all_rows = list(csv.reader(io.StringIO(csv_body_all.decode("utf-8"))))
    assert all_rows[2][0] == "2"
    assert all_rows[2][6] == "line break"




def test_issues_filter_semantics_by_field(api_env):
    domain = "example.com"
    run_id = "run-filter-semantics"
    _write(domain, run_id, "issues.json", [
        {"id": "10", "category": "translation_mismatch", "language": "fr", "state": "baseline", "message": "alpha", "evidence": {"url": "https://shop.example.com/path-a"}, "severity": "high"},
        {"id": "20", "category": "layout", "language": "de", "state": "logged_in", "message": "beta", "evidence": {"url": "https://other.example.com/path-b"}, "severity": "low"},
    ])

    checks = [
        ("type=translation_mismatch", ["10"]),
        ("language=fr", ["10"]),
        ("severity=high", ["10"]),
        ("state=baseline", ["10"]),
        ("url=path-a", ["10"]),
        ("domain_filter=shop.example.com", ["10"]),
        ("q=alpha", ["10"]),
    ]
    for query, expected_ids in checks:
        status, _, body = _request(api_env, f"/api/issues?domain={domain}&run_id={run_id}&{query}")
        payload = json.loads(body)
        assert status == HTTPStatus.OK
        assert [item["id"] for item in payload["issues"]] == expected_ids

    status_all, _, body_all = _request(api_env, f"/api/issues?domain={domain}&run_id={run_id}")
    payload_all = json.loads(body_all)
    assert status_all == HTTPStatus.OK
    assert [item["id"] for item in payload_all["issues"]] == ["10", "20"]



def test_issues_numeric_like_ids_sort_numerically(api_env):
    domain = "example.com"
    run_id = "run-numeric-sort"
    _write(domain, run_id, "issues.json", [
        {"id": "10", "category": "layout", "language": "fr", "state": "baseline", "message": "b", "evidence": {"url": "https://a"}},
        {"id": "2", "category": "layout", "language": "fr", "state": "baseline", "message": "a", "evidence": {"url": "https://a"}},
    ])
    status, _, body = _request(api_env, f"/api/issues?domain={domain}&run_id={run_id}")
    assert status == HTTPStatus.OK
    assert [issue["id"] for issue in json.loads(body)["issues"]] == ["2", "10"]

def test_issues_not_ready_and_corruption(api_env):
    domain = "example.com"
    run_id = "run-missing"
    status, _, body = _request(api_env, f"/api/issues?domain={domain}&run_id={run_id}")
    assert status == HTTPStatus.NOT_FOUND
    assert json.loads(body) == {"error": "issues artifact missing", "status": "not_ready"}

    from pipeline.storage import _gcs_client, artifact_path

    blob = _gcs_client().bucket(storage.BUCKET_NAME).blob(artifact_path(domain, "run-bad", "issues.json"))
    blob.upload_from_string('{"bad":"shape"}')
    status2, _, body2 = _request(api_env, f"/api/issues?domain={domain}&run_id=run-bad")
    assert status2 == HTTPStatus.INTERNAL_SERVER_ERROR
    assert json.loads(body2) == {"error": "issues.json artifact_invalid", "status": "artifact_invalid"}






def test_required_artifact_listing_failure_returns_500(api_env, monkeypatch):
    domain = "example.com"
    run_id = "run-list-fail"
    _write(domain, run_id, "collected_items.json", [])
    _write(domain, run_id, "issues.json", [])
    _write(domain, run_id, "page_screenshots.json", [])

    def fail_list(*args, **kwargs):
        raise RuntimeError("listing down")

    monkeypatch.setattr(storage, "list_run_artifacts", fail_list)

    status_pulls, _, body_pulls = _request(api_env, f"/api/pulls?domain={domain}&run_id={run_id}")
    assert status_pulls == HTTPStatus.INTERNAL_SERVER_ERROR
    assert json.loads(body_pulls) == {"error": "collected_items.json artifact_read_failed", "status": "artifact_invalid"}

    status_issues, _, body_issues = _request(api_env, f"/api/issues?domain={domain}&run_id={run_id}")
    assert status_issues == HTTPStatus.INTERNAL_SERVER_ERROR
    assert json.loads(body_issues) == {"error": "issues.json artifact_read_failed", "status": "artifact_invalid"}

    status_contexts, _, body_contexts = _request(api_env, f"/api/capture-contexts?domain={domain}&run_id={run_id}")
    assert status_contexts == HTTPStatus.INTERNAL_SERVER_ERROR
    assert json.loads(body_contexts) == {"error": "page_screenshots.json artifact_read_failed", "status": "artifact_invalid"}


def test_issue_detail_optional_listing_failure_returns_500(api_env, monkeypatch):
    domain = "example.com"
    run_id = "run-detail-list-fail"
    _write(domain, run_id, "issues.json", [{"id": "x", "evidence": {"item_id": "i1", "storage_uri": "gs://f"}}])

    original_list = storage.list_run_artifacts
    call_count = {"n": 0}

    def flaky_list(d, r):
        if d == domain and r == run_id:
            call_count["n"] += 1
            if call_count["n"] >= 2:
                raise RuntimeError("listing down")
        return original_list(d, r)

    monkeypatch.setattr(storage, "list_run_artifacts", flaky_list)

    status, _, body = _request(api_env, f"/api/issues/detail?domain={domain}&run_id={run_id}&id=x")
    assert status == HTTPStatus.INTERNAL_SERVER_ERROR
    assert json.loads(body) == {"error": "page_screenshots.json artifact_read_failed", "status": "artifact_invalid"}

def test_required_artifact_read_failure_returns_500(api_env, monkeypatch):
    domain = "example.com"
    run_id = "run-read-fail"
    _write(domain, run_id, "issues.json", [{"id": "1", "category": "x", "evidence": {"url": "https://a"}}])

    original = storage.read_json_artifact

    def flaky_read(d, r, filename):
        if d == domain and r == run_id and filename == "issues.json":
            raise OSError("simulated read failure")
        return original(d, r, filename)

    monkeypatch.setattr(storage, "read_json_artifact", flaky_read)
    status, _, body = _request(api_env, f"/api/issues?domain={domain}&run_id={run_id}")
    assert status == HTTPStatus.INTERNAL_SERVER_ERROR
    assert json.loads(body) == {"error": "issues.json artifact_read_failed", "status": "artifact_invalid"}

def test_issue_detail_full_partial_and_optional_artifact_corruption(api_env):
    domain = "example.com"
    _write(domain, "run-full", "issues.json", [{"id": "ok", "evidence": {"item_id": "i1", "storage_uri": "gs://fallback", "url": "https://a"}}])
    _write(domain, "run-full", "collected_items.json", [{"item_id": "i1", "page_id": "p1"}])
    _write(domain, "run-full", "page_screenshots.json", [{"page_id": "p1", "storage_uri": "gs://page-shot"}])

    status_ok, _, body_ok = _request(api_env, f"/api/issues/detail?domain={domain}&run_id=run-full&id=ok")
    payload_ok = json.loads(body_ok)
    assert status_ok == HTTPStatus.OK
    assert payload_ok["drilldown"]["element"] is not None
    assert payload_ok["drilldown"]["page"] is not None
    assert payload_ok["drilldown"]["screenshot_uri"] == "gs://page-shot"

    _write(domain, "run-partial", "issues.json", [{"id": "partial", "evidence": {"storage_uri": "gs://only-evidence", "url": "https://b"}}])
    status_partial, _, body_partial = _request(api_env, f"/api/issues/detail?domain={domain}&run_id=run-partial&id=partial")
    payload_partial = json.loads(body_partial)
    assert status_partial == HTTPStatus.OK
    assert payload_partial["drilldown"]["element"] is None
    assert payload_partial["drilldown"]["page"] is None
    assert payload_partial["drilldown"]["screenshot_uri"] == "gs://only-evidence"

    from pipeline.storage import _gcs_client, artifact_path

    _write(domain, "run-bad-page", "issues.json", [{"id": "x", "evidence": {"item_id": "i1", "storage_uri": "gs://x"}}])
    _write(domain, "run-bad-page", "collected_items.json", [{"item_id": "i1", "page_id": "p1"}])
    _gcs_client().bucket(storage.BUCKET_NAME).blob(artifact_path(domain, "run-bad-page", "page_screenshots.json")).upload_from_string('{"bad":1}')
    status_bad, _, body_bad = _request(api_env, f"/api/issues/detail?domain={domain}&run_id=run-bad-page&id=x")
    assert status_bad == HTTPStatus.INTERNAL_SERVER_ERROR
    assert json.loads(body_bad) == {"error": "page_screenshots.json artifact_invalid", "status": "artifact_invalid"}




def test_issue_detail_not_ready_when_issues_missing(api_env):
    status, _, body = _request(api_env, "/api/issues/detail?domain=example.com&run_id=run-missing-detail&id=abc")
    assert status == HTTPStatus.NOT_FOUND
    assert json.loads(body) == {"error": "issues artifact missing", "status": "not_ready"}

def test_issue_detail_not_found_and_required_param(api_env):
    _write("example.com", "run-404", "issues.json", [])
    status, _, _ = _request(api_env, "/api/issues/detail?domain=example.com&run_id=run-404&id=missing")
    assert status == HTTPStatus.NOT_FOUND
    status2, _, body2 = _request(api_env, "/api/issues/detail?domain=example.com&run_id=run-404")
    assert status2 == HTTPStatus.BAD_REQUEST
    assert json.loads(body2) == {"error": "missing_required_query_params", "missing": ["id"]}




def test_capture_contexts_deterministic_ordering(api_env):
    domain = "example.com"
    run_id = "run-capture-order"
    _write(domain, run_id, "page_screenshots.json", [
        {"page_id": "p2", "url": "https://b", "viewport_kind": "desktop", "state": "baseline", "language": "fr", "storage_uri": "gs://p2"},
        {"page_id": "p1", "url": "https://a", "viewport_kind": "desktop", "state": "baseline", "language": "fr", "storage_uri": "gs://p1"},
    ])
    status, _, body = _request(api_env, f"/api/capture-contexts?domain={domain}&run_id={run_id}")
    assert status == HTTPStatus.OK
    contexts = json.loads(body)["contexts"]
    ordered = sorted(contexts, key=lambda row: (row["capture_context_id"], row["page_id"], row["url"]))
    assert contexts == ordered

def test_capture_contexts_artifact_backed_and_corruption(api_env):
    domain = "example.com"
    run_id = "run-capture"
    _write(domain, run_id, "page_screenshots.json", [{"page_id": "p1", "url": "https://a", "viewport_kind": "desktop", "state": "baseline", "language": "fr", "user_tier": "None", "storage_uri": "gs://p1"}])
    _write(domain, run_id, "collected_items.json", [{"item_id": "i1", "page_id": "p1"}, {"item_id": "i2", "page_id": "p1"}])

    status, _, body = _request(api_env, f"/api/capture-contexts?domain={domain}&run_id={run_id}")
    payload = json.loads(body)
    assert status == HTTPStatus.OK
    assert payload["contexts"][0]["elements_count"] == 2
    assert payload["contexts"][0]["user_tier"] is None

    status2, _, body2 = _request(api_env, f"/api/capture-contexts?domain={domain}&run_id=missing")
    assert status2 == HTTPStatus.NOT_FOUND
    assert json.loads(body2) == {"error": "page_screenshots artifact missing", "status": "not_ready"}

    from pipeline.storage import _gcs_client, artifact_path

    _gcs_client().bucket(storage.BUCKET_NAME).blob(artifact_path(domain, "run-bad", "page_screenshots.json")).upload_from_string('{"bad":1}')
    status3, _, body3 = _request(api_env, f"/api/capture-contexts?domain={domain}&run_id=run-bad")
    assert status3 == HTTPStatus.INTERNAL_SERVER_ERROR
    assert json.loads(body3) == {"error": "page_screenshots.json artifact_invalid", "status": "artifact_invalid"}


def test_element_signature_whitelist_specific_domain_scoped_and_removable(api_env):
    domain = "example.com"
    run_a = "run-whitelist-a"
    run_b = "run-whitelist-b"
    _write(domain, run_a, "collected_items.json", [
        {"item_id": "i1", "page_id": "p1", "url": "https://example.com/a", "state": "baseline", "language": "fr", "viewport_kind": "desktop", "user_tier": "guest", "element_type": "a", "css_selector": "header .cta", "bbox": {"x": 0, "y": 0, "width": 1, "height": 1}, "text": "Acheter", "attributes": {"class": "cta primary", "href": "/buy"}, "visible": True},
        {"item_id": "i2", "page_id": "p2", "url": "https://example.com/a", "state": "baseline", "language": "fr", "viewport_kind": "desktop", "user_tier": "guest", "element_type": "link", "css_selector": "a", "bbox": {"x": 0, "y": 0, "width": 1, "height": 1}, "text": "Voir", "visible": True},
        {"item_id": "i4", "page_id": "p2", "url": "https://example.com/a", "state": "baseline", "language": "fr", "viewport_kind": "desktop", "user_tier": "guest", "element_type": "a", "css_selector": "footer a", "bbox": {"x": 0, "y": 0, "width": 1, "height": 1}, "text": "Contact", "attributes": {"class": "footer-link", "href": "/contact"}, "visible": True},
    ])
    _write(domain, run_a, "page_screenshots.json", [
        {"page_id": "p1", "url": "https://example.com/a", "state": "baseline", "language": "fr", "viewport_kind": "desktop", "user_tier": "guest", "screenshot_id": "s1", "storage_uri": "gs://test-bucket/example.com/run-whitelist-a/screenshots/p1.png", "captured_at": "2026-01-01T00:00:00Z", "viewport": {"width": 100, "height": 100}},
        {"page_id": "p2", "url": "https://example.com/a", "state": "baseline", "language": "fr", "viewport_kind": "desktop", "user_tier": "guest", "screenshot_id": "s2", "storage_uri": "gs://test-bucket/example.com/run-whitelist-a/screenshots/p2.png", "captured_at": "2026-01-01T00:00:00Z", "viewport": {"width": 100, "height": 100}},
    ])
    _write(domain, run_a, "template_rules.json", [])

    _write(domain, run_b, "collected_items.json", [
        {"item_id": "i3", "page_id": "p3", "url": "https://example.com/b", "state": "baseline", "language": "de", "viewport_kind": "mobile", "user_tier": "pro", "element_type": "a", "css_selector": "header .cta", "bbox": {"x": 0, "y": 0, "width": 1, "height": 1}, "text": "Kaufen", "attributes": {"class": "primary cta", "href": "/kaufen", "aria-label": "Jetzt kaufen"}, "visible": True}
    ])
    _write(domain, run_b, "page_screenshots.json", [
        {"page_id": "p3", "url": "https://example.com/b", "state": "baseline", "language": "de", "viewport_kind": "mobile", "user_tier": "pro", "screenshot_id": "s3", "storage_uri": "gs://test-bucket/example.com/run-whitelist-b/screenshots/p3.png", "captured_at": "2026-01-01T00:00:00Z", "viewport": {"width": 100, "height": 100}},
    ])
    _write(domain, run_b, "template_rules.json", [])

    status_add, _, body_add = _request_with_payload(api_env, "POST", "/api/element-type-whitelist", {
        "domain": domain,
        "element_type": "a",
        "css_selector": "header .cta",
        "attributes": {"class": "cta primary", "href": "/buy"},
    })
    assert status_add == HTTPStatus.OK
    entries = json.loads(body_add)["entries"]
    assert len(entries) == 1
    signature_key = entries[0]["signature_key"]
    assert entries[0]["description"].startswith("a")
    assert json.loads(body_add)["added_entry"]["signature_key"] == signature_key

    status_wl, _, body_wl = _request(api_env, f"/api/element-type-whitelist?domain={domain}")
    assert status_wl == HTTPStatus.OK
    assert len(json.loads(body_wl)["entries"]) == 1

    status_a, _, body_a = _request(api_env, f"/api/pulls?domain={domain}&run_id={run_a}")
    payload_a = json.loads(body_a)
    assert status_a == HTTPStatus.OK
    assert [row["item_id"] for row in payload_a["rows"]] == ["i2", "i4"]

    status_b, _, body_b = _request(api_env, f"/api/pulls?domain={domain}&run_id={run_b}")
    payload_b = json.loads(body_b)
    assert status_b == HTTPStatus.OK
    assert payload_b["rows"] == []

    status_remove, _, body_remove = _request_with_payload(api_env, "POST", "/api/element-type-whitelist/remove", {"domain": domain, "signature_key": signature_key})
    assert status_remove == HTTPStatus.OK
    assert json.loads(body_remove)["entries"] == []

    status_a2, _, body_a2 = _request(api_env, f"/api/pulls?domain={domain}&run_id={run_a}")
    payload_a2 = json.loads(body_a2)
    assert status_a2 == HTTPStatus.OK
    assert [row["item_id"] for row in payload_a2["rows"]] == ["i1", "i2", "i4"]

    status_b2, _, body_b2 = _request(api_env, f"/api/pulls?domain={domain}&run_id={run_b}")
    payload_b2 = json.loads(body_b2)
    assert status_b2 == HTTPStatus.OK
    assert [row["item_id"] for row in payload_b2["rows"]] == ["i3"]


def test_legacy_tag_only_whitelist_artifact_does_not_hide_rows(api_env):
    domain = "example.com"
    run_id = "run-legacy-whitelist"
    _write(domain, run_id, "collected_items.json", [
        {"item_id": "i1", "page_id": "p1", "url": "https://example.com/a", "state": "baseline", "language": "fr", "viewport_kind": "desktop", "user_tier": "guest", "element_type": "a", "css_selector": "header a", "bbox": {"x": 0, "y": 0, "width": 1, "height": 1}, "text": "Header", "attributes": {"class": "header-link"}, "visible": True},
        {"item_id": "i2", "page_id": "p2", "url": "https://example.com/a", "state": "baseline", "language": "fr", "viewport_kind": "desktop", "user_tier": "guest", "element_type": "a", "css_selector": "footer a", "bbox": {"x": 0, "y": 0, "width": 1, "height": 1}, "text": "Footer", "attributes": {"class": "footer-link"}, "visible": True},
    ])
    _write(domain, run_id, "page_screenshots.json", [
        {"page_id": "p1", "url": "https://example.com/a", "state": "baseline", "language": "fr", "viewport_kind": "desktop", "user_tier": "guest", "screenshot_id": "s1", "storage_uri": "gs://test-bucket/example.com/run-legacy-whitelist/screenshots/p1.png", "captured_at": "2026-01-01T00:00:00Z", "viewport": {"width": 100, "height": 100}},
        {"page_id": "p2", "url": "https://example.com/a", "state": "baseline", "language": "fr", "viewport_kind": "desktop", "user_tier": "guest", "screenshot_id": "s2", "storage_uri": "gs://test-bucket/example.com/run-legacy-whitelist/screenshots/p2.png", "captured_at": "2026-01-01T00:00:00Z", "viewport": {"width": 100, "height": 100}},
    ])
    _write(domain, run_id, "template_rules.json", [])
    _write(domain, "_shared", "element_type_whitelist.json", ["a"])

    status, _, body = _request(api_env, f"/api/pulls?domain={domain}&run_id={run_id}")
    payload = json.loads(body)
    assert status == HTTPStatus.OK
    assert [row["item_id"] for row in payload["rows"]] == ["i1", "i2"]


def test_element_signature_requires_more_than_single_generic_class(api_env):
    domain = "example.com"
    status_add, _, body_add = _request_with_payload(api_env, "POST", "/api/element-type-whitelist", {
        "domain": domain,
        "element_type": "a",
        "attributes": {"class": "link", "href": "/localized"},
    })
    payload = json.loads(body_add)
    assert status_add == HTTPStatus.BAD_REQUEST
    assert payload["error"] == "element_signature_requires_specific_attributes"
    assert payload["status"] == "invalid_request"
