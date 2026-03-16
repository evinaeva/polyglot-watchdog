import http.client
import json
import threading
from http import HTTPStatus
from http.server import ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

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


def _request(method: str, port: int, path: str, body: str = "", headers: dict | None = None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    request_headers = headers or {}
    conn.request(method, path, body=body or None, headers=request_headers)
    response = conn.getresponse()
    raw = response.read()
    location = response.getheader("Location", "")
    content_type = response.getheader("Content-Type", "")
    conn.close()
    if "application/json" in content_type and raw:
        return response.status, json.loads(raw), location
    return response.status, raw.decode("utf-8") if raw else "", location


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


def _seed_runs(domain: str):
    _write("_system", "manual", "domains.json", {"domains": [domain]})
    _write(domain, "manual", "capture_runs.json", {
        "runs": [
            {"run_id": "run-en", "created_at": "2026-03-11T00:00:00Z", "jobs": []},
            {"run_id": "run-fr-old", "created_at": "2026-03-10T00:00:00Z", "jobs": []},
            {"run_id": "run-ja", "created_at": "2026-03-09T00:00:00Z", "jobs": []},
        ]
    })


def _seed_pages(domain: str, run_id: str, language: str, rows: list[dict] | None = None):
    if rows is None:
        rows = [{"page_id": "p1", "language": language, "url": "https://example.com", "viewport_kind": "desktop", "state": "baseline", "user_tier": "guest"}]
    _write(domain, run_id, "page_screenshots.json", rows)




def _seed_phase6_prereqs(domain: str, run_id: str, language: str = "en"):
    _seed_pages(domain, run_id, language)
    _write(domain, run_id, "collected_items.json", [{"item_id": "i1", "page_id": "p1", "language": language}])
    _write(domain, run_id, "eligible_dataset.json", [{"item_id": "i1", "language": language, "url": "https://example.com"}])


def test_get_check_languages_renders_new_inputs(api_env):
    domain = "example.com"
    _seed_runs(domain)
    _seed_pages(domain, "run-en", "en")
    _seed_pages(domain, "run-fr-old", "fr")

    status, body, _ = _request("GET", api_env, f"/check-languages?domain={domain}")
    assert status == HTTPStatus.OK
    assert 'name="en_run_id"' in body
    assert 'name="target_language"' in body
    assert 'name="run_id"' not in body


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/check-languages", "Domain is required."),
        ("/check-languages?domain=example.com&target_language=fr", "English reference run is required."),
        ("/check-languages?domain=example.com&en_run_id=run-en", "Target language is required."),
    ],
)
def test_get_check_languages_missing_input_validation(api_env, path, expected):
    _seed_runs("example.com")
    _seed_pages("example.com", "run-en", "en")
    status, body, _ = _request("GET", api_env, path)
    assert status == HTTPStatus.OK
    assert expected in body


def test_post_rejects_non_english_reference(api_env):
    domain = "example.com"
    _seed_runs(domain)
    _seed_pages(domain, "run-en", "en")
    _seed_pages(domain, "run-fr-old", "fr")

    form = "domain=example.com&en_run_id=run-fr-old&target_language=ja"
    status_post, _, location = _request("POST", api_env, "/check-languages", form, {"Content-Type": "application/x-www-form-urlencoded"})
    assert status_post == HTTPStatus.FOUND
    assert "not+English-only" in location


def test_post_starts_composed_async_workflow(api_env, monkeypatch):
    domain = "example.com"
    _seed_runs(domain)
    _seed_phase6_prereqs(domain, "run-en", "en")
    _seed_pages(domain, "run-fr-old", "fr")

    started = {}

    def _fake_run(job_id, domain, en_run_id, target_language, target_run_id):
        started["args"] = (job_id, domain, en_run_id, target_language, target_run_id)

    monkeypatch.setattr("app.skeleton_server._run_check_languages_async", _fake_run)

    form = "domain=example.com&en_run_id=run-en&target_language=fr"
    status_post, _, location = _request("POST", api_env, "/check-languages", form, {"Content-Type": "application/x-www-form-urlencoded"})
    assert status_post == HTTPStatus.FOUND
    parsed = parse_qs(urlparse(location).query)
    assert parsed["message"][0] == "Language check started."
    assert parsed["target_run_id"][0].startswith("run-en-check-fr")
    assert started["args"][1:] == ("example.com", "run-en", "fr", parsed["target_run_id"][0])

    runs = storage.read_json_artifact(domain, "manual", "capture_runs.json")
    run = next(row for row in runs["runs"] if row["run_id"] == parsed["target_run_id"][0])
    assert any(job.get("type") == "check_languages" and job.get("status") == "queued" for job in run["jobs"])


