import csv
import http.client
import io
import json
import threading
from http import HTTPStatus
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from app.skeleton_server import SkeletonHandler
from pipeline import storage


class _BlobMeta:
    def __init__(self, name: str):
        self.name = name


class _FakeBlob:
    def __init__(self, objects: dict[tuple[str, str], bytes], bucket: str, path: str):
        self._objects = objects
        self._bucket = bucket
        self._path = path

    def upload_from_string(self, content, content_type=None):
        payload = content.encode("utf-8") if isinstance(content, str) else bytes(content)
        self._objects[(self._bucket, self._path)] = payload

    def download_as_text(self, encoding="utf-8"):
        return self._objects[(self._bucket, self._path)].decode(encoding)

    def exists(self, client=None):
        return (self._bucket, self._path) in self._objects


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


def _request(method: str, port: int, path: str, payload: dict | None = None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    headers = {"Content-Type": "application/json"}
    body = json.dumps(payload) if payload is not None else None
    conn.request(method, path, body=body, headers=headers)
    response = conn.getresponse()
    raw = response.read()
    content_type = response.getheader("Content-Type", "")
    conn.close()
    if "application/json" in content_type and raw:
        return response.status, json.loads(raw)
    return response.status, raw.decode("utf-8") if raw else ""


@pytest.fixture
def api_env(monkeypatch):
    objects: dict[tuple[str, str], bytes] = {}
    monkeypatch.setenv("AUTH_MODE", "OFF")
    monkeypatch.setattr(storage, "BUCKET_NAME", "test-bucket")
    monkeypatch.setattr(storage, "validate", lambda *args, **kwargs: None)
    monkeypatch.setattr(storage, "_gcs_client", lambda: _FakeClient(objects))
    monkeypatch.setattr("app.skeleton_server._ReviewConfigStore._client", lambda self: _FakeClient(objects))

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


def test_stage_c_workflow_routes_and_artifact_endpoints(api_env):
    domain = "example.com"
    run_id = "run-c1"
    _write("_system", "manual", "domains.json", {"domains": [domain]})
    _write(domain, "manual", "capture_runs.json", {"runs": [{"run_id": run_id, "created_at": "2026-03-11T00:00:00Z", "jobs": [{"job_id": "j1"}]}]})
    _write(domain, run_id, "page_screenshots.json", [{"page_id": "p1", "url": "https://example.com/a", "language": "fr", "viewport_kind": "desktop", "state": "baseline", "user_tier": "guest", "storage_uri": "gs://shot"}])
    _write(domain, run_id, "collected_items.json", [{"item_id": "i1", "page_id": "p1", "url": "https://example.com/a", "language": "fr", "viewport_kind": "desktop", "state": "baseline", "element_type": "button", "text": "Acheter"}])
    _write(domain, run_id, "issues.json", [{"id": "1", "category": "TRANSLATION_MISMATCH", "severity": "high", "language": "fr", "state": "baseline", "message": "Mismatch", "evidence": {"url": "https://example.com/a", "item_id": "i1"}}])

    status_urls, body_urls = _request("GET", api_env, "/urls")
    assert status_urls == HTTPStatus.OK
    assert '<h1>ADD URL</h1>' in body_urls
    status_runs, body_runs = _request("GET", api_env, "/runs")
    assert status_runs == HTTPStatus.OK
    assert 'selectedRunId' in body_runs
    assert 'selectedOpenContexts' in body_runs
    assert 'selectedOpenPulls' in body_runs
    assert 'selectedOpenIssues' in body_runs
    assert 'selectedExportCsv' in body_runs
    assert _request("GET", api_env, f"/contexts?domain={domain}&run_id={run_id}")[0] == HTTPStatus.OK
    pulls_page_status, pulls_page_body = _request("GET", api_env, f"/pulls?domain={domain}&run_id={run_id}")
    assert pulls_page_status == HTTPStatus.OK
    assert 'id="pullsElementTypeFilter"' in pulls_page_body
    assert '<th>Language</th>' not in pulls_page_body
    workflow_page_status, workflow_page_body = _request("GET", api_env, f"/workflow?domain={domain}&run_id={run_id}")
    assert workflow_page_status == HTTPStatus.OK
    assert 'id="wfExistingRuns"' in workflow_page_body
    assert _request("GET", api_env, f"/?domain={domain}&run_id={run_id}")[0] == HTTPStatus.OK
    status_detail_page, body_detail_page = _request("GET", api_env, f"/issues/detail?domain={domain}&run_id={run_id}&id=1")
    assert status_detail_page == HTTPStatus.OK
    assert 'Issue Detail' in body_detail_page

    assert _request("GET", api_env, f"/api/capture/runs?domain={domain}")[1]["runs"][0]["run_id"] == run_id
    assert _request("GET", api_env, f"/api/capture/contexts?domain={domain}&run_id={run_id}")[1]["contexts"][0]["elements_count"] == 1
    assert _request("GET", api_env, f"/api/pulls?domain={domain}&run_id={run_id}")[1]["rows"][0]["item_id"] == "i1"
    assert _request("GET", api_env, f"/api/issues?domain={domain}&run_id={run_id}")[1]["count"] == 1
    status_detail, payload_detail = _request("GET", api_env, f"/api/issues/detail?domain={domain}&run_id={run_id}&id=1")
    assert status_detail == HTTPStatus.OK
    assert payload_detail["drilldown"]["screenshot_uri"] == "gs://shot"


def test_stage_c_issues_filter_and_csv_export_consistency(api_env):
    domain = "example.com"
    run_id = "run-c2"
    _write(domain, run_id, "issues.json", [
        {"id": "1", "category": "TRANSLATION_MISMATCH", "severity": "high", "language": "fr", "state": "baseline", "message": "m1", "evidence": {"url": "https://example.com/a"}},
        {"id": "2", "category": "FORMATTING_MISMATCH", "severity": "low", "language": "es", "state": "cart", "message": "m2", "evidence": {"url": "https://example.com/b"}},
    ])

    status, payload = _request("GET", api_env, f"/api/issues?domain={domain}&run_id={run_id}&language=fr")
    assert status == HTTPStatus.OK
    assert payload["count"] == 1
    assert payload["issues"][0]["id"] == "1"

    status_csv, csv_raw = _request("GET", api_env, f"/api/issues/export?domain={domain}&run_id={run_id}&language=fr&format=csv")
    assert status_csv == HTTPStatus.OK
    rows = list(csv.DictReader(io.StringIO(csv_raw)))
    assert len(rows) == 1
    assert rows[0]["id"] == "1"


def test_stage_c_issue_detail_partial_evidence_is_usable(api_env):
    domain = "example.com"
    run_id = "run-c3"
    _write(domain, run_id, "issues.json", [{"id": "9", "category": "X", "severity": "medium", "language": "fr", "state": "baseline", "message": "partial", "evidence": {"url": "https://example.com/a", "storage_uri": "gs://only-shot"}}])

    status, payload = _request("GET", api_env, f"/api/issues/detail?domain={domain}&run_id={run_id}&id=9")
    assert status == HTTPStatus.OK
    assert payload["drilldown"]["screenshot_uri"] == "gs://only-shot"
    assert payload["drilldown"]["page"] is None
    assert payload["drilldown"]["element"] is None
    assert payload["drilldown"]["partial"] is True
    assert "collected_items" in payload["drilldown"]["missing_refs"]


def test_stage_c_not_ready_states_for_contexts_and_issues(api_env):
    domain = "example.com"
    run_id = "run-c4"
    status_ctx, payload_ctx = _request("GET", api_env, f"/api/capture/contexts?domain={domain}&run_id={run_id}")
    assert status_ctx == HTTPStatus.NOT_FOUND
    assert payload_ctx == {"status": "not_ready", "error": "page_screenshots artifact missing"}

    status_issues, payload_issues = _request("GET", api_env, f"/api/issues?domain={domain}&run_id={run_id}")
    assert status_issues == HTTPStatus.NOT_FOUND
    assert payload_issues == {"status": "not_ready", "error": "issues artifact missing"}


def test_stage_c_ui_not_ready_and_error_states_have_explicit_render_targets():
    contexts_js = Path("web/static/contexts.js").read_text(encoding="utf-8")
    issues_js = Path("web/static/index.js").read_text(encoding="utf-8")
    detail_js = Path("web/static/issues-detail.js").read_text(encoding="utf-8")
    runs_js = Path("web/static/runs.js").read_text(encoding="utf-8")
    pulls_js = Path("web/static/pulls.js").read_text(encoding="utf-8")
    helper_js = Path("web/static/api-client.js").read_text(encoding="utf-8")

    assert "Not ready: page_screenshots artifact is missing" in contexts_js
    assert "Not ready: issues.json artifact is missing" in issues_js
    assert "async function safeReadPayload" in helper_js
    assert "window.safeReadPayload" in helper_js
    assert "await safeReadPayload(response)" in contexts_js
    assert "await safeReadPayload(response)" in issues_js
    assert "await safeReadPayload(response)" in detail_js
    assert "await safeReadPayload(response)" in runs_js
    assert "await safeReadPayload(response)" in pulls_js
    assert "compute_item_id in pipeline/interactive_capture.py" in pulls_js
    assert "Showing ${rows.length} of ${totalCount} items." in pulls_js
    assert "pullsPreviewImage.naturalWidth" in pulls_js
    assert "Missing screenshot dimensions; cannot scale bbox overlay." in pulls_js
    assert "async function safeReadPayload" not in contexts_js
    assert "async function safeReadPayload" not in issues_js
    assert "async function safeReadPayload" not in detail_js
    assert "async function safeReadPayload" not in runs_js
    assert "async function safeReadPayload" not in pulls_js


def test_stage_c_readme_status_is_not_outdated():
    content = Path("README.md").read_text(encoding="utf-8")
    assert "full visible operator workflow is not fully integrated end-to-end" not in content
    assert "operator workflow pages are now visibly linked via global navigation" in content
