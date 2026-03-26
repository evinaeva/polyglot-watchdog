import http.client
import json
import threading
import uuid
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


def _request_multipart(port: int, path: str, fields: dict[str, str], filename: str, content: bytes, *, quoted_boundary: bool = False):
    boundary = f"----watchdog-{uuid.uuid4().hex}"
    body_parts: list[bytes] = []
    for key, value in fields.items():
        body_parts.append(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{key}"\r\n\r\n'
                f"{value}\r\n"
            ).encode("utf-8")
        )
    body_parts.append(
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            "Content-Type: application/json\r\n\r\n"
        ).encode("utf-8")
    )
    body_parts.append(content)
    body_parts.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request(
        "POST",
        path,
        body=b"".join(body_parts),
        headers={"Content-Type": f"multipart/form-data; boundary=\"{boundary}\"" if quoted_boundary else f"multipart/form-data; boundary={boundary}"},
    )
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


def test_recipe_upload_supports_json5_attach_and_overwrite_confirmation(api_env):
    domain = "example.com"
    _request("POST", api_env, "/api/seed-urls/add", {"domain": domain, "urls_multiline": "https://example.com/p1"})

    status, body = _request_multipart(
        api_env,
        "/api/recipes/upload",
        {"domain_id": domain, "attach_to_url": "true", "url": "https://example.com/p1"},
        "recipe.json5",
        b'{// comment\n"recipe_id":"r-upload","url_pattern":"/p1","steps":[],"capture_points":[{"state":"baseline"},],}',
    )
    assert status == HTTPStatus.OK
    assert body["status"] == "ok"
    assert body["recipe_id"] == "r-upload"
    assert body["attached_to_url"] is True

    seed_status, seed_body = _request("GET", api_env, f"/api/seed-urls?domain={domain}")
    assert seed_status == HTTPStatus.OK
    assert seed_body["urls"][0]["recipe_ids"] == ["r-upload"]
    seed_updated_at_before_conflict = seed_body["updated_at"]

    conflict_status, conflict_body = _request_multipart(
        api_env,
        "/api/recipes/upload",
        {"domain_id": domain, "attach_to_url": "false"},
        "recipe.json",
        b'{"recipe_id":"r-upload","url_pattern":"/p1","steps":[],"capture_points":[{"state":"baseline"}]}',
    )
    assert conflict_status == HTTPStatus.CONFLICT
    assert conflict_body["status"] == "overwrite_required"
    recipes_after_conflict = _request("GET", api_env, f"/api/recipes?domain={domain}")[1]["recipes"]
    assert [row["recipe_id"] for row in recipes_after_conflict] == ["r-upload"]
    seed_after_conflict = _request("GET", api_env, f"/api/seed-urls?domain={domain}")[1]
    assert seed_after_conflict["urls"][0]["recipe_ids"] == ["r-upload"]
    assert seed_after_conflict["updated_at"] == seed_updated_at_before_conflict

    overwrite_status, overwrite_body = _request_multipart(
        api_env,
        "/api/recipes/upload",
        {"domain_id": domain, "attach_to_url": "false", "overwrite": "true"},
        "recipe.json",
        b'{"recipe_id":"r-upload","url_pattern":"/p1","steps":[],"capture_points":[{"state":"baseline"}]}',
    )
    assert overwrite_status == HTTPStatus.OK
    assert overwrite_body["overwrote"] is True


