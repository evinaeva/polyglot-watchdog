import http.client
import json
import threading
from http import HTTPStatus
from http.server import ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import pytest

from app.skeleton_server import SkeletonHandler
from pipeline import storage

SUPPORTED_MAIN_DOMAIN = "https://bongacams.com/"
SUPPORTED_TEST_DOMAIN = "https://evinaeva.github.io/polyglot-watchdog-testsite/en/index.html"
SUPPORTED_TEST_DOMAIN_TEST_PAGE = "https://evinaeva.github.io/polyglot-watchdog-testsite/en/test.html"
LEGACY_TESTSITE_ROOT_DOMAIN = "https://evinaeva.github.io/"


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


def _query(params: dict[str, str]) -> str:
    from urllib.parse import urlencode

    return urlencode(params)


def _seed_pages(domain: str, run_id: str, language: str, rows: list[dict] | None = None):
    if rows is None:
        rows = [{"page_id": "p1", "language": language, "url": "https://example.com", "viewport_kind": "desktop", "state": "baseline", "user_tier": "guest"}]
    _write(domain, run_id, "page_screenshots.json", rows)




def _seed_phase6_prereqs(domain: str, run_id: str, language: str = "en"):
    _seed_pages(domain, run_id, language)
    _write(domain, run_id, "collected_items.json", [{"item_id": "i1", "page_id": "p1", "language": language}])
    _write(domain, run_id, "eligible_dataset.json", [{"item_id": "i1", "language": language, "url": "https://example.com"}])


def test_get_check_languages_renders_new_inputs(api_env):
    domain = SUPPORTED_MAIN_DOMAIN
    _seed_runs(domain)
    _seed_pages(domain, "run-en", "en")
    _seed_pages(domain, "run-fr-old", "fr")

    status, body, _ = _request("GET", api_env, f"/check-languages?domain={domain}")
    assert status == HTTPStatus.OK
    assert 'name="en_run_id"' in body
    assert 'name="target_language"' in body
    assert 'name="selected_domain"' in body
    assert '<option value="https://bongacams.com/"' in body
    assert '<option value="https://bongamodels.com/"' in body
    assert '<option value="https://bongacash.com/"' in body
    assert '<option value="https://evinaeva.github.io/polyglot-watchdog-testsite/en/index.html"' in body
    assert 'name="run_id"' not in body


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/check-languages", "Domain is required."),
        ("/check-languages?selected_domain=https%3A%2F%2Fbongacams.com%2F&target_language=fr", "English reference run is required."),
        ("/check-languages?selected_domain=https%3A%2F%2Fbongacams.com%2F&en_run_id=run-en", "Target language is required."),
    ],
)
def test_get_check_languages_missing_input_validation(api_env, path, expected):
    _seed_runs(SUPPORTED_MAIN_DOMAIN)
    _seed_pages(SUPPORTED_MAIN_DOMAIN, "run-en", "en")
    status, body, _ = _request("GET", api_env, path)
    assert status == HTTPStatus.OK
    assert expected in body


def test_post_rejects_non_english_reference(api_env):
    domain = SUPPORTED_MAIN_DOMAIN
    _seed_runs(domain)
    _seed_pages(domain, "run-en", "en")
    _seed_pages(domain, "run-fr-old", "fr")

    form = _query({"selected_domain": domain, "en_run_id": "run-fr-old", "target_language": "ja"})
    status_post, _, location = _request("POST", api_env, "/check-languages", form, {"Content-Type": "application/x-www-form-urlencoded"})
    assert status_post == HTTPStatus.FOUND
    assert "not+English-only" in location


def test_post_starts_composed_async_workflow(api_env, monkeypatch):
    domain = SUPPORTED_MAIN_DOMAIN
    _seed_runs(domain)
    _seed_phase6_prereqs(domain, "run-en", "en")
    _seed_pages(domain, "run-fr-old", "fr")

    started = {}

    def _fake_run(job_id, domain, en_run_id, target_language, target_run_id, target_url):
        started["args"] = (job_id, domain, en_run_id, target_language, target_run_id, target_url)

    monkeypatch.setattr("app.skeleton_server._run_check_languages_async", _fake_run)

    form = _query({"selected_domain": domain, "en_run_id": "run-en", "target_language": "fr"})
    status_post, _, location = _request("POST", api_env, "/check-languages", form, {"Content-Type": "application/x-www-form-urlencoded"})
    assert status_post == HTTPStatus.FOUND
    parsed = parse_qs(urlparse(location).query)
    assert parsed["message"][0] == "Language check started."
    assert parsed["target_run_id"][0].startswith("run-en-check-fr")
    assert started["args"][1:] == (domain, "run-en", "fr", parsed["target_run_id"][0], "https://fr.bongacams.com/")

    runs = storage.read_json_artifact(domain, "manual", "capture_runs.json")
    run = next(row for row in runs["runs"] if row["run_id"] == parsed["target_run_id"][0])
    assert any(job.get("type") == "check_languages" and job.get("status") == "queued" and job.get("target_url") == "https://fr.bongacams.com/" for job in run["jobs"])


