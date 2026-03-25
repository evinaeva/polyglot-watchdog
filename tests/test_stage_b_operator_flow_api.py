import http.client
import json
import threading
from http import HTTPStatus
from http.server import ThreadingHTTPServer

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
    conn.close()
    return response.status, (json.loads(raw) if raw else {})


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


def test_review_persisted_and_joined_in_contexts(api_env):
    domain = "example.com"
    run_id = "run-b"
    _write(domain, run_id, "page_screenshots.json", [{"page_id": "p1", "url": "https://a", "language": "en", "viewport_kind": "desktop", "state": "baseline", "user_tier": None, "storage_uri": "gs://x"}])

    status_get, payload_get = _request("GET", api_env, f"/api/capture/contexts?domain={domain}&run_id={run_id}")
    assert status_get == HTTPStatus.OK
    assert payload_get["contexts"][0]["screenshot_view_url"] == f"/api/page-screenshot?domain={domain}&run_id={run_id}&page_id=p1"
    capture_context_id = payload_get["contexts"][0]["capture_context_id"]

    status_post, payload_post = _request("POST", api_env, "/api/capture/reviews", {
        "domain": domain,
        "run_id": run_id,
        "capture_context_id": capture_context_id,
        "language": "en",
        "status": "blocked_by_overlay",
        "reviewer": "operator",
        "timestamp": "2026-03-10T12:00:00Z",
    })
    assert status_post == HTTPStatus.OK
    assert payload_post["record"]["status"] == "blocked_by_overlay"

    status_get2, payload_get2 = _request("GET", api_env, f"/api/capture/contexts?domain={domain}&run_id={run_id}")
    assert status_get2 == HTTPStatus.OK
    assert payload_get2["contexts"][0]["review_status"]["status"] == "blocked_by_overlay"


def test_review_last_write_wins_for_same_context_and_language(api_env):
    domain = "example.com"
    run_id = "run-b-lww"
    _write(domain, run_id, "page_screenshots.json", [{"page_id": "p1", "url": "https://a", "language": "en", "viewport_kind": "desktop", "state": "baseline", "user_tier": None, "storage_uri": "gs://x"}])
    status_get, payload_get = _request("GET", api_env, f"/api/capture/contexts?domain={domain}&run_id={run_id}")
    assert status_get == HTTPStatus.OK
    capture_context_id = payload_get["contexts"][0]["capture_context_id"]

    first = {
        "domain": domain,
        "run_id": run_id,
        "capture_context_id": capture_context_id,
        "language": "en",
        "status": "blocked_by_overlay",
        "reviewer": "operator",
        "timestamp": "2026-03-10T12:00:00Z",
    }
    second = dict(first)
    second["status"] = "not_found"
    second["timestamp"] = "2026-03-10T12:10:00Z"

    assert _request("POST", api_env, "/api/capture/reviews", first)[0] == HTTPStatus.OK
    assert _request("POST", api_env, "/api/capture/reviews", second)[0] == HTTPStatus.OK

    status_get2, payload_get2 = _request("GET", api_env, f"/api/capture/contexts?domain={domain}&run_id={run_id}")
    assert status_get2 == HTTPStatus.OK
    assert payload_get2["contexts"][0]["review_status"]["status"] == "not_found"


def test_review_validation_and_rerun_contract(api_env, monkeypatch):
    domain = "example.com"
    run_id = "run-rerun"

    status_bad, payload_bad = _request("POST", api_env, "/api/capture/reviews", {
        "domain": domain,
        "run_id": run_id,
        "capture_context_id": "ctx",
        "language": "en",
        "status": "approved",
        "reviewer": "operator",
        "timestamp": "2026-03-10T00:00:00Z",
    })
    assert status_bad == HTTPStatus.BAD_REQUEST
    assert "status" in payload_bad["error"]

    monkeypatch.setattr("app.skeleton_server._run_rerun_async", lambda job_id, runtime_payload: None)
    status_rerun, payload_rerun = _request("POST", api_env, "/api/capture/rerun", {
        "domain": domain,
        "run_id": run_id,
        "url": "https://a",
        "viewport_kind": "desktop",
        "state": "baseline",
        "language": "en",
        "user_tier": None,
        "capture_context_id": "ctx-1",
    })
    assert status_rerun == HTTPStatus.ACCEPTED
    assert payload_rerun["type"] == "rerun"
    assert payload_rerun["status"] == "running"


def test_rerun_job_failure_is_reflected_via_job_status(api_env, monkeypatch):
    domain = "example.com"
    run_id = "run-rerun-fail"

    def _explode(*args, **kwargs):
        raise RuntimeError("rerun boom")

    monkeypatch.setattr("pipeline.run_phase1.run_exact_context", _explode)

    status_rerun, payload_rerun = _request("POST", api_env, "/api/capture/rerun", {
        "domain": domain,
        "run_id": run_id,
        "url": "https://a",
        "viewport_kind": "desktop",
        "state": "baseline",
        "language": "en",
        "user_tier": None,
        "capture_context_id": "ctx-1",
    })
    assert status_rerun == HTTPStatus.ACCEPTED

    job_id = payload_rerun["job_id"]
    for _ in range(100):
        status_job, payload_job = _request("GET", api_env, f"/api/job?id={job_id}")
        assert status_job == HTTPStatus.OK
        if payload_job.get("status") in {"done", "error"}:
            break
    assert payload_job["status"] == "error"
    assert "rerun boom" in payload_job.get("error", "")

    runs_payload = storage.read_json_artifact(domain, "manual", "capture_runs.json")
    run_row = next(row for row in runs_payload["runs"] if row.get("run_id") == run_id)
    failed_job = next(row for row in run_row.get("jobs", []) if row.get("job_id") == job_id)
    assert failed_job["status"] == "failed"
    assert failed_job["type"] == "rerun"


