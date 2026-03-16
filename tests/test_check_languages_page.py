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


def _seed_runs(domain: str, target_run: str = "run-fr", en_run: str = "run-en"):
    _write("_system", "manual", "domains.json", {"domains": [domain]})
    _write(domain, "manual", "capture_runs.json", {
        "runs": [
            {"run_id": target_run, "created_at": "2026-03-10T00:00:00Z", "jobs": []},
            {"run_id": en_run, "created_at": "2026-03-11T00:00:00Z", "jobs": []},
        ]
    })


def _seed_phase6_prereqs(domain: str, run_id: str, language: str):
    _write(domain, run_id, "page_screenshots.json", [{"page_id": "p1", "language": language, "url": "https://example.com"}])
    _write(domain, run_id, "collected_items.json", [{"item_id": "i1", "page_id": "p1", "language": language}])
    _write(domain, run_id, "eligible_dataset.json", [{"item_id": "i1", "language": language, "url": "https://example.com"}])


def test_get_check_languages_renders_and_shows_readiness(api_env):
    domain = "example.com"
    _seed_runs(domain)
    _seed_phase6_prereqs(domain, "run-fr", "fr")
    _seed_phase6_prereqs(domain, "run-en", "en")

    status, body, _ = _request("GET", api_env, f"/check-languages?domain={domain}&run_id=run-fr&en_run_id=run-en")
    assert status == HTTPStatus.OK
    assert 'Current state: <strong id="checkLanguagesState">ready</strong>' in body
    assert "Start language check" in body
    assert "Target run prerequisites" in body
    assert "English run prerequisites" in body


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/check-languages", "Domain is required."),
        ("/check-languages?domain=example.com&en_run_id=run-en", "Target run is required."),
        ("/check-languages?domain=example.com&run_id=run-fr", "English reference run is required."),
    ],
)
def test_get_check_languages_missing_input_validation(api_env, path, expected):
    _seed_runs("example.com")

    status, body, _ = _request("GET", api_env, path)
    assert status == HTTPStatus.OK
    assert expected in body


def test_check_languages_not_ready_and_post_refuses_start(api_env):
    domain = "example.com"
    _seed_runs(domain)
    _seed_phase6_prereqs(domain, "run-en", "en")

    status_get, body_get, _ = _request("GET", api_env, f"/check-languages?domain={domain}&run_id=run-fr&en_run_id=run-en")
    assert status_get == HTTPStatus.OK
    assert 'Current state: <strong id="checkLanguagesState">not_ready</strong>' in body_get

    form = "domain=example.com&run_id=run-fr&en_run_id=run-en"
    status_post, _, location = _request("POST", api_env, "/check-languages", form, {"Content-Type": "application/x-www-form-urlencoded"})
    assert status_post == HTTPStatus.FOUND
    assert "Prerequisites+are+missing" in location


def test_check_languages_post_starts_async_phase6_job(api_env, monkeypatch):
    domain = "example.com"
    _seed_runs(domain)
    _seed_phase6_prereqs(domain, "run-fr", "fr")
    _seed_phase6_prereqs(domain, "run-en", "en")

    started = {}

    def _fake_run_phase6_async(job_id, domain, run_id, en_run_id):
        started["job_id"] = job_id
        started["args"] = (domain, run_id, en_run_id)

    monkeypatch.setattr("app.skeleton_server._run_phase6_async", _fake_run_phase6_async)

    form = "domain=example.com&run_id=run-fr&en_run_id=run-en"
    status_post, _, location = _request("POST", api_env, "/check-languages", form, {"Content-Type": "application/x-www-form-urlencoded"})
    assert status_post == HTTPStatus.FOUND
    assert "Language+check+started" in location
    assert started["args"] == ("example.com", "run-fr", "run-en")

    runs = storage.read_json_artifact(domain, "manual", "capture_runs.json")
    run = next(row for row in runs["runs"] if row["run_id"] == "run-fr")
    assert any(str(job.get("phase")) == "6" and str(job.get("status")) == "queued" for job in run["jobs"])