def test_duplicate_in_progress_guard(api_env):
    domain = SUPPORTED_MAIN_DOMAIN
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

    form = _query({"selected_domain": domain, "en_run_id": "run-en", "target_language": "fr"})
    status_post, _, location = _request("POST", api_env, "/check-languages", form, {"Content-Type": "application/x-www-form-urlencoded"})
    assert status_post == HTTPStatus.FOUND
    assert "already+in+progress" in location


def test_duplicate_guard_ignores_stale_running_job(api_env, monkeypatch):
    domain = SUPPORTED_MAIN_DOMAIN
    _seed_runs(domain)
    _seed_phase6_prereqs(domain, "run-en", "en")
    _seed_pages(domain, "run-fr-old", "fr")
    _write(domain, "manual", "capture_runs.json", {
        "runs": [
            {
                "run_id": "run-en-check-fr",
                "created_at": "2026-03-12T00:00:00Z",
                "jobs": [
                    {
                        "job_id": "check-languages-run-en-check-fr-1",
                        "status": "running",
                        "type": "check_languages",
                        "en_run_id": "run-en",
                        "target_language": "fr",
                        "updated_at": "2000-01-01T00:00:00Z",
                        "created_at": "2000-01-01T00:00:00Z",
                    }
                ],
            },
            {"run_id": "run-en", "created_at": "2026-03-11T00:00:00Z", "jobs": []},
        ]
    })
    monkeypatch.setenv("WORKFLOW_STALE_JOB_SECONDS", "30")

    form = _query({"selected_domain": domain, "en_run_id": "run-en", "target_language": "fr"})
    status_post, _, location = _request("POST", api_env, "/check-languages", form, {"Content-Type": "application/x-www-form-urlencoded"})
    assert status_post == HTTPStatus.FOUND
    assert "Language+check+started." in location


def test_completed_state_shows_target_run_and_summary(api_env):
    domain = SUPPORTED_MAIN_DOMAIN
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
    domain = SUPPORTED_MAIN_DOMAIN
    _seed_runs(domain)
    _seed_pages(domain, "run-en", "en")

    status, body, _ = _request("GET", api_env, f"/check-languages?domain={domain}")
    assert status == HTTPStatus.OK
    assert '<option value="fr"' in body




def test_get_check_languages_default_selects_latest_first_run_display_name(api_env):
    domain = SUPPORTED_MAIN_DOMAIN
    _write("_system", "manual", "domains.json", {"domains": [domain]})
    _write(domain, "manual", "capture_runs.json", {
        "runs": [
            {"run_id": "run-en-latest", "created_at": "2026-03-13T00:00:00Z", "display_name": "Nightly EN", "jobs": []},
            {"run_id": "run-en-first", "created_at": "2026-03-12T00:00:00Z", "display_name": "First_run_10:00|12.03.2026", "jobs": []},
            {"run_id": "run-en-first-old", "created_at": "2026-03-11T00:00:00Z", "display_name": "First_run_10:00|11.03.2026", "jobs": []},
        ]
    })
    _seed_phase6_prereqs(domain, "run-en-first", "en")
    _seed_phase6_prereqs(domain, "run-en-latest", "en")

    status, body, _ = _request("GET", api_env, f"/check-languages?domain={domain}")
    assert status == HTTPStatus.OK
    assert '<option value="run-en-first" selected="selected">First_run_10:00|12.03.2026</option>' in body


def test_get_check_languages_en_dropdown_excludes_mixed_language_runs(api_env):
    domain = SUPPORTED_MAIN_DOMAIN
    _write("_system", "manual", "domains.json", {"domains": [domain]})
    _write(domain, "manual", "capture_runs.json", {
        "runs": [
            {"run_id": "run-mixed", "created_at": "2026-03-12T00:00:00Z", "display_name": "First_run_10:00|12.03.2026", "jobs": []},
            {"run_id": "run-en", "created_at": "2026-03-11T00:00:00Z", "display_name": "First_run_10:00|11.03.2026", "jobs": []},
            {"run_id": "run-fr", "created_at": "2026-03-10T00:00:00Z", "jobs": []},
        ]
    })
    _seed_pages(domain, "run-mixed", rows=[
        {"page_id": "p1", "language": "en", "url": "https://example.com/en", "viewport_kind": "desktop", "state": "baseline"},
        {"page_id": "p2", "language": "fr", "url": "https://example.com/fr", "viewport_kind": "desktop", "state": "baseline"},
    ], language="en")
    _seed_phase6_prereqs(domain, "run-en", "en")
    _seed_pages(domain, "run-fr", "fr")

    status, body, _ = _request("GET", api_env, f"/check-languages?domain={domain}")
    assert status == HTTPStatus.OK
    assert '<option value="run-mixed"' not in body
    assert '<option value="run-en" selected="selected">First_run_10:00|11.03.2026</option>' in body


def test_get_check_languages_en_dropdown_shows_no_runs_placeholder(api_env):
    domain = SUPPORTED_MAIN_DOMAIN
    _write("_system", "manual", "domains.json", {"domains": [domain]})
    _write(domain, "manual", "capture_runs.json", {
        "runs": [
            {"run_id": "run-fr", "created_at": "2026-03-10T00:00:00Z", "jobs": []},
        ]
    })
    _seed_pages(domain, "run-fr", "fr")

    status, body, _ = _request("GET", api_env, f"/check-languages?domain={domain}")
    assert status == HTTPStatus.OK
    assert '<option value="">No English runs found</option>' in body