def test_duplicate_in_progress_guard(api_env):
    domain = "example.com"
    _seed_runs(domain)
    _seed_phase6_prereqs(domain, "run-en", "en")
    _seed_pages(domain, "run-fr-old", "fr")
    _seed_pages(domain, "run-en-check-fr", "fr")
    _write(domain, "manual", "capture_runs.json", {
        "runs": [
            {"run_id": "run-en-check-fr", "created_at": "2026-03-12T00:00:00Z", "jobs": [{"job_id": "check-languages-run-en-check-fr-1", "status": "running", "type": "check_languages", "en_run_id": "run-en", "target_language": "fr"}]},
            {"run_id": "run-en", "created_at": "2026-03-11T00:00:00Z", "jobs": []},
        ]
    })

    form = "domain=example.com&en_run_id=run-en&target_language=fr"
    status_post, _, location = _request("POST", api_env, "/check-languages", form, {"Content-Type": "application/x-www-form-urlencoded"})
    assert status_post == HTTPStatus.FOUND
    assert "already+in+progress" in location


def test_completed_state_shows_target_run_and_summary(api_env):
    domain = "example.com"
    _seed_runs(domain)
    _seed_phase6_prereqs(domain, "run-en", "en")
    target_run_id = "run-en-check-fr"
    _seed_pages(domain, target_run_id, "fr")
    _write(domain, target_run_id, "issues.json", [{"id": "1", "category": "TRANSLATION_MISMATCH", "severity": "high", "language": "fr", "state": "baseline"}])
    _write(domain, "manual", "capture_runs.json", {
        "runs": [
            {"run_id": target_run_id, "created_at": "2026-03-12T00:00:00Z", "jobs": [{"job_id": "check-languages-1", "status": "succeeded", "type": "check_languages", "stage": "completed", "en_run_id": "run-en", "target_language": "fr"}]},
            {"run_id": "run-en", "created_at": "2026-03-11T00:00:00Z", "jobs": []},
        ]
    })

    status, body, _ = _request("GET", api_env, f"/check-languages?domain={domain}&en_run_id=run-en&target_language=fr&target_run_id={target_run_id}")
    assert status == HTTPStatus.OK
    assert 'Current state: <strong id="checkLanguagesState">completed_with_issues</strong>' in body
    assert f"Generated target run: <code>{target_run_id}</code>" in body
    assert "Total: <strong>1</strong>" in body
    assert "Open issue explorer" in body



def test_target_language_options_allow_first_non_english_run(api_env):
    domain = "example.com"
    _seed_runs(domain)
    _seed_pages(domain, "run-en", "en")

    status, body, _ = _request("GET", api_env, f"/check-languages?domain={domain}")
    assert status == HTTPStatus.OK
    assert '<option value="fr"' in body


def test_post_rejects_when_english_reference_not_phase6_ready(api_env):
    domain = "example.com"
    _seed_runs(domain)
    _seed_pages(domain, "run-en", "en")

    form = "domain=example.com&en_run_id=run-en&target_language=fr"
    status_post, _, location = _request("POST", api_env, "/check-languages", form, {"Content-Type": "application/x-www-form-urlencoded"})
    assert status_post == HTTPStatus.FOUND
    assert "not+ready+for+comparison+prerequisites" in location


def test_queued_state_is_rendered_as_queued(api_env):
    domain = "example.com"
    _seed_runs(domain)
    _seed_phase6_prereqs(domain, "run-en", "en")
    _seed_pages(domain, "run-en-check-fr", "fr")
    _write(domain, "manual", "capture_runs.json", {
        "runs": [
            {"run_id": "run-en-check-fr", "created_at": "2026-03-12T00:00:00Z", "jobs": [{"job_id": "check-languages-1", "status": "queued", "type": "check_languages", "stage": "queued", "en_run_id": "run-en", "target_language": "fr"}]},
            {"run_id": "run-en", "created_at": "2026-03-11T00:00:00Z", "jobs": []},
        ]
    })

    status, body, _ = _request("GET", api_env, f"/check-languages?domain={domain}&en_run_id=run-en&target_language=fr&target_run_id=run-en-check-fr")
    assert status == HTTPStatus.OK
    assert 'Current state: <strong id="checkLanguagesState">queued</strong>' in body