def test_check_languages_completed_summary_and_missing_output_states(api_env):
    domain = "example.com"
    _seed_runs(domain)
    _seed_phase6_prereqs(domain, "run-fr", "fr")
    _seed_phase6_prereqs(domain, "run-en", "en")
    _write(domain, "run-fr", "issues.json", [{"id": "1", "category": "TRANSLATION_MISMATCH", "severity": "high", "language": "fr", "state": "baseline"}])
    _write(domain, "manual", "capture_runs.json", {
        "runs": [
            {"run_id": "run-fr", "created_at": "2026-03-10T00:00:00Z", "jobs": [{"job_id": "phase6-run-fr", "phase": "6", "status": "succeeded", "en_run_id": "run-en"}]},
            {"run_id": "run-en", "created_at": "2026-03-11T00:00:00Z", "jobs": []},
        ]
    })

    status_issues, body_issues, _ = _request("GET", api_env, f"/check-languages?domain={domain}&run_id=run-fr&en_run_id=run-en")
    assert status_issues == HTTPStatus.OK
    assert 'Current state: <strong id="checkLanguagesState">completed_with_issues</strong>' in body_issues
    assert "Total: <strong>1</strong>" in body_issues

    _write(domain, "run-fr", "issues.json", [])
    status_zero, body_zero, _ = _request("GET", api_env, f"/check-languages?domain={domain}&run_id=run-fr&en_run_id=run-en")
    assert status_zero == HTTPStatus.OK
    assert 'Current state: <strong id="checkLanguagesState">completed_with_zero_issues</strong>' in body_zero

    from pipeline.storage import artifact_path, _gcs_client

    bucket = _gcs_client().bucket(storage.BUCKET_NAME)
    missing_path = artifact_path(domain, "run-fr", "issues.json")
    bucket._objects.pop((storage.BUCKET_NAME, missing_path), None)
    status_missing, body_missing, _ = _request("GET", api_env, f"/check-languages?domain={domain}&run_id=run-fr&en_run_id=run-en")
    assert status_missing == HTTPStatus.OK
    assert 'Current state: <strong id="checkLanguagesState">completed</strong>' in body_missing
    assert "Job completed but issues.json is missing." in body_missing


def test_check_languages_run_selection_prefers_english_reference(api_env):
    domain = "example.com"
    _write("_system", "manual", "domains.json", {"domains": [domain]})
    _write(domain, "manual", "capture_runs.json", {
        "runs": [
            {"run_id": "run-mixed", "created_at": "2026-03-13T00:00:00Z", "jobs": []},
            {"run_id": "run-ja", "created_at": "2026-03-12T00:00:00Z", "jobs": []},
            {"run_id": "run-en", "created_at": "2026-03-11T00:00:00Z", "jobs": []},
            {"run_id": "run-unknown", "created_at": "2026-03-10T00:00:00Z", "jobs": []},
        ]
    })
    _seed_phase6_prereqs(domain, "run-ja", "ja")
    _seed_phase6_prereqs(domain, "run-en", "en")
    _seed_phase6_prereqs(domain, "run-mixed", "ja")

    status, body, _ = _request("GET", api_env, f"/check-languages?domain={domain}")
    assert status == HTTPStatus.OK
    target_start = body.index('<select id="checkLanguagesRunId" name="run_id">')
    target_end = body.index("</select>", target_start)
    target_html = body[target_start:target_end]
    en_start = body.index('<select id="checkLanguagesEnRunId" name="en_run_id">')
    en_end = body.index("</select>", en_start)
    en_html = body[en_start:en_end]

    assert target_html.index("run-mixed (ja)") < target_html.index("run-en (en)")
    assert target_html.index("run-ja (ja)") < target_html.index("run-unknown (unknown)")
    assert en_html.index("run-en (en)") < en_html.index("run-mixed (ja)")
    assert en_html.index("run-en (en)") < en_html.index("run-unknown (unknown)")

    form = "domain=example.com&run_id=run-en&en_run_id=run-en"
    status_post, _, location = _request("POST", api_env, "/check-languages", form, {"Content-Type": "application/x-www-form-urlencoded"})
    assert status_post == HTTPStatus.FOUND
    parsed = parse_qs(urlparse(location).query)
    assert parsed["message"][0].startswith("Target run and English reference run must be different")


def test_check_languages_failed_latest_job_marks_existing_summary_as_stale(api_env):
    domain = "example.com"
    _seed_runs(domain)
    _seed_phase6_prereqs(domain, "run-fr", "fr")
    _seed_phase6_prereqs(domain, "run-en", "en")
    _write(domain, "run-fr", "issues.json", [{"id": "1", "category": "TRANSLATION_MISMATCH", "confidence": 0.95, "language": "fr", "state": "baseline"}])
    _write(domain, "manual", "capture_runs.json", {
        "runs": [
            {"run_id": "run-fr", "created_at": "2026-03-10T00:00:00Z", "jobs": [{"job_id": "phase6-run-fr-old", "phase": "6", "status": "succeeded", "en_run_id": "run-en"}, {"job_id": "phase6-run-fr-new", "phase": "6", "status": "failed", "en_run_id": "run-en", "updated_at": "2026-03-11T01:00:00Z"}]},
            {"run_id": "run-en", "created_at": "2026-03-11T00:00:00Z", "jobs": []},
        ]
    })

    status, body, _ = _request("GET", api_env, f"/check-languages?domain={domain}&run_id=run-fr&en_run_id=run-en")
    assert status == HTTPStatus.OK
    assert 'Current state: <strong id="checkLanguagesState">failed</strong>' in body
    assert "Total: <strong>1</strong>" in body
    assert "By severity: high: 1" in body
    assert "may be stale from a previous successful run" in body
