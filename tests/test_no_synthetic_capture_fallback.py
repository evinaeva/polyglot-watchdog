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


def test_static_invariant_no_synthetic_capture_fallback_codepaths():
    source = Path("app/skeleton_server.py").read_text(encoding="utf-8")
    assert "_bootstrap_capture_from_seed_urls" not in source
    assert "WORKFLOW_CAPTURE_FALLBACK" not in source
    assert "Captured text" not in source
    assert "gs://shot-" not in source


def test_behavior_invariant_capture_failure_does_not_create_synthetic_artifacts(api_env):
    domain = "example.com"
    run_id = f"run-invariant-{uuid.uuid4().hex[:8]}"
    seed_url = f"http://127.0.0.1:{api_env}/watchdog-fixture/index.html"

    assert _request("POST", api_env, "/api/seed-urls/add", {"domain": domain, "urls_multiline": seed_url})[0] == HTTPStatus.OK
    assert _request("POST", api_env, "/api/workflow/start-capture", {
        "domain": domain,
        "run_id": run_id,
        "language": "en",
        "viewport_kind": "desktop",
        "state": "baseline",
    })[0] == HTTPStatus.OK

    deadline = time.time() + 60
    payload = {}
    while time.time() < deadline:
        status, payload = _request("GET", api_env, f"/api/workflow/status?domain={domain}&run_id={run_id}")
        assert status == HTTPStatus.OK
        if payload.get("capture", {}).get("status") in {"failed", "ready", "empty"}:
            break
        time.sleep(0.5)

    assert payload.get("capture", {}).get("status") == "failed"

    from pipeline.storage import _gcs_client, artifact_path

    bucket = _gcs_client().bucket(storage.BUCKET_NAME)
    assert not bucket.blob(artifact_path(domain, run_id, "page_screenshots.json")).exists()
    assert not bucket.blob(artifact_path(domain, run_id, "collected_items.json")).exists()

    ctx_status, ctx_payload = _request("GET", api_env, f"/api/capture/contexts?domain={domain}&run_id={run_id}")
    assert ctx_status == HTTPStatus.NOT_FOUND
    assert ctx_payload == {"status": "not_ready", "error": "page_screenshots artifact missing"}