def test_reviews_route_returns_not_ready_without_phase1_artifacts(api_env):
    domain = "example.com"
    run_id = "run-no-phase1"
    payload = {
        "domain": domain,
        "run_id": run_id,
        "capture_context_id": "ctx-arbitrary",
        "language": "en",
        "status": "valid",
        "reviewer": "operator",
        "timestamp": "2026-03-10T00:00:00Z",
    }
    assert _request("POST", api_env, "/api/capture/reviews", payload)[0] == HTTPStatus.OK

    status_reviews, body_reviews = _request("GET", api_env, f"/api/capture/reviews?domain={domain}&run_id={run_id}")
    assert status_reviews == HTTPStatus.NOT_FOUND
    assert body_reviews == {"status": "not_ready", "error": "page_screenshots artifact missing"}


def test_reviews_route_is_scoped_to_requested_run_contexts(api_env):
    domain = "example.com"
    run_id = "run-scoped"
    _write(domain, run_id, "page_screenshots.json", [
        {"page_id": "p1", "url": "https://a", "language": "en", "viewport_kind": "desktop", "state": "baseline", "user_tier": None, "storage_uri": "gs://x"}
    ])

    status_get, payload_get = _request("GET", api_env, f"/api/capture/contexts?domain={domain}&run_id={run_id}")
    assert status_get == HTTPStatus.OK
    capture_context_id = payload_get["contexts"][0]["capture_context_id"]

    assert _request("POST", api_env, "/api/capture/reviews", {
        "domain": domain,
        "run_id": run_id,
        "capture_context_id": capture_context_id,
        "language": "en",
        "status": "valid",
        "reviewer": "operator",
        "timestamp": "2026-03-10T10:00:00Z",
    })[0] == HTTPStatus.OK

    # unrelated review in the same domain should not leak into run-scoped response
    assert _request("POST", api_env, "/api/capture/reviews", {
        "domain": domain,
        "run_id": "other-run",
        "capture_context_id": "ctx-unrelated",
        "language": "en",
        "status": "blocked_by_overlay",
        "reviewer": "operator",
        "timestamp": "2026-03-10T10:01:00Z",
    })[0] == HTTPStatus.OK

    status_reviews, body_reviews = _request("GET", api_env, f"/api/capture/reviews?domain={domain}&run_id={run_id}")
    assert status_reviews == HTTPStatus.OK
    assert len(body_reviews["reviews"]) == 1
    assert body_reviews["reviews"][0]["capture_context_id"] == capture_context_id


def test_annotation_decisions_persist_to_template_rules_and_pulls(api_env):
    domain = "example.com"
    run_id = "run-rules"
    _write(domain, run_id, "page_screenshots.json", [
        {"page_id": "p1", "url": "https://a", "state": "baseline", "language": "en", "viewport_kind": "desktop", "user_tier": None, "screenshot_id": "s1", "storage_uri": "gs://test-bucket/example.com/run-rules/screenshots/p1.png", "captured_at": "2026-01-01T00:00:00Z", "viewport": {"width": 1200, "height": 1800}}
    ])
    _write(domain, run_id, "collected_items.json", [
        {"item_id": "i1", "page_id": "p1", "url": "https://a", "state": "baseline", "language": "en", "viewport_kind": "desktop", "user_tier": None, "element_type": "button", "css_selector": "button.buy", "bbox": {"x": 1, "y": 2, "width": 3, "height": 4}, "visible": True, "text": "Buy"}
    ])

    status_post, payload_post = _request("POST", api_env, "/api/rules", {
        "domain": domain,
        "run_id": run_id,
        "item_id": "i1",
        "url": "https://a",
        "state": "baseline",
        "language": "en",
        "viewport_kind": "desktop",
        "user_tier": None,
        "decision": "eligible",
    })
    assert status_post == HTTPStatus.OK
    assert payload_post["rule_type"] == "ALWAYS_COLLECT"

    status_rules, payload_rules = _request("GET", api_env, f"/api/rules?domain={domain}&run_id={run_id}")
    assert status_rules == HTTPStatus.OK
    assert payload_rules["rules"][0]["rule_type"] == "ALWAYS_COLLECT"

    status_pulls, payload_pulls = _request("GET", api_env, f"/api/pulls?domain={domain}&run_id={run_id}")
    assert status_pulls == HTTPStatus.OK
    assert payload_pulls["rows"][0]["decision"] == "ALWAYS_COLLECT"