def test_recipe_upload_attach_noop_does_not_duplicate_recipe_id_or_rewrite_seed_rows(api_env):
    domain = "attach-noop.example"
    _write(
        domain,
        "manual",
        "seed_urls.json",
        {
            "domain": domain,
            "updated_at": "2026-03-01T00:00:00Z",
            "urls": [{"url": "https://attach-noop.example/p1", "description": None, "recipe_ids": ["m"]}],
        },
    )
    _write(
        domain,
        "manual",
        "seed_url_states.json",
        {"updated_at": "2026-03-01T00:00:00Z", "states": [{"url": "https://attach-noop.example/p1", "active": True}]},
    )
    _write(domain, "manual", "recipes.json", [{"recipe_id": "m", "url_pattern": "*", "steps": [], "capture_points": []}])

    first_status, first_body = _request_multipart(
        api_env,
        "/api/recipes/upload",
        {"domain_id": domain, "attach_to_url": "true", "url": "https://attach-noop.example/p1", "overwrite": "true"},
        "m.json",
        b'{"recipe_id":"m"}',
    )
    assert first_status == HTTPStatus.OK
    assert first_body["status"] == "ok"
    assert first_body["overwrote"] is True

    seed_after_noop = _request("GET", api_env, f"/api/seed-urls?domain={domain}")[1]
    assert seed_after_noop["urls"][0]["recipe_ids"] == ["m"]
    assert seed_after_noop["updated_at"] == "2026-03-01T00:00:00Z"


def test_recipe_upload_attach_same_recipe_set_different_order_is_noop(api_env):
    domain = "attach-order-noop.example"
    _write(
        domain,
        "manual",
        "seed_urls.json",
        {
            "domain": domain,
            "updated_at": "2026-03-01T00:00:00Z",
            "urls": [{"url": "https://attach-order-noop.example/p1", "description": None, "recipe_ids": ["b", "a"]}],
        },
    )
    _write(
        domain,
        "manual",
        "seed_url_states.json",
        {"updated_at": "2026-03-01T00:00:00Z", "states": [{"url": "https://attach-order-noop.example/p1", "active": True}]},
    )
    _write(
        domain,
        "manual",
        "recipes.json",
        [
            {"recipe_id": "a", "url_pattern": "*", "steps": [], "capture_points": []},
            {"recipe_id": "b", "url_pattern": "*", "steps": [], "capture_points": []},
        ],
    )

    status, body = _request_multipart(
        api_env,
        "/api/recipes/upload",
        {"domain_id": domain, "attach_to_url": "true", "url": "https://attach-order-noop.example/p1", "overwrite": "true"},
        "a.json",
        b'{"recipe_id":"a"}',
    )
    assert status == HTTPStatus.OK
    assert body["status"] == "ok"

    seed_after = _request("GET", api_env, f"/api/seed-urls?domain={domain}")[1]
    assert seed_after["updated_at"] == "2026-03-01T00:00:00Z"
    assert seed_after["urls"][0]["recipe_ids"] == ["a", "b"]


def test_recipe_upload_json_and_delete_clears_seed_url_associations(api_env):
    domain = "example.com"
    _request("POST", api_env, "/api/seed-urls/add", {"domain": domain, "urls_multiline": "https://example.com/p2"})
    upload_status, upload_body = _request_multipart(
        api_env,
        "/api/recipes/upload",
        {"domain_id": domain, "attach_to_url": "true", "url": "https://example.com/p2"},
        "recipe.json",
        b'{"recipe_id":"r-json","url_pattern":"/p2"}',
    )
    assert upload_status == HTTPStatus.OK
    assert upload_body["status"] == "ok"
    assert upload_body["attached_to_url"] is True

    delete_status, delete_body = _request("POST", api_env, "/api/recipes/delete", {"domain": domain, "recipe_id": "r-json"})
    assert delete_status == HTTPStatus.OK
    assert delete_body["status"] == "ok"
    assert delete_body["recipe_id"] == "r-json"

    seed_status, seed_body = _request("GET", api_env, f"/api/seed-urls?domain={domain}")
    assert seed_status == HTTPStatus.OK
    assert seed_body["urls"][0]["recipe_ids"] == []


def test_recipe_upload_attach_failure_does_not_persist_recipe(api_env):
    domain = "atomic-upload.example"
    status, body = _request_multipart(
        api_env,
        "/api/recipes/upload",
        {"domain_id": domain, "attach_to_url": "true", "url": "https://atomic-upload.example/missing"},
        "missing.json",
        b'{"recipe_id":"should-not-save","url_pattern":"/missing"}',
    )
    assert status == HTTPStatus.BAD_REQUEST
    assert body["status"] == "failed"

    list_status, list_body = _request("GET", api_env, f"/api/recipes?domain={domain}")
    assert list_status == HTTPStatus.OK
    assert list_body["recipes"] == []