def test_get_check_languages_default_prefers_latest_explicit_en_standard(api_env):
    domain = SUPPORTED_MAIN_DOMAIN
    _write("_system", "manual", "domains.json", {"domains": [domain]})
    _write(domain, "manual", "capture_runs.json", {
        "runs": [
            {"run_id": "run-first-newer", "created_at": "2026-03-13T00:00:00Z", "display_name": "First_run_10:00|13.03.2026", "jobs": []},
            {"run_id": "run-en-standard", "created_at": "2026-03-12T00:00:00Z", "en_standard_display_name": "EN Standard (Mar 12)", "jobs": []},
        ]
    })
    _seed_phase6_prereqs(domain, "run-first-newer", "en")
    _seed_phase6_prereqs(domain, "run-en-standard", "en")

    status, body, _ = _request("GET", api_env, f"/check-languages?domain={domain}")
    assert status == HTTPStatus.OK
    assert '<option value="run-en-standard" selected="selected">EN Standard (Mar 12)</option>' in body

def test_get_check_languages_auto_selects_latest_successful_english_standard(api_env):
    domain = SUPPORTED_MAIN_DOMAIN
    _write("_system", "manual", "domains.json", {"domains": [domain]})
    _write(domain, "manual", "capture_runs.json", {
        "runs": [
            {"run_id": "run-en-old", "created_at": "2026-03-10T00:00:00Z", "jobs": []},
            {"run_id": "run-en-latest-ready", "created_at": "2026-03-12T00:00:00Z", "jobs": []},
            {"run_id": "run-fr", "created_at": "2026-03-11T00:00:00Z", "jobs": []},
        ]
    })
    _seed_phase6_prereqs(domain, "run-en-old", "en")
    _seed_phase6_prereqs(domain, "run-en-latest-ready", "en")
    _seed_pages(domain, "run-fr", "fr")

    status, body, _ = _request("GET", api_env, f"/check-languages?domain={domain}")
    assert status == HTTPStatus.OK
    assert '<option value="run-en-latest-ready" selected="selected">' in body
    assert "English reference run is required." not in body
    assert "Target language is required." not in body


def test_get_check_languages_auto_selects_en_standard_success_marker_when_not_ready(api_env):
    domain = SUPPORTED_MAIN_DOMAIN
    _write("_system", "manual", "domains.json", {"domains": [domain]})
    _write(domain, "manual", "capture_runs.json", {
        "runs": [
            {
                "run_id": "run-en-marker",
                "created_at": "2026-03-12T00:00:00Z",
                "metadata": {"en_standard_status": "succeeded"},
                "jobs": [],
            },
            {"run_id": "run-fr", "created_at": "2026-03-11T00:00:00Z", "jobs": []},
        ]
    })
    _seed_pages(domain, "run-en-marker", "en")
    _seed_pages(domain, "run-fr", "fr")

    status, body, _ = _request("GET", api_env, f"/check-languages?domain={domain}&target_language=fr")
    assert status == HTTPStatus.OK
    assert '<option value="run-en-marker" selected="selected">' in body
    assert "English reference run is not ready for comparison prerequisites." in body


def test_get_check_languages_en_option_uses_metadata_display_label(api_env):
    domain = SUPPORTED_MAIN_DOMAIN
    _write("_system", "manual", "domains.json", {"domains": [domain]})
    _write(domain, "manual", "capture_runs.json", {
        "runs": [
            {"run_id": "run-en", "created_at": "2026-03-11T00:00:00Z", "metadata": {"display_label": "EN Baseline (March 11)"}, "jobs": []},
            {"run_id": "run-fr", "created_at": "2026-03-10T00:00:00Z", "jobs": []},
        ]
    })
    _seed_phase6_prereqs(domain, "run-en", "en")
    _seed_pages(domain, "run-fr", "fr")

    status, body, _ = _request("GET", api_env, f"/check-languages?domain={domain}")
    assert status == HTTPStatus.OK
    assert '<option value="run-en" selected="selected">EN Baseline (March 11)</option>' in body


def test_get_check_languages_en_option_uses_metadata_display_name(api_env):
    domain = SUPPORTED_MAIN_DOMAIN
    _write("_system", "manual", "domains.json", {"domains": [domain]})
    _write(domain, "manual", "capture_runs.json", {
        "runs": [
            {"run_id": "run-en", "created_at": "2026-03-11T00:00:00Z", "metadata": {"display_name": "EN Baseline Display Name"}, "jobs": []},
            {"run_id": "run-fr", "created_at": "2026-03-10T00:00:00Z", "jobs": []},
        ]
    })
    _seed_phase6_prereqs(domain, "run-en", "en")
    _seed_pages(domain, "run-fr", "fr")

    status, body, _ = _request("GET", api_env, f"/check-languages?domain={domain}")
    assert status == HTTPStatus.OK
    assert '<option value="run-en" selected="selected">EN Baseline Display Name</option>' in body


def test_post_rejects_when_english_reference_not_phase6_ready(api_env):
    domain = SUPPORTED_MAIN_DOMAIN
    _seed_runs(domain)
    _seed_pages(domain, "run-en", "en")

    form = _query({"selected_domain": domain, "en_run_id": "run-en", "target_language": "fr"})
    status_post, _, location = _request("POST", api_env, "/check-languages", form, {"Content-Type": "application/x-www-form-urlencoded"})
    assert status_post == HTTPStatus.FOUND
    assert "not+ready+for+comparison+prerequisites" in location


