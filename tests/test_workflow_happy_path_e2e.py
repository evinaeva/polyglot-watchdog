"""Happy-path end-to-end acceptance test for the full v1.0 Workstream A operator journey.

This test is SKIPPED (not failed) when Playwright is unavailable, so it is safe to
include in the default test suite. In CI without Playwright the test simply reports:

    SKIPPED [reason: Playwright Chromium binary not found ...]

The deterministic, clean-env way to run this test is via Docker:

    bash scripts/run_e2e_happy_path.sh

Inside Dockerfile.e2e, PLAYWRIGHT_BROWSERS_PATH=/ms-playwright is pre-installed
at image-build time, so the probe always returns (True, 'ok') and the test runs.

Constraints enforced by this test:
- No phase runner functions are monkeypatched.
- No artifacts are written directly (no storage.write_json_artifact calls).
- No synthetic fallback paths are used.
- All workflow steps go through the real HTTP API (UI-equivalent path).
"""
from __future__ import annotations

import http.client
import json
import threading
import time
import uuid
from http import HTTPStatus
from http.server import ThreadingHTTPServer

import pytest

from tests.playwright_probe import playwright_ready

_READY, _REASON = playwright_ready()

pytestmark = [
    pytest.mark.skipif(not _READY, reason=_REASON),
    pytest.mark.e2e_happy_path,
]

# ---------------------------------------------------------------------------
# Shared fake GCS infrastructure (same pattern as existing acceptance tests)
# ---------------------------------------------------------------------------


class _BlobMeta:
    def __init__(self, name: str):
        self.name = name


class _FakeBlob:
    def __init__(self, objects: dict, bucket: str, path: str):
        self._objects = objects
        self._bucket = bucket
        self._path = path

    def upload_from_string(self, content, content_type=None):
        payload = content.encode("utf-8") if isinstance(content, str) else bytes(content)
        self._objects[(self._bucket, self._path)] = payload

    def download_as_text(self, encoding="utf-8"):
        data = self._objects[(self._bucket, self._path)]
        return data.decode(encoding)

    def exists(self, client=None):
        return (self._bucket, self._path) in self._objects


class _FakeBucket:
    def __init__(self, objects: dict, name: str):
        self._objects = objects
        self._name = name

    def blob(self, path: str):
        return _FakeBlob(self._objects, self._name, path)

    def list_blobs(self, prefix: str):
        names = sorted(
            path for (bucket, path) in self._objects
            if bucket == self._name and path.startswith(prefix)
        )
        return [_BlobMeta(name=n) for n in names]


