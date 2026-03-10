import http.client
import json
import threading
import time
import uuid
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
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=20)
    headers = {"Content-Type": "application/json"}
    body = json.dumps(payload) if payload is not None else None
    conn.request(method, path, body=body, headers=headers)
    response = conn.getresponse()
    raw = response.read()
    conn.close()
    return response.status, (json.loads(raw) if raw else {})


@pytest.fixture
def api_env(monkeypatch, tmp_path):
    objects: dict[tuple[str, str], bytes] = {}
    monkeypatch.setenv("AUTH_MODE", "OFF")
    # force runner-unavailable condition for deterministic truthful failure path
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path / "no-browsers"))
    monkeypatch.setattr(storage, "BUCKET_NAME", "test-bucket")
    monkeypatch.setattr(storage, "validate", lambda *args, **kwargs: None)
    monkeypatch.setattr(storage, "_gcs_client", lambda: _FakeClient(objects))
    monkeypatch.setattr("app.skeleton_server._ReviewConfigStore._client", lambda self: _FakeClient(objects))
    monkeypatch.setattr("google.cloud.storage.Client", lambda: _FakeClient(objects))

    server = ThreadingHTTPServer(("127.0.0.1", 0), SkeletonHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        thread.join(timeout=2)


def test_workflow_status_contract_reports_clean_state(api_env):
    domain = "example.com"
    run_id = "run-status-clean"

    assert _request("POST", api_env, "/api/seed-urls/add", {"domain": domain, "urls_multiline": "https://example.com/a"})[0] == HTTPStatus.OK

    status0, payload0 = _request("GET", api_env, f"/api/workflow/status?domain={domain}&run_id={run_id}")
    assert status0 == HTTPStatus.OK
    assert payload0["seed_urls"]["configured"] is True
    assert payload0["capture"]["status"] in {"not_ready", "not_started"}
    assert payload0["next_recommended_action"] == "start_capture"


def test_capture_failure_is_truthful_and_no_synthetic_artifacts(api_env):
    domain = "example.com"
    run_id = f"run-fail-{uuid.uuid4().hex[:8]}"
    seed_url = f"http://127.0.0.1:{api_env}/watchdog-fixture/index.html"

    assert _request("POST", api_env, "/api/seed-urls/add", {"domain": domain, "urls_multiline": seed_url})[0] == HTTPStatus.OK
    status_start, payload_start = _request("POST", api_env, "/api/workflow/start-capture", {
        "domain": domain,
        "run_id": run_id,
        "language": "en",
        "viewport_kind": "desktop",
        "state": "baseline",
    })
    assert status_start == HTTPStatus.OK
    assert payload_start["status"] == "started"

    deadline = time.time() + 60
    status_payload = {}
    while time.time() < deadline:
        status_code, status_payload = _request("GET", api_env, f"/api/workflow/status?domain={domain}&run_id={run_id}")
        assert status_code == HTTPStatus.OK
        if status_payload.get("capture", {}).get("status") in {"failed", "ready", "empty"}:
            break
        time.sleep(0.5)

    # In this test env we force missing browser runtime, so capture must fail truthfully.
    assert status_payload.get("capture", {}).get("status") == "failed"
    assert status_payload.get("run", {}).get("status") == "failed"
    assert status_payload.get("capture", {}).get("error")
    assert status_payload.get("next_recommended_action") == "start_capture"

    # No synthetic fallback artifacts are allowed.
    ctx_status, ctx_payload = _request("GET", api_env, f"/api/capture/contexts?domain={domain}&run_id={run_id}")
    assert ctx_status == HTTPStatus.NOT_FOUND
    assert ctx_payload == {"status": "not_ready", "error": "page_screenshots artifact missing"}

    from pipeline.storage import _gcs_client, artifact_path

    bucket = _gcs_client().bucket(storage.BUCKET_NAME)
    assert not bucket.blob(artifact_path(domain, run_id, "page_screenshots.json")).exists()
    assert not bucket.blob(artifact_path(domain, run_id, "collected_items.json")).exists()


    # downstream workflow actions must be blocked when capture is not ready
    ds_status, ds_payload = _request("POST", api_env, "/api/workflow/generate-eligible-dataset", {"domain": domain, "run_id": run_id})
    assert ds_status == HTTPStatus.CONFLICT
    assert ds_payload["status"] == "not_ready"
    assert ds_payload["action"] == "generate_eligible_dataset"

    issues_status, issues_payload = _request("POST", api_env, "/api/workflow/generate-issues", {"domain": domain, "run_id": run_id, "en_run_id": run_id})
    assert issues_status == HTTPStatus.CONFLICT
    assert issues_payload["status"] == "not_ready"
    assert issues_payload["action"] == "generate_issues"

    # document truthfully that clean-env happy path remains blocked when runner prerequisites are absent
    notes = Path("docs/WORKFLOW_GAP_MAP.md").read_text(encoding="utf-8")
    assert "capture runner prerequisites" in notes