def test_queued_state_is_rendered_as_queued(api_env):
    domain = SUPPORTED_MAIN_DOMAIN
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


@pytest.mark.parametrize(
    ("selected_domain", "language", "expected"),
    [
        ("https://bongacams.com/", "de", "https://de.bongacams.com/"),
        ("https://bongamodels.com/", "de", "https://de.bongamodels.com/"),
        ("https://bongacash.com/", "de", "https://de.bongacash.com/"),
        (
            "https://evinaeva.github.io/polyglot-watchdog-testsite/en/index.html",
            "de",
            "https://evinaeva.github.io/polyglot-watchdog-testsite/de/index.html",
        ),
        (
            "https://evinaeva.github.io/polyglot-watchdog-testsite/en/test.html",
            "de",
            "https://evinaeva.github.io/polyglot-watchdog-testsite/de/test.html",
        ),
        (
            "https://evinaeva.github.io/polyglot-watchdog-testsite/en/pricing.html",
            "ru",
            "https://evinaeva.github.io/polyglot-watchdog-testsite/ru/pricing.html",
        ),
    ],
)
def test_target_url_generation_for_supported_domains(selected_domain, language, expected):
    from app.skeleton_server import _build_check_languages_target_url

    assert _build_check_languages_target_url(selected_domain, language) == expected


def test_target_url_generation_rejects_unsupported_domain():
    from app.skeleton_server import _build_check_languages_target_url

    with pytest.raises(ValueError, match="unsupported"):
        _build_check_languages_target_url("https://unsupported.example/", "de")


def test_testsite_root_alias_normalizes_to_canonical():
    from app.skeleton_server import _normalize_check_languages_domain

    assert _normalize_check_languages_domain(LEGACY_TESTSITE_ROOT_DOMAIN) == SUPPORTED_TEST_DOMAIN


def test_post_rejects_unsupported_domain(api_env):
    _seed_runs(SUPPORTED_MAIN_DOMAIN)
    _seed_phase6_prereqs(SUPPORTED_MAIN_DOMAIN, "run-en", "en")
    form = _query({"selected_domain": "https://unsupported.example/", "en_run_id": "run-en", "target_language": "fr"})
    status_post, _, location = _request("POST", api_env, "/check-languages", form, {"Content-Type": "application/x-www-form-urlencoded"})
    assert status_post == HTTPStatus.FOUND
    assert "Selected+domain+is+unsupported." in location


def test_get_accepts_github_pages_project_site_domain_pattern(api_env):
    domain = SUPPORTED_TEST_DOMAIN_TEST_PAGE
    _seed_runs(domain)
    _seed_phase6_prereqs(domain, "run-en", "en")
    _seed_pages(domain, "run-fr-old", "fr")

    status, body, _ = _request("GET", api_env, f"/check-languages?domain={domain}&en_run_id=run-en&target_language=de")
    assert status == HTTPStatus.OK
    assert "Selected domain is unsupported." not in body
    assert "Selected English reference run is invalid for this domain." not in body
    assert '<option value="de" selected="selected">' in body


def test_post_with_legacy_root_writes_under_canonical_domain(api_env, monkeypatch):
    _seed_runs(SUPPORTED_TEST_DOMAIN)
    _seed_phase6_prereqs(SUPPORTED_TEST_DOMAIN, "run-en", "en")

    started = {}

    def _fake_run(job_id, domain, en_run_id, target_language, target_run_id, target_url):
        started["args"] = (job_id, domain, en_run_id, target_language, target_run_id, target_url)

    monkeypatch.setattr("app.skeleton_server._run_check_languages_async", _fake_run)

    form = _query({"selected_domain": LEGACY_TESTSITE_ROOT_DOMAIN, "en_run_id": "run-en", "target_language": "de"})
    status_post, _, location = _request("POST", api_env, "/check-languages", form, {"Content-Type": "application/x-www-form-urlencoded"})
    assert status_post == HTTPStatus.FOUND
    parsed = parse_qs(urlparse(location).query)
    assert parsed["selected_domain"][0] == SUPPORTED_TEST_DOMAIN
    assert started["args"][1] == SUPPORTED_TEST_DOMAIN
    runs = storage.read_json_artifact(SUPPORTED_TEST_DOMAIN, "manual", "capture_runs.json")
    assert any(str(row.get("run_id", "")).startswith("run-en-check-de") for row in runs["runs"])


def test_check_languages_discovers_legacy_runs_from_canonical_testsite_domain(api_env):
    _write("_system", "manual", "domains.json", {"domains": [SUPPORTED_TEST_DOMAIN, LEGACY_TESTSITE_ROOT_DOMAIN]})
    _write(LEGACY_TESTSITE_ROOT_DOMAIN, "manual", "capture_runs.json", {"runs": [{"run_id": "run-en-legacy", "created_at": "2026-03-01T00:00:00Z", "jobs": []}]})
    _seed_phase6_prereqs(LEGACY_TESTSITE_ROOT_DOMAIN, "run-en-legacy", "en")

    status, body, _ = _request("GET", api_env, f"/check-languages?domain={SUPPORTED_TEST_DOMAIN}")
    assert status == HTTPStatus.OK
    assert "Selected domain is unsupported." not in body
    assert '<option value="run-en-legacy"' in body


