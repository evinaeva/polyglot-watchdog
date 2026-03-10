import http.client
import json
import sys
import threading
import types
from http import HTTPStatus
from http.server import ThreadingHTTPServer

import pytest

from app.skeleton_server import SkeletonHandler
from pipeline import storage
from pipeline.run_phase3 import run as run_phase3


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
    body = json.dumps(payload) if payload is not None else None
    conn.request(method, path, body=body, headers={"Content-Type": "application/json"})
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

    storage_module = types.ModuleType("google.cloud.storage")
    storage_module.Client = lambda: _FakeClient(objects)
    cloud_module = types.ModuleType("google.cloud")
    cloud_module.storage = storage_module
    google_module = types.ModuleType("google")
    google_module.cloud = cloud_module
    monkeypatch.setitem(sys.modules, "google", google_module)
    monkeypatch.setitem(sys.modules, "google.cloud", cloud_module)
    monkeypatch.setitem(sys.modules, "google.cloud.storage", storage_module)

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


def test_phase3_consumes_persisted_reviews_and_rules_via_canonical_flow(api_env):
    domain = "example.com"
    run_id = "run-stage-b-phase3"

    _write(domain, run_id, "page_screenshots.json", [
        {"page_id": "p1", "url": "https://a", "language": "en", "viewport_kind": "desktop", "state": "baseline", "user_tier": None, "storage_uri": "gs://a"},
        {"page_id": "p2", "url": "https://b", "language": "en", "viewport_kind": "desktop", "state": "baseline", "user_tier": None, "storage_uri": "gs://b"},
    ])
    _write(domain, run_id, "collected_items.json", [
        {"item_id": "i1", "page_id": "p1", "url": "https://a", "state": "baseline", "language": "en", "viewport_kind": "desktop", "user_tier": None, "element_type": "button", "text": "Buy"},
        {"item_id": "i2", "page_id": "p2", "url": "https://b", "state": "baseline", "language": "en", "viewport_kind": "desktop", "user_tier": None, "element_type": "span", "text": "Price"},
        {"item_id": "i3", "page_id": "p2", "url": "https://b", "state": "baseline", "language": "en", "viewport_kind": "desktop", "user_tier": None, "element_type": "span", "text": "Inventory"},
    ])

    status_ctx, payload_ctx = _request("GET", api_env, f"/api/capture/contexts?domain={domain}&run_id={run_id}")
    assert status_ctx == HTTPStatus.OK
    assert len(payload_ctx["contexts"]) == 2
    context_by_url = {row["url"]: row["capture_context_id"] for row in payload_ctx["contexts"]}
    ctx_a = context_by_url["https://a"]
    ctx_b = context_by_url["https://b"]

    # last-write-wins proof + special statuses persisted
    assert _request("POST", api_env, "/api/capture/reviews", {
        "domain": domain, "run_id": run_id, "capture_context_id": ctx_a, "language": "en",
        "status": "retry_requested", "reviewer": "operator", "timestamp": "2026-03-10T11:00:00Z",
    })[0] == HTTPStatus.OK
    assert _request("POST", api_env, "/api/capture/reviews", {
        "domain": domain, "run_id": run_id, "capture_context_id": ctx_a, "language": "en",
        "status": "blocked_by_overlay", "reviewer": "operator", "timestamp": "2026-03-10T11:01:00Z",
    })[0] == HTTPStatus.OK

    assert _request("POST", api_env, "/api/capture/reviews", {
        "domain": domain, "run_id": run_id, "capture_context_id": ctx_b, "language": "en",
        "status": "valid", "reviewer": "operator", "timestamp": "2026-03-10T11:02:00Z",
    })[0] == HTTPStatus.OK
    assert _request("POST", api_env, "/api/capture/reviews", {
        "domain": domain, "run_id": run_id, "capture_context_id": ctx_b, "language": "en",
        "status": "not_found", "reviewer": "operator", "timestamp": "2026-03-10T11:03:00Z",
    })[0] == HTTPStatus.OK

    # persist rules via public API (canonical Phase2 write)
    assert _request("POST", api_env, "/api/rules", {
        "domain": domain, "run_id": run_id, "item_id": "i1", "url": "https://a", "decision": "eligible",
    })[0] == HTTPStatus.OK
    assert _request("POST", api_env, "/api/rules", {
        "domain": domain, "run_id": run_id, "item_id": "i2", "url": "https://b", "decision": "exclude",
    })[0] == HTTPStatus.OK
    assert _request("POST", api_env, "/api/rules", {
        "domain": domain, "run_id": run_id, "item_id": "i3", "url": "https://b", "decision": "needs-fix",
    })[0] == HTTPStatus.OK

    status_rules, payload_rules = _request("GET", api_env, f"/api/rules?domain={domain}&run_id={run_id}")
    assert status_rules == HTTPStatus.OK
    assert sorted((row["item_id"], row["rule_type"]) for row in payload_rules["rules"]) == [
        ("i1", "ALWAYS_COLLECT"),
        ("i2", "IGNORE_ENTIRE_ELEMENT"),
        ("i3", "MASK_VARIABLE"),
    ]

    persisted_rules = storage.read_json_artifact(domain, run_id, "template_rules.json")
    assert sorted((row["item_id"], row["rule_type"]) for row in persisted_rules) == [
        ("i1", "ALWAYS_COLLECT"),
        ("i2", "IGNORE_ENTIRE_ELEMENT"),
        ("i3", "MASK_VARIABLE"),
    ]

    eligible_rows = run_phase3(domain, run_id)
    assert [row["item_id"] for row in eligible_rows] == ["i3"]
    assert eligible_rows[0]["mask_applied"] is True

    eligible_dataset = storage.read_json_artifact(domain, run_id, "eligible_dataset.json")
    assert [row["item_id"] for row in eligible_dataset] == ["i3"]
    assert eligible_dataset[0]["mask_applied"] is True

    manifest = storage.read_json_artifact(domain, run_id, "phase3_manifest.json")
    assert manifest["summary_counters"]["blocked_overlay_contexts"] == 1
    error_records = {(rec["capture_context_id"], rec["status"]) for rec in manifest["error_records"]}
    assert (ctx_a, "blocked_by_overlay") in error_records
    assert (ctx_b, "not_found") in error_records