def test_recipe_upload_accepts_minimal_payload_via_compat_normalization(api_env):
    domain = "example.com"
    status, body = _request_multipart(
        api_env,
        "/api/recipes/upload",
        {"domain_id": domain, "attach_to_url": "false"},
        "minimal.json",
        b'{"recipe_id":"minimal-only"}',
    )
    assert status == HTTPStatus.OK
    assert body["status"] == "ok"
    assert body["recipe"]["recipe_id"] == "minimal-only"
    assert body["recipe"]["url_pattern"] == "*"
    assert body["recipe"]["steps"] == []
    assert body["recipe"]["capture_points"] == []


def test_recipe_upload_attach_preserves_seed_row_order(api_env):
    domain = "order.example"
    _write(
        domain,
        "manual",
        "seed_urls.json",
        {
            "domain": domain,
            "updated_at": "2026-03-01T00:00:00Z",
            "urls": [
                {"url": "https://order.example/second", "description": None, "recipe_ids": []},
                {"url": "https://order.example/first", "description": None, "recipe_ids": []},
            ],
        },
    )
    _write(
        domain,
        "manual",
        "seed_url_states.json",
        {
            "updated_at": "2026-03-01T00:00:00Z",
            "states": [
                {"url": "https://order.example/second", "active": True},
                {"url": "https://order.example/first", "active": True},
            ],
        },
    )

    status, body = _request_multipart(
        api_env,
        "/api/recipes/upload",
        {"domain_id": domain, "attach_to_url": "true", "url": "https://order.example/second"},
        "order.json",
        b'{"recipe_id":"order-r1"}',
    )
    assert status == HTTPStatus.OK
    assert body["status"] == "ok"

    seed_status, seed_body = _request("GET", api_env, f"/api/seed-urls?domain={domain}")
    assert seed_status == HTTPStatus.OK
    assert [row["url"] for row in seed_body["urls"]] == ["https://order.example/second", "https://order.example/first"]
    assert seed_body["urls"][0]["recipe_ids"] == ["order-r1"]


def test_recipe_upload_multipart_handles_quoted_boundary_and_empty_field(api_env):
    domain = "example.com"
    status, body = _request_multipart(
        api_env,
        "/api/recipes/upload",
        {"domain_id": domain, "attach_to_url": "false", "url": ""},
        "quoted.json5",
        b'{/*c*/"recipe_id":"quoted","url_pattern":"/x","steps":[],"capture_points":[]}',
        quoted_boundary=True,
    )
    assert status == HTTPStatus.OK
    assert body["status"] == "ok"
    assert body["recipe_id"] == "quoted"


def test_recipe_delete_cleanup_preserves_row_order_and_unrelated_fields(api_env):
    domain = "example.com"
    _request("POST", api_env, "/api/seed-urls/add", {"domain": domain, "urls_multiline": "https://example.com/second\nhttps://example.com/first"})
    _request("POST", api_env, "/api/seed-urls/row-upsert", {
        "domain": domain,
        "row": {"url": "https://example.com/second", "recipe_ids": ["keep", "drop"], "active": True},
    })
    _request("POST", api_env, "/api/seed-urls/row-upsert", {
        "domain": domain,
        "row": {"url": "https://example.com/first", "recipe_ids": ["drop"], "active": False},
    })
    _request_multipart(
        api_env,
        "/api/recipes/upload",
        {"domain_id": domain, "attach_to_url": "false"},
        "drop.json",
        b'{"recipe_id":"drop","url_pattern":"/x","steps":[],"capture_points":[]}',
    )
    status, body = _request("POST", api_env, "/api/recipes/delete", {"domain": domain, "recipe_id": "drop"})
    assert status == HTTPStatus.OK
    assert body["status"] == "ok"
    rows = body["seed_urls"]["urls"]
    assert [row["url"] for row in rows] == ["https://example.com/first", "https://example.com/second"]
    assert rows[0]["recipe_ids"] == []
    assert rows[1]["recipe_ids"] == ["keep"]
    assert rows[0]["active"] is False