def test_replay_scope_helper_uses_reference_contexts(monkeypatch):
    pages = [
        {"url": "https://example.com/a", "language": "en", "viewport_kind": "desktop", "state": "baseline", "user_tier": "guest"},
        {"url": "https://example.com/a", "language": "en", "viewport_kind": "desktop", "state": "checkout", "user_tier": "pro"},
        {"url": "https://example.com/a", "language": "fr", "viewport_kind": "desktop", "state": "baseline", "user_tier": "guest"},
    ]

    monkeypatch.setattr("app.skeleton_server._read_list_artifact_required", lambda domain, run_id, filename: pages)

    calls = []

    def _fake_build(domain, url, language, viewport_kind, state, user_tier):
        calls.append((domain, url, language, viewport_kind, state, user_tier))
        return {"ctx": (url, viewport_kind, state, user_tier)}

    monkeypatch.setattr("pipeline.run_phase1.build_exact_context_job", _fake_build)

    from app.skeleton_server import _replay_scope_from_reference_run

    jobs = _replay_scope_from_reference_run("example.com", "run-en", "ja")
    assert len(jobs) == 2
    assert calls == [
        ("example.com", "https://example.com/a", "ja", "desktop", "baseline", "guest"),
        ("example.com", "https://example.com/a", "ja", "desktop", "checkout", "pro"),
    ]


def test_orchestrator_runs_capture_then_comparison(monkeypatch):
    calls = []
    monkeypatch.setattr("app.skeleton_server._replay_scope_from_reference_run", lambda d, e, t: ["j1", "j2"])

    async def _fake_main(*args, **kwargs):
        calls.append("phase1")

    monkeypatch.setattr("pipeline.run_phase1.main", _fake_main)
    monkeypatch.setattr("pipeline.run_phase3.run", lambda **kwargs: calls.append("phase3"))
    monkeypatch.setattr("pipeline.run_phase6.run", lambda **kwargs: calls.append("phase6"))
    monkeypatch.setattr("app.skeleton_server._upsert_job_status", lambda *args, **kwargs: None)

    from app.skeleton_server import _run_check_languages_async

    _run_check_languages_async("job1", "example.com", "run-en", "fr", "run-en-check-fr")
    assert calls == ["phase1", "phase3", "phase6"]


def test_orchestrator_stops_before_comparison_on_capture_failure(monkeypatch):
    calls = []
    monkeypatch.setattr("app.skeleton_server._replay_scope_from_reference_run", lambda d, e, t: ["j1"])

    async def _fake_main(*args, **kwargs):
        calls.append("phase1")
        raise RuntimeError("capture failed")

    monkeypatch.setattr("pipeline.run_phase1.main", _fake_main)
    monkeypatch.setattr("pipeline.run_phase3.run", lambda **kwargs: calls.append("phase3"))
    monkeypatch.setattr("pipeline.run_phase6.run", lambda **kwargs: calls.append("phase6"))
    updates = []
    monkeypatch.setattr("app.skeleton_server._upsert_job_status", lambda d, r, rec: updates.append(rec))

    from app.skeleton_server import _run_check_languages_async

    _run_check_languages_async("job1", "example.com", "run-en", "fr", "run-en-check-fr")
    assert calls == ["phase1"]
    assert any(str(rec.get("stage")) == "running_target_capture_failed" for rec in updates)


def test_orchestrator_surfaces_comparison_failure(monkeypatch):
    monkeypatch.setattr("app.skeleton_server._replay_scope_from_reference_run", lambda d, e, t: ["j1"])

    async def _fake_main(*args, **kwargs):
        return None

    monkeypatch.setattr("pipeline.run_phase1.main", _fake_main)
    monkeypatch.setattr("pipeline.run_phase3.run", lambda **kwargs: None)
    monkeypatch.setattr("pipeline.run_phase6.run", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("phase6 failed")))
    updates = []
    monkeypatch.setattr("app.skeleton_server._upsert_job_status", lambda d, r, rec: updates.append(rec))

    from app.skeleton_server import _run_check_languages_async

    _run_check_languages_async("job1", "example.com", "run-en", "fr", "run-en-check-fr")
    assert any(str(rec.get("stage")) == "running_comparison_failed" for rec in updates)