def test_en_run_under_index_visible_when_opening_test_page(api_env):
    _seed_runs(SUPPORTED_TEST_DOMAIN)
    _seed_phase6_prereqs(SUPPORTED_TEST_DOMAIN, "run-en", "en")
    _seed_pages(SUPPORTED_TEST_DOMAIN, "run-fr-old", "fr")
    _write("_system", "manual", "domains.json", {"domains": [SUPPORTED_TEST_DOMAIN, SUPPORTED_TEST_DOMAIN_TEST_PAGE]})

    status, body, _ = _request("GET", api_env, f"/check-languages?domain={SUPPORTED_TEST_DOMAIN_TEST_PAGE}")
    assert status == HTTPStatus.OK
    assert '<option value="run-en"' in body
    assert "Selected English reference run is invalid for this domain." not in body


def test_en_run_under_test_page_visible_when_opening_index_page(api_env):
    _seed_runs(SUPPORTED_TEST_DOMAIN_TEST_PAGE)
    _seed_phase6_prereqs(SUPPORTED_TEST_DOMAIN_TEST_PAGE, "run-en", "en")
    _seed_pages(SUPPORTED_TEST_DOMAIN_TEST_PAGE, "run-fr-old", "fr")
    _write("_system", "manual", "domains.json", {"domains": [SUPPORTED_TEST_DOMAIN, SUPPORTED_TEST_DOMAIN_TEST_PAGE]})

    status, body, _ = _request("GET", api_env, f"/check-languages?domain={SUPPORTED_TEST_DOMAIN}")
    assert status == HTTPStatus.OK
    assert '<option value="run-en"' in body
    assert "Selected English reference run is invalid for this domain." not in body


def test_legacy_domains_remain_exact_match_for_run_discovery(api_env):
    _seed_runs("https://bongacams.com/")
    _seed_phase6_prereqs("https://bongacams.com/", "run-en", "en")
    _seed_pages("https://bongacams.com/", "run-fr-old", "fr")
    _write("_system", "manual", "domains.json", {"domains": ["https://bongacams.com/", "https://bongamodels.com/"]})

    status, body, _ = _request("GET", api_env, "/check-languages?domain=https%3A%2F%2Fbongamodels.com%2F")
    assert status == HTTPStatus.OK
    assert '<option value="run-en"' not in body


@pytest.mark.parametrize(
    ("selected_domain", "expected_target_url"),
    [
        ("https://bongacams.com/", "https://de.bongacams.com/"),
        ("https://bongamodels.com/", "https://de.bongamodels.com/"),
        ("https://bongacash.com/", "https://de.bongacash.com/"),
        (
            "https://evinaeva.github.io/polyglot-watchdog-testsite/en/index.html",
            "https://evinaeva.github.io/polyglot-watchdog-testsite/de/index.html",
        ),
    ],
)
def test_post_passes_generated_target_url_into_runtime_execution(api_env, monkeypatch, selected_domain, expected_target_url):
    from app.skeleton_server import _normalize_check_languages_domain

    _seed_runs(selected_domain)
    _seed_phase6_prereqs(selected_domain, "run-en", "en")
    _seed_pages(selected_domain, "run-fr-old", "fr")

    started = {}

    def _fake_run(job_id, domain, en_run_id, target_language, target_run_id, target_url):
        started["args"] = (job_id, domain, en_run_id, target_language, target_run_id, target_url)

    monkeypatch.setattr("app.skeleton_server._run_check_languages_async", _fake_run)

    form = _query({"selected_domain": selected_domain, "en_run_id": "run-en", "target_language": "de"})
    status_post, _, location = _request("POST", api_env, "/check-languages", form, {"Content-Type": "application/x-www-form-urlencoded"})
    assert status_post == HTTPStatus.FOUND
    assert started["args"][1] == _normalize_check_languages_domain(selected_domain)
    assert started["args"][2] == "run-en"
    assert started["args"][3] == "de"
    assert started["args"][5] == expected_target_url

    parsed = parse_qs(urlparse(location).query)
    assert parsed["generated_target_url"][0] == expected_target_url


def test_post_preserves_selected_domain_and_language_and_shows_generated_target_url(api_env, monkeypatch):
    domain = SUPPORTED_TEST_DOMAIN
    _seed_runs(domain)
    _seed_phase6_prereqs(domain, "run-en", "en")
    _seed_pages(domain, "run-fr-old", "fr")
    monkeypatch.setattr("app.skeleton_server._run_check_languages_async", lambda *args, **kwargs: None)

    form = _query({"selected_domain": domain, "en_run_id": "run-en", "target_language": "de"})
    status_post, _, location = _request("POST", api_env, "/check-languages", form, {"Content-Type": "application/x-www-form-urlencoded"})
    assert status_post == HTTPStatus.FOUND

    status_get, body, _ = _request("GET", api_env, location)
    assert status_get == HTTPStatus.OK
    assert f'<option value="{domain}" selected="selected">' in body
    assert '<option value="de" selected="selected">' in body
    assert "Generated target URL: <code>https://evinaeva.github.io/polyglot-watchdog-testsite/de/index.html</code>" in body
    assert "Target language is required." not in body