class _FakeClient:
    def __init__(self, objects: dict):
        self._objects = objects

    def bucket(self, name: str):
        return _FakeBucket(self._objects, name)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _req(method: str, port: int, path: str, payload: dict | None = None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
    headers = {"Content-Type": "application/json"}
    body = json.dumps(payload) if payload is not None else None
    conn.request(method, path, body=body, headers=headers)
    resp = conn.getresponse()
    raw = resp.read()
    conn.close()
    return resp.status, (json.loads(raw) if raw else {})


def _poll_until(port: int, path: str, accept, timeout: float = 180.0, interval: float = 1.0) -> dict:
    """Poll GET endpoint until accept(payload) returns True, or raise TimeoutError."""
    deadline = time.time() + timeout
    last_payload: dict = {}
    while time.time() < deadline:
        status, last_payload = _req("GET", port, path)
        assert status == HTTPStatus.OK, f"Unexpected {status} from {path}: {last_payload}"
        if accept(last_payload):
            return last_payload
        time.sleep(interval)
    raise TimeoutError(
        f"Timed out polling {path}. Last payload: {json.dumps(last_payload, indent=2)}"
    )


# ---------------------------------------------------------------------------
# Fixture: real server + fake GCS (function-scoped; monkeypatch is function-scoped)
# ---------------------------------------------------------------------------


@pytest.fixture
def api_env(monkeypatch):
    """Spin up the real SkeletonHandler server with fake GCS storage.

    PLAYWRIGHT_BROWSERS_PATH is intentionally NOT overridden here.
    Inside Dockerfile.e2e it is already set to /ms-playwright (pre-installed).
    On a developer machine it should point to the local Playwright cache.
    """
    from app.skeleton_server import SkeletonHandler
    from pipeline import storage

    objects: dict = {}
    monkeypatch.setenv("AUTH_MODE", "OFF")
    monkeypatch.setattr(storage, "BUCKET_NAME", "test-bucket-e2e")
    monkeypatch.setattr(storage, "validate", lambda *a, **kw: None)
    monkeypatch.setattr(storage, "_gcs_client", lambda: _FakeClient(objects))
    monkeypatch.setattr(
        "app.skeleton_server._ReviewConfigStore._client",
        lambda self: _FakeClient(objects),
    )
    monkeypatch.setattr("google.cloud.storage.Client", lambda: _FakeClient(objects))

    server = ThreadingHTTPServer(("127.0.0.1", 0), SkeletonHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    try:
        yield port
    finally:
        server.shutdown()
        thread.join(timeout=5)


# ---------------------------------------------------------------------------
# The happy-path E2E test
# ---------------------------------------------------------------------------


def test_full_v1_operator_journey_happy_path(api_env):
    """Prove the full v1.0 operator journey is executable end-to-end.

    Steps (all via HTTP API — no direct artifact writes, no runner monkeypatching):
      1. Configure seed URL pointing at the local fixture server
      2. Start EN baseline capture
      3. Poll until capture.status == ready
      4. Save one review decision via canonical review API
      5. Save one annotation rule via canonical rules API (if items present)
      6. Generate eligible dataset; poll until terminal
      7. Generate issues (self-comparison: EN vs EN → 0 issues = empty-success)
         poll until issues.status is ready or empty
      8. GET /api/issues — assert well-formed response
      9. GET /api/issues/detail — assert artifact_refs present (if any issue exists)
    """
    port = api_env
    domain = "fixture.local"
    run_id = f"happy-{uuid.uuid4().hex[:10]}"

    fixture_url = f"http://127.0.0.1:{port}/watchdog-fixture/index.html"

    # Step 1: Configure seed URL
    status, payload = _req("POST", port, "/api/seed-urls/add", {
        "domain": domain,
        "urls_multiline": fixture_url,
    })
    assert status == HTTPStatus.OK, f"seed-urls/add failed: {payload}"

    # Step 2: Start EN capture
    status, payload = _req("POST", port, "/api/workflow/start-capture", {
        "domain": domain,
        "run_id": run_id,
        "language": "en",
        "viewport_kind": "desktop",
        "state": "baseline",
    })
    assert status == HTTPStatus.OK, f"start-capture failed: {payload}"
    assert payload.get("status") == "started"

    # Step 3: Poll until capture reaches a terminal state; assert ready
    status_payload = _poll_until(
        port,
        f"/api/workflow/status?domain={domain}&run_id={run_id}",
        accept=lambda p: p.get("capture", {}).get("status") in {"ready", "empty", "failed"},
        timeout=180,
    )
    capture_status = status_payload["capture"]["status"]
    assert capture_status == "ready", (
        f"Capture did not reach ready state. Got: {capture_status!r}. "
        f"Error: {status_payload['capture'].get('error', '')}"
    )
    assert status_payload["capture"]["artifacts_present"] is True
    assert status_payload["capture"]["contexts"] >= 1

    # Step 4: Fetch contexts and save at least one review decision
    ctx_status, ctx_payload = _req(
        "GET", port, f"/api/capture/contexts?domain={domain}&run_id={run_id}"
    )
    assert ctx_status == HTTPStatus.OK, f"capture/contexts failed: {ctx_payload}"
    contexts = ctx_payload.get("contexts", [])
    assert len(contexts) >= 1, "Expected at least one capture context"

    first_ctx = contexts[0]
    capture_context_id = first_ctx["capture_context_id"]
    language = first_ctx["language"]

    rev_status, rev_payload = _req("POST", port, "/api/capture/reviews", {
        "domain": domain,
        "capture_context_id": capture_context_id,
        "language": language,
        "status": "valid",
        "reviewer": "e2e-test",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })
    assert rev_status == HTTPStatus.OK, f"capture/reviews POST failed: {rev_payload}"
    assert rev_payload.get("record", {}).get("status") == "valid"

    # Step 5: Fetch pulls and save one annotation rule (if items present)
    pulls_status, pulls_payload = _req(
        "GET", port, f"/api/pulls?domain={domain}&run_id={run_id}"
    )
    assert pulls_status == HTTPStatus.OK, f"GET /api/pulls failed: {pulls_payload}"
    rows = pulls_payload.get("rows", [])

    if rows:
        first_row = rows[0]
        rule_status, rule_payload = _req("POST", port, "/api/rules", {
            "domain": domain,
            "run_id": run_id,
            "item_id": first_row["item_id"],
            "url": first_row["url"],
            "decision": "eligible",
        })
        assert rule_status == HTTPStatus.OK, f"POST /api/rules failed: {rule_payload}"
        assert rule_payload.get("status") == "ok"

    # Step 6: Generate eligible dataset; poll until terminal
    gen_status, gen_payload = _req("POST", port, "/api/workflow/generate-eligible-dataset", {
        "domain": domain,
        "run_id": run_id,
    })
    assert gen_status == HTTPStatus.OK, f"generate-eligible-dataset failed: {gen_payload}"
    assert gen_payload.get("status") == "started"

    _poll_until(
        port,
        f"/api/workflow/status?domain={domain}&run_id={run_id}",
        accept=lambda p: p.get("eligible_dataset", {}).get("status") in {"ready", "empty"},
        timeout=60,
    )

    # Step 7: Generate issues; poll until terminal (ready or empty)
    iss_status, iss_payload = _req("POST", port, "/api/workflow/generate-issues", {
        "domain": domain,
        "run_id": run_id,
        "en_run_id": run_id,
    })
    assert iss_status == HTTPStatus.OK, f"generate-issues failed: {iss_payload}"
    assert iss_payload.get("status") == "started"

    final_status = _poll_until(
        port,
        f"/api/workflow/status?domain={domain}&run_id={run_id}",
        accept=lambda p: p.get("issues", {}).get("status") in {"ready", "empty"},
        timeout=60,
    )

    assert final_status["issues"]["status"] in {"ready", "empty"}

    # Step 8: GET /api/issues — well-formed response
    iss_get_status, iss_get_payload = _req(
        "GET", port, f"/api/issues?domain={domain}&run_id={run_id}"
    )
    assert iss_get_status == HTTPStatus.OK
    assert "issues" in iss_get_payload
    assert "count" in iss_get_payload
    assert iss_get_payload["count"] == len(iss_get_payload["issues"])

    # Step 9: GET /api/issues/detail (only if issues exist)
    if iss_get_payload["count"] > 0:
        first_issue_id = iss_get_payload["issues"][0]["id"]
        detail_status, detail_payload = _req(
            "GET", port,
            f"/api/issues/detail?domain={domain}&run_id={run_id}&id={first_issue_id}",
        )
        assert detail_status == HTTPStatus.OK
        drilldown = detail_payload.get("drilldown", {})
        artifact_refs = drilldown.get("artifact_refs", {})
        assert artifact_refs.get("issues")
        assert artifact_refs.get("page_screenshots")
        assert artifact_refs.get("collected_items")
    else:
        assert isinstance(iss_get_payload["issues"], list)

    # Final invariant: capture artifacts are real (Playwright-produced)
    assert final_status["capture"]["artifacts_present"] is True
    assert final_status["eligible_dataset"]["status"] in {"ready", "empty"}
    assert final_status["issues"]["status"] in {"ready", "empty"}
