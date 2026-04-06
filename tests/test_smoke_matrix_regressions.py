from __future__ import annotations

import http.client
import json
import threading
from http import HTTPStatus
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote_plus

import pytest

from app.skeleton_server import SkeletonHandler
from pipeline import storage
from tests.smoke_matrix import EXISTING_COVERAGE_TESTS, SMOKE_MATRIX


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
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
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
    monkeypatch.setattr("app.skeleton_server._run_phase0_async", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.skeleton_server._run_phase1_async", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.skeleton_server._run_phase3_async", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.skeleton_server._run_phase6_async", lambda *args, **kwargs: None)

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


def _seed_baseline(domain: str, run_id: str):
    _write("_system", "manual", "domains.json", {"domains": [domain]})
    _write(domain, "manual", "capture_runs.json", {"runs": [{"run_id": run_id, "created_at": "2026-04-06T00:00:00Z", "jobs": []}]})
    _write(domain, run_id, "page_screenshots.json", [{"page_id": "p1", "url": "https://example.com", "language": "en", "viewport_kind": "desktop", "state": "baseline", "user_tier": "guest", "storage_uri": "gs://shot"}])
    _write(domain, run_id, "collected_items.json", [{"item_id": "i1", "page_id": "p1", "url": "https://example.com", "language": "en", "viewport_kind": "desktop", "state": "baseline", "user_tier": "guest", "element_type": "button", "text": "Buy", "bbox": {"x": 1, "y": 2, "width": 3, "height": 4}, "visible": True}])
    _write(domain, run_id, "issues.json", [])
    _write(domain, run_id, "eligible_dataset.json", [{"item_id": "i1", "url": "https://example.com", "language": "en"}])


def _snapshot_main_pages(port: int, domain: str, run_id: str) -> dict[str, int]:
    encoded_domain = quote_plus(domain)
    pages = {
        "/": f"/?domain={encoded_domain}&run_id={run_id}",
        "/workflow": f"/workflow?domain={encoded_domain}&run_id={run_id}",
        "/check-languages": f"/check-languages?selected_domain={encoded_domain}",
        "/pulls": f"/pulls?domain={encoded_domain}&run_id={run_id}",
        "/result-files": f"/result-files?domain={encoded_domain}&run_id={run_id}",
        "/urls": "/urls",
        "/runs": "/runs",
    }
    return {name: _request("GET", port, path)[0] for name, path in pages.items()}


def _snapshot_read_api(port: int, domain: str, run_id: str) -> dict[str, tuple[int, dict]]:
    encoded_domain = quote_plus(domain)
    endpoints = {
        "/api/domains": "/api/domains",
        "/api/capture/runs": f"/api/capture/runs?domain={encoded_domain}",
        "/api/workflow/status": f"/api/workflow/status?domain={encoded_domain}&run_id={run_id}",
        "/api/issues": f"/api/issues?domain={encoded_domain}&run_id={run_id}",
        "/api/pulls": f"/api/pulls?domain={encoded_domain}&run_id={run_id}",
    }
    snap: dict[str, tuple[int, dict]] = {}
    for route, path in endpoints.items():
        status, payload = _request("GET", port, path)
        snap[route] = (status, payload if isinstance(payload, dict) else {})
    return snap


def _write_requests(domain: str, run_id: str) -> dict[str, dict]:
    return {
        "/api/seed-urls/add": {"domain": domain, "urls_multiline": "https://example.com"},
        "/api/seed-urls/row-upsert": {
            "domain": domain,
            "row": {"url": "https://example.com/row", "description": "smoke", "recipe_ids": [], "active": True},
        },
        "/api/seed-urls/clear": {"domain": domain},
        "/api/recipes/upsert": {
            "domain": domain,
            "recipe": {
                "recipe_id": "smoke-recipe",
                "url_pattern": "example.com",
                "steps": [],
                "capture_points": [{"state": "baseline", "capture_point_id": "cp-baseline"}],
            },
        },
        "/api/recipes/delete": {"domain": domain, "recipe_id": "smoke-recipe"},
        "/api/capture/start": {"domain": domain, "run_id": run_id, "url": "https://example.com", "language": "en", "viewport_kind": "desktop", "state": "baseline"},
        "/api/workflow/generate-eligible-dataset": {"domain": domain, "run_id": run_id},
        "/api/workflow/generate-issues": {"domain": domain, "run_id": run_id, "en_run_id": run_id},
    }


def test_smoke_matrix_is_bound_to_existing_test_suites():
    for entry in SMOKE_MATRIX:
        assert entry.covered_by, f"{entry.path} should be mapped to existing suites"
        for test_path in entry.covered_by:
            assert test_path in EXISTING_COVERAGE_TESTS
            assert Path(test_path).exists(), f"Coverage target file is missing: {test_path}"


def test_smoke_before_after_with_same_fixtures(api_env):
    domain = "example.com"
    run_id = "smoke-run"
    _seed_baseline(domain, run_id)

    before_pages = _snapshot_main_pages(api_env, domain, run_id)
    before_read = _snapshot_read_api(api_env, domain, run_id)

    route_by_path = {route.path: route for route in SMOKE_MATRIX}
    for path, payload in _write_requests(domain, run_id).items():
        status, response_payload = _request("POST", api_env, path, payload)
        assert status != HTTPStatus.INTERNAL_SERVER_ERROR, f"write endpoint returned 500: {path}"
        assert isinstance(response_payload, dict), f"write endpoint must return json payload: {path}"
        expected_keys = set(route_by_path[path].expected_json_keys)
        assert expected_keys.issubset(response_payload.keys()), f"write endpoint missing keys for {path}: {expected_keys - set(response_payload.keys())}"

    after_pages = _snapshot_main_pages(api_env, domain, run_id)
    after_read = _snapshot_read_api(api_env, domain, run_id)

    for path, status in before_pages.items():
        assert status != HTTPStatus.INTERNAL_SERVER_ERROR, f"before: {path} returned 500"
    for path, status in after_pages.items():
        assert status != HTTPStatus.INTERNAL_SERVER_ERROR, f"after: {path} returned 500"

    required_read_keys = {
        "/api/domains": {"items"},
        "/api/capture/runs": {"runs"},
        "/api/workflow/status": {"capture", "run"},
        "/api/issues": {"count", "issues"},
        "/api/pulls": {"rows"},
    }

    for route, keys in required_read_keys.items():
        before_status, before_payload = before_read[route]
        after_status, after_payload = after_read[route]
        assert before_status != HTTPStatus.INTERNAL_SERVER_ERROR
        assert after_status != HTTPStatus.INTERNAL_SERVER_ERROR
        assert keys.issubset(before_payload.keys()), f"before: {route} missing keys {keys - set(before_payload.keys())}"
        assert keys.issubset(after_payload.keys()), f"after: {route} missing keys {keys - set(after_payload.keys())}"
        assert before_status == after_status, f"status drift detected for {route}: {before_status} -> {after_status}"