def test_post_prefers_non_empty_target_language_when_duplicate_form_values(api_env, monkeypatch):
    domain = SUPPORTED_TEST_DOMAIN
    _seed_runs(domain)
    _seed_phase6_prereqs(domain, "run-en", "en")
    _seed_pages(domain, "run-fr-old", "fr")
    monkeypatch.setattr("app.skeleton_server._run_check_languages_async", lambda *args, **kwargs: None)

    form = "selected_domain=https%3A%2F%2Fevinaeva.github.io%2Fpolyglot-watchdog-testsite%2Fen%2Findex.html&en_run_id=run-en&target_language=&target_language=de"
    status_post, _, location = _request("POST", api_env, "/check-languages", form, {"Content-Type": "application/x-www-form-urlencoded"})
    assert status_post == HTTPStatus.FOUND
    assert "Target+language+is+required." not in location
    assert "target_language=de" in location

    status_get, body, _ = _request("GET", api_env, location)
    assert status_get == HTTPStatus.OK
    assert "Target language: <code>de</code>" in body
    assert "Generated target URL: <code>https://evinaeva.github.io/polyglot-watchdog-testsite/de/index.html</code>" in body


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

    jobs = _replay_scope_from_reference_run("https://bongacams.com/", "run-en", "ja", "https://ja.bongacams.com/")
    assert len(jobs) == 2
    assert calls == [
        ("https://bongacams.com/", "https://ja.bongacams.com/a", "ja", "desktop", "baseline", "guest"),
        ("https://bongacams.com/", "https://ja.bongacams.com/a", "ja", "desktop", "checkout", "pro"),
    ]


def test_replay_scope_helper_rewrites_github_pages_language_segment_only(monkeypatch):
    domain = "https://evinaeva.github.io/polyglot-watchdog-testsite/en/index.html"
    pages = [
        {"url": "https://evinaeva.github.io/polyglot-watchdog-testsite/en/index.html", "language": "en", "viewport_kind": "desktop", "state": "baseline", "user_tier": "guest"},
        {"url": "https://evinaeva.github.io/polyglot-watchdog-testsite/en/test.html", "language": "en", "viewport_kind": "desktop", "state": "checkout", "user_tier": "pro"},
    ]
    monkeypatch.setattr("app.skeleton_server._read_list_artifact_required", lambda _domain, _run_id, _filename: pages)

    calls = []

    def _fake_build(domain, url, language, viewport_kind, state, user_tier):
        calls.append((domain, url, language, viewport_kind, state, user_tier))
        return {"ctx": (url, viewport_kind, state, user_tier)}

    monkeypatch.setattr("pipeline.run_phase1.build_exact_context_job", _fake_build)

    from app.skeleton_server import _replay_scope_from_reference_run

    jobs = _replay_scope_from_reference_run(
        domain,
        "run-en",
        "de",
        "https://evinaeva.github.io/polyglot-watchdog-testsite/de/index.html",
    )
    assert len(jobs) == 2
    assert calls == [
        (domain, "https://evinaeva.github.io/polyglot-watchdog-testsite/de/index.html", "de", "desktop", "baseline", "guest"),
        (domain, "https://evinaeva.github.io/polyglot-watchdog-testsite/de/test.html", "de", "desktop", "checkout", "pro"),
    ]


def test_replay_scope_helper_treats_null_recipe_fields_as_not_applicable(monkeypatch):
    pages = [
        {
            "url": "https://example.com/a",
            "language": "en",
            "viewport_kind": "desktop",
            "state": "baseline",
            "user_tier": "guest",
            "recipe_id": None,
            "capture_point_id": None,
        }
    ]
    monkeypatch.setattr("app.skeleton_server._read_list_artifact_required", lambda _domain, _run_id, _filename: pages)

    calls = []

    def _fake_build(domain, url, language, viewport_kind, state, user_tier, recipe_id=None, capture_point_id=None):
        calls.append((domain, url, language, viewport_kind, state, user_tier, recipe_id, capture_point_id))
        return {"ctx": (url, viewport_kind, state, user_tier)}

    monkeypatch.setattr("pipeline.run_phase1.build_exact_context_job", _fake_build)

    from app.skeleton_server import _replay_scope_from_reference_run

    jobs = _replay_scope_from_reference_run("https://bongacams.com/", "run-en", "ja", "https://ja.bongacams.com/")
    assert len(jobs) == 1
    assert calls == [
        ("https://bongacams.com/", "https://ja.bongacams.com/a", "ja", "desktop", "baseline", "guest", None, None),
    ]


def test_orchestrator_runs_capture_then_comparison(monkeypatch):
    calls = []
    monkeypatch.setattr("app.skeleton_server._replay_scope_from_reference_run", lambda d, e, t, u: ["j1", "j2"])

    async def _fake_main(*args, **kwargs):
        calls.append("phase1")

    monkeypatch.setattr("pipeline.run_phase1.main", _fake_main)
    monkeypatch.setattr("pipeline.run_phase3.run", lambda **kwargs: calls.append("phase3"))
    monkeypatch.setattr("pipeline.run_phase6.run", lambda **kwargs: calls.append("phase6"))
    monkeypatch.setattr("app.skeleton_server._require_artifact_exists", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.skeleton_server._upsert_job_status", lambda *args, **kwargs: None)
    monkeypatch.setenv("PHASE6_REVIEW_PROVIDER", "test-heuristic")

    from app.skeleton_server import _run_check_languages_async

    _run_check_languages_async("job1", "https://bongacams.com/", "run-en", "fr", "run-en-check-fr", "https://fr.bongacams.com/")
    assert calls == ["phase1", "phase3", "phase6"]


def test_orchestrator_stops_before_comparison_on_capture_failure(monkeypatch):
    calls = []
    monkeypatch.setattr("app.skeleton_server._replay_scope_from_reference_run", lambda d, e, t, u: ["j1"])

    async def _fake_main(*args, **kwargs):
        calls.append("phase1")
        raise RuntimeError("capture failed")

    monkeypatch.setattr("pipeline.run_phase1.main", _fake_main)
    monkeypatch.setattr("pipeline.run_phase3.run", lambda **kwargs: calls.append("phase3"))
    monkeypatch.setattr("pipeline.run_phase6.run", lambda **kwargs: calls.append("phase6"))
    updates = []
    monkeypatch.setattr("app.skeleton_server._upsert_job_status", lambda d, r, rec: updates.append(rec))

    from app.skeleton_server import _run_check_languages_async

    _run_check_languages_async("job1", "https://bongacams.com/", "run-en", "fr", "run-en-check-fr", "https://fr.bongacams.com/")
    assert calls == ["phase1"]
    assert any(str(rec.get("stage")) == "running_target_capture_failed" for rec in updates)
    assert any(str(rec.get("status")) == "failed" for rec in updates)


def test_orchestrator_fails_when_capture_returns_without_required_artifacts(monkeypatch):
    calls = []
    monkeypatch.setattr("app.skeleton_server._replay_scope_from_reference_run", lambda d, e, t, u: ["j1"])

    async def _fake_main(*args, **kwargs):
        calls.append("phase1")
        return None

    monkeypatch.setattr("pipeline.run_phase1.main", _fake_main)
    monkeypatch.setattr("pipeline.run_phase3.run", lambda **kwargs: calls.append("phase3"))
    monkeypatch.setattr("pipeline.run_phase6.run", lambda **kwargs: calls.append("phase6"))
    monkeypatch.setattr("app.skeleton_server._require_artifact_exists", lambda *args, **kwargs: (_ for _ in ()).throw(FileNotFoundError("page_screenshots.json artifact missing")))
    updates = []
    monkeypatch.setattr("app.skeleton_server._upsert_job_status", lambda d, r, rec: updates.append(rec))

    from app.skeleton_server import _run_check_languages_async

    _run_check_languages_async("job1", "https://bongacams.com/", "run-en", "fr", "run-en-check-fr", "https://fr.bongacams.com/")
    assert calls == ["phase1"]
    failed = [rec for rec in updates if str(rec.get("stage")) == "running_target_capture_failed"]
    assert failed
    assert "artifact missing" in str(failed[-1].get("error", ""))


def test_orchestrator_surfaces_comparison_failure(monkeypatch):
    monkeypatch.setattr("app.skeleton_server._replay_scope_from_reference_run", lambda d, e, t, u: ["j1"])

    async def _fake_main(*args, **kwargs):
        return None

    monkeypatch.setattr("pipeline.run_phase1.main", _fake_main)
    monkeypatch.setattr("pipeline.run_phase3.run", lambda **kwargs: None)
    monkeypatch.setattr("pipeline.run_phase6.run", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("phase6 failed")))
    monkeypatch.setattr("app.skeleton_server._require_artifact_exists", lambda *args, **kwargs: None)
    updates = []
    monkeypatch.setattr("app.skeleton_server._upsert_job_status", lambda d, r, rec: updates.append(rec))

    from app.skeleton_server import _run_check_languages_async

    _run_check_languages_async("job1", "https://bongacams.com/", "run-en", "fr", "run-en-check-fr", "https://fr.bongacams.com/")
    assert any(str(rec.get("stage")) == "running_comparison_failed" for rec in updates)


def test_orchestrator_surfaces_missing_phase6_provider(monkeypatch):
    monkeypatch.setattr("app.skeleton_server._replay_scope_from_reference_run", lambda d, e, t, u: ["j1"])
    monkeypatch.setattr("app.skeleton_server._require_artifact_exists", lambda *args, **kwargs: None)

    async def _fake_main(*args, **kwargs):
        return None

    monkeypatch.setattr("pipeline.run_phase1.main", _fake_main)
    monkeypatch.setattr("pipeline.run_phase3.run", lambda **kwargs: None)
    monkeypatch.setattr("pipeline.run_phase6.run", lambda **kwargs: None)
    monkeypatch.delenv("PHASE6_REVIEW_PROVIDER", raising=False)
    updates = []
    monkeypatch.setattr("app.skeleton_server._upsert_job_status", lambda d, r, rec: updates.append(rec))

    from app.skeleton_server import _run_check_languages_async

    _run_check_languages_async("job1", "https://bongacams.com/", "run-en", "fr", "run-en-check-fr", "https://fr.bongacams.com/")
    failed = [rec for rec in updates if str(rec.get("stage")) == "running_comparison_failed"]
    assert failed
    assert "PHASE6_REVIEW_PROVIDER is required" in str(failed[-1].get("error", ""))


def test_stale_check_languages_job_is_rendered_as_failed(api_env, monkeypatch):
    domain = SUPPORTED_MAIN_DOMAIN
    _seed_runs(domain)
    _seed_phase6_prereqs(domain, "run-en", "en")
    _seed_pages(domain, "run-en-check-fr", "fr")
    _write(domain, "manual", "capture_runs.json", {
        "runs": [
            {
                "run_id": "run-en-check-fr",
                "created_at": "2026-03-12T00:00:00Z",
                "jobs": [
                    {
                        "job_id": "check-languages-1",
                        "status": "running",
                        "type": "check_languages",
                        "stage": "running_target_capture",
                        "en_run_id": "run-en",
                        "target_language": "fr",
                        "updated_at": "2000-01-01T00:00:00Z",
                        "created_at": "2000-01-01T00:00:00Z",
                    }
                ],
            },
            {"run_id": "run-en", "created_at": "2026-03-11T00:00:00Z", "jobs": []},
        ]
    })
    monkeypatch.setenv("WORKFLOW_STALE_JOB_SECONDS", "30")

    status, body, _ = _request("GET", api_env, f"/check-languages?domain={domain}&en_run_id=run-en&target_language=fr&target_run_id=run-en-check-fr")
    assert status == HTTPStatus.OK
    assert 'Current state: <strong id="checkLanguagesState">failed</strong>' in body
    assert "capture worker stale: no completion heartbeat" in body


def test_llm_review_state_missing_telemetry_in_progress(api_env):
    domain = SUPPORTED_MAIN_DOMAIN
    _seed_runs(domain)
    _seed_phase6_prereqs(domain, "run-en", "en")
    _seed_pages(domain, "run-en-check-fr", "fr")
    _write(domain, "manual", "capture_runs.json", {
        "runs": [
            {
                "run_id": "run-en-check-fr",
                "created_at": "2026-03-12T00:00:00Z",
                "jobs": [
                    {
                        "job_id": "check-languages-1",
                        "status": "running",
                        "type": "check_languages",
                        "stage": "running_comparison",
                        "en_run_id": "run-en",
                        "target_language": "fr",
                    }
                ],
            },
            {"run_id": "run-en", "created_at": "2026-03-11T00:00:00Z", "jobs": []},
        ]
    })

    status, body, _ = _request("GET", api_env, f"/check-languages?domain={domain}&en_run_id=run-en&target_language=fr&target_run_id=run-en-check-fr")
    assert status == HTTPStatus.OK
    assert "LLM review not reached yet" in body


def test_llm_review_state_missing_telemetry_completed(api_env):
    domain = SUPPORTED_MAIN_DOMAIN
    _seed_runs(domain)
    _seed_phase6_prereqs(domain, "run-en", "en")
    _seed_pages(domain, "run-en-check-fr", "fr")
    _write(domain, "manual", "capture_runs.json", {
        "runs": [
            {
                "run_id": "run-en-check-fr",
                "created_at": "2026-03-12T00:00:00Z",
                "jobs": [
                    {
                        "job_id": "check-languages-1",
                        "status": "succeeded",
                        "type": "check_languages",
                        "stage": "completed",
                        "en_run_id": "run-en",
                        "target_language": "fr",
                    }
                ],
            },
            {"run_id": "run-en", "created_at": "2026-03-11T00:00:00Z", "jobs": []},
        ]
    })

    status, body, _ = _request("GET", api_env, f"/check-languages?domain={domain}&en_run_id=run-en&target_language=fr&target_run_id=run-en-check-fr")
    assert status == HTTPStatus.OK
    assert "LLM telemetry missing" in body


def test_llm_review_telemetry_renders_request_and_cost_priority(api_env):
    domain = SUPPORTED_MAIN_DOMAIN
    _seed_runs(domain)
    _seed_phase6_prereqs(domain, "run-en", "en")
    _seed_pages(domain, "run-en-check-fr", "fr")
    _write(domain, "run-en-check-fr", "llm_review_stats.json", {
        "llm_requested": False,
        "batches_attempted": 2,
        "batches_succeeded": 0,
        "batches_failed": 2,
        "fallback_batches": 2,
        "fallback_items": 8,
        "estimated_tokens": {"prompt": 100, "completion": 20, "total": 120},
        "actual_tokens": {"prompt": 90, "completion": 10, "total": 100},
        "estimated_cost_usd": 0.12,
    })
    _write(domain, "manual", "capture_runs.json", {
        "runs": [
            {
                "run_id": "run-en-check-fr",
                "created_at": "2026-03-12T00:00:00Z",
                "jobs": [
                    {
                        "job_id": "check-languages-1",
                        "status": "succeeded",
                        "type": "check_languages",
                        "stage": "completed",
                        "en_run_id": "run-en",
                        "target_language": "fr",
                    }
                ],
            },
            {"run_id": "run-en", "created_at": "2026-03-11T00:00:00Z", "jobs": []},
        ]
    })

    status, body, _ = _request("GET", api_env, f"/check-languages?domain={domain}&en_run_id=run-en&target_language=fr&target_run_id=run-en-check-fr")
    assert status == HTTPStatus.OK
    assert "no real LLM request was sent" in body
    assert "Fallback status: Full fallback" in body
    assert "$0.120000 (estimated)" in body
