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


def _llm_review_stats_payload(
    *,
    llm_requested: bool = True,
    review_mode: str = "llm",
    configured_provider: str = "llm",
    configured_model: str = "openrouter/free",
    effective_model: str = "openrouter/free",
    llm_batches_attempted: int = 1,
    llm_batches_succeeded: int = 1,
    llm_batches_failed: int = 0,
    fallback_batches: int = 0,
    fallback_items: int = 0,
    used_fallback: bool = False,
    responses_received: int = 1,
    estimated_prompt_tokens: int = 120,
    estimated_completion_tokens: int = 30,
    estimated_total_tokens: int = 150,
    actual_prompt_tokens: int | None = 118,
    actual_completion_tokens: int | None = 28,
    actual_total_tokens: int | None = 146,
    actual_cost_usd: float | None = 0.0012,
) -> dict:
    return {
        "review_mode": review_mode,
        "provider_type": "llm",
        "configured_provider": configured_provider,
        "configured_model": configured_model,
        "effective_model": effective_model,
        "llm_requested": llm_requested,
        "llm_batches_attempted": llm_batches_attempted,
        "llm_batches_succeeded": llm_batches_succeeded,
        "llm_batches_failed": llm_batches_failed,
        "fallback_batches": fallback_batches,
        "fallback_items": fallback_items,
        "used_fallback": used_fallback,
        "responses_received": responses_received,
        "estimated_prompt_tokens": estimated_prompt_tokens,
        "estimated_completion_tokens": estimated_completion_tokens,
        "estimated_total_tokens": estimated_total_tokens,
        "actual_prompt_tokens": actual_prompt_tokens,
        "actual_completion_tokens": actual_completion_tokens,
        "actual_total_tokens": actual_total_tokens,
        "actual_cost_usd": actual_cost_usd,
        "batches": [],
    }


def _llm_review_stats_completed_payload() -> dict:
    return _llm_review_stats_payload()


def _llm_review_stats_partial_fallback_payload() -> dict:
    return _llm_review_stats_payload(
        llm_batches_attempted=2,
        llm_batches_succeeded=1,
        llm_batches_failed=1,
        fallback_batches=1,
        fallback_items=2,
        used_fallback=True,
        responses_received=1,
    )


def _llm_review_stats_full_fallback_payload() -> dict:
    return _llm_review_stats_payload(
        llm_batches_attempted=2,
        llm_batches_succeeded=0,
        llm_batches_failed=2,
        fallback_batches=2,
        fallback_items=3,
        used_fallback=True,
        responses_received=0,
        actual_prompt_tokens=None,
        actual_completion_tokens=None,
        actual_total_tokens=None,
        actual_cost_usd=None,
    )


def _seed_check_languages_completed_run(domain: str, en_run_id: str, target_language: str, target_run_id: str):
    _seed_runs(domain)
    _seed_phase6_prereqs(domain, en_run_id, "en")
    _seed_pages(domain, target_run_id, target_language)
    _write(domain, target_run_id, "issues.json", [])
    _write(domain, "manual", "capture_runs.json", {
        "runs": [
            {
                "run_id": target_run_id,
                "created_at": "2026-03-12T00:00:00Z",
                "jobs": [
                    {
                        "job_id": "check-languages-1",
                        "status": "succeeded",
                        "type": "check_languages",
                        "stage": "completed",
                        "en_run_id": en_run_id,
                        "target_language": target_language,
                    }
                ],
            },
            {"run_id": en_run_id, "created_at": "2026-03-11T00:00:00Z", "jobs": []},
        ]
    })


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
    assert parsed["message"][0] == "Language check payload preparation started."
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
    assert "Language+check+payload+preparation+started." in location


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


def test_orchestrator_converts_phase1_system_exit_to_failed_capture(monkeypatch):
    calls = []
    monkeypatch.setattr("app.skeleton_server._replay_scope_from_reference_run", lambda d, e, t, u: ["j1"])

    async def _fake_main(*args, **kwargs):
        calls.append("phase1")
        raise SystemExit(1)

    monkeypatch.setattr("pipeline.run_phase1.main", _fake_main)
    monkeypatch.setattr("pipeline.run_phase3.run", lambda **kwargs: calls.append("phase3"))
    monkeypatch.setattr("pipeline.run_phase6.run", lambda **kwargs: calls.append("phase6"))
    updates = []
    monkeypatch.setattr("app.skeleton_server._upsert_job_status", lambda d, r, rec: updates.append(rec))

    from app.skeleton_server import _jobs, _run_check_languages_async

    _run_check_languages_async("job1", "https://bongacams.com/", "run-en", "fr", "run-en-check-fr", "https://fr.bongacams.com/")

    assert calls == ["phase1"]
    failed = [rec for rec in updates if str(rec.get("stage")) == "running_target_capture_failed"]
    assert failed
    assert str(failed[-1].get("status")) == "failed"
    assert str(failed[-1].get("error", "")).strip()
    assert "All replay units failed during target capture" in str(failed[-1].get("error", "")) or str(failed[-1].get("error", "")).strip()
    assert not any(str(rec.get("stage")) == "running_llm_review" for rec in updates)
    assert _jobs["job1"]["status"] == "failed"
    assert _jobs["job1"].get("error", "").strip()
    assert _jobs["job1"]["error"] != ""




def test_target_capture_replay_exception_immediately_marks_terminal_failure_and_writes_artifacts(api_env, monkeypatch):
    domain = SUPPORTED_MAIN_DOMAIN
    target_run_id = "run-en-check-fr"
    updates = []

    monkeypatch.setattr("app.skeleton_server._replay_scope_from_reference_run", lambda *_args, **_kwargs: ["j1"])

    async def _fake_main(*_args, **_kwargs):
        raise RuntimeError("All replay units failed")

    monkeypatch.setattr("pipeline.run_phase1.main", _fake_main)
    monkeypatch.setattr("app.skeleton_server._upsert_job_status", lambda _d, _r, rec: updates.append(rec))

    from app.skeleton_server import _run_check_languages_async

    _run_check_languages_async("job1", domain, "run-en", "fr", target_run_id, "https://fr.bongacams.com/")

    failed = [rec for rec in updates if str(rec.get("stage")) == "running_target_capture_failed"]
    assert failed
    assert str(failed[-1].get("status")) == "failed"
    assert "All replay units failed" in str(failed[-1].get("error", ""))
    assert not any(str(rec.get("stage")) == "running_target_capture" and str(rec.get("status")) in {"running", "queued"} for rec in updates[updates.index(failed[-1]) + 1 :])

    artifacts = storage.list_run_artifacts(domain, target_run_id)
    assert f"{domain}/{target_run_id}/check_languages_replay_failure.json" in artifacts
    assert f"{domain}/{target_run_id}/check_languages_replay_failure.traceback.txt" in artifacts

    failure_payload = storage.read_json_artifact(domain, target_run_id, "check_languages_replay_failure.json")
    assert failure_payload["message"] == "All replay units failed"
    assert "Traceback" in failure_payload["traceback"]



def test_target_capture_failure_still_terminal_when_failure_artifact_persistence_raises(monkeypatch):
    updates = []
    monkeypatch.setattr("app.skeleton_server._replay_scope_from_reference_run", lambda *_args, **_kwargs: ["j1"])

    async def _fake_main(*_args, **_kwargs):
        raise RuntimeError("All replay units failed")

    monkeypatch.setattr("pipeline.run_phase1.main", _fake_main)
    monkeypatch.setattr(
        "app.skeleton_server._persist_check_languages_failure_artifacts",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("artifact write failed")),
    )
    monkeypatch.setattr("app.skeleton_server._upsert_job_status", lambda _d, _r, rec: updates.append(rec))

    from app.skeleton_server import _jobs, _prepare_check_languages_async

    _prepare_check_languages_async("job-prep", "https://bongacams.com/", "run-en", "fr", "run-en-check-fr", "https://fr.bongacams.com/")

    failed = [rec for rec in updates if rec.get("stage") == "running_target_capture_failed"]
    assert failed
    assert failed[-1].get("status") == "failed"
    assert str(failed[-1].get("error", "")).strip()
    assert failed[-1].get("failure_artifact_error") == "artifact write failed"
    assert _jobs["job-prep"]["status"] == failed[-1].get("status")

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
    assert any(str(rec.get("stage")) in {"running_llm_review_failed", "running_comparison_failed"} for rec in updates)


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
    failed = [rec for rec in updates if str(rec.get("stage")) in {"running_llm_review_failed", "running_comparison_failed"}]
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


def test_get_check_languages_completed_llm_run_shows_provider_model_tokens_and_cost(api_env):
    domain = SUPPORTED_MAIN_DOMAIN
    target_run_id = "run-en-check-fr"
    _seed_check_languages_completed_run(domain, "run-en", "fr", target_run_id)
    _write(domain, target_run_id, "llm_review_stats.json", _llm_review_stats_completed_payload())

    status, body, _ = _request("GET", api_env, f"/check-languages?domain={domain}&en_run_id=run-en&target_language=fr&target_run_id={target_run_id}")
    assert status == HTTPStatus.OK
    assert "Configured provider/model: llm / openrouter/free" in body
    assert "Effective provider/model: llm / openrouter/free" in body
    assert "Estimated tokens (prompt/completion/total): prompt=120, completion=30, total=150" in body
    assert "Actual tokens (prompt/completion/total): prompt=118, completion=28, total=146" in body
    assert "Cost used: $0.001200 (actual)" in body


def test_get_check_languages_completed_llm_run_shows_partial_fallback_clearly(api_env):
    domain = SUPPORTED_MAIN_DOMAIN
    target_run_id = "run-en-check-fr"
    _seed_check_languages_completed_run(domain, "run-en", "fr", target_run_id)
    _write(domain, target_run_id, "llm_review_stats.json", _llm_review_stats_partial_fallback_payload())

    status, body, _ = _request("GET", api_env, f"/check-languages?domain={domain}&en_run_id=run-en&target_language=fr&target_run_id={target_run_id}")
    assert status == HTTPStatus.OK
    assert "Fallback status: Partial fallback" in body
    assert "Operator notes: Fallback used: Partial fallback" in body


def test_get_check_languages_completed_llm_run_shows_full_fallback_clearly(api_env):
    domain = SUPPORTED_MAIN_DOMAIN
    target_run_id = "run-en-check-fr"
    _seed_check_languages_completed_run(domain, "run-en", "fr", target_run_id)
    _write(domain, target_run_id, "llm_review_stats.json", _llm_review_stats_full_fallback_payload())

    status, body, _ = _request("GET", api_env, f"/check-languages?domain={domain}&en_run_id=run-en&target_language=fr&target_run_id={target_run_id}")
    assert status == HTTPStatus.OK
    assert "Fallback status: Full fallback" in body
    assert "No successful LLM responses" in body


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
    assert "running" in body.lower()
    assert "State: <strong>LLM review not reached yet</strong>" in body


def test_get_check_languages_warns_when_llm_telemetry_missing_after_completion(api_env):
    domain = SUPPORTED_MAIN_DOMAIN
    target_run_id = "run-en-check-fr"
    _seed_check_languages_completed_run(domain, "run-en", "fr", target_run_id)

    status, body, _ = _request("GET", api_env, f"/check-languages?domain={domain}&en_run_id=run-en&target_language=fr&target_run_id={target_run_id}")
    assert status == HTTPStatus.OK
    assert "State: <strong>LLM stage not started</strong>" in body or "State: <strong>LLM telemetry missing</strong>" in body


def test_get_check_languages_malformed_llm_telemetry_warning_is_rendered_safely(api_env):
    domain = SUPPORTED_MAIN_DOMAIN
    target_run_id = "run-en-check-fr"
    _seed_check_languages_completed_run(domain, "run-en", "fr", target_run_id)
    _write(domain, target_run_id, "llm_review_stats.json", ["<script>alert(1)</script>"])

    status, body, _ = _request("GET", api_env, f"/check-languages?domain={domain}&en_run_id=run-en&target_language=fr&target_run_id={target_run_id}")
    assert status == HTTPStatus.OK
    assert "LLM telemetry malformed" in body
    assert "<script>alert(1)</script>" not in body
    assert "Telemetry file exists but is malformed; showing unavailable placeholders." in body


def test_get_check_languages_llm_requested_false_shows_no_real_llm_request_message(api_env):
    domain = SUPPORTED_MAIN_DOMAIN
    target_run_id = "run-en-check-fr"
    _seed_check_languages_completed_run(domain, "run-en", "fr", target_run_id)
    _write(
        domain,
        target_run_id,
        "llm_review_stats.json",
        _llm_review_stats_payload(
            llm_requested=False,
            review_mode="llm",
            llm_batches_attempted=0,
            llm_batches_succeeded=0,
            llm_batches_failed=0,
            fallback_batches=1,
            fallback_items=1,
            used_fallback=True,
            responses_received=0,
            estimated_prompt_tokens=0,
            estimated_completion_tokens=0,
            estimated_total_tokens=0,
            actual_prompt_tokens=None,
            actual_completion_tokens=None,
            actual_total_tokens=None,
            actual_cost_usd=None,
        ),
    )

    status, body, _ = _request("GET", api_env, f"/check-languages?domain={domain}&en_run_id=run-en&target_language=fr&target_run_id={target_run_id}")
    assert status == HTTPStatus.OK
    assert "LLM not executed: provider misconfigured (missing API key or provider)" in body


def test_llm_review_ui_state_is_consistent_with_telemetry(api_env):
    domain = SUPPORTED_MAIN_DOMAIN
    target_run_id = "run-en-check-fr"
    _seed_check_languages_completed_run(domain, "run-en", "fr", target_run_id)
    _write(
        domain,
        target_run_id,
        "llm_review_stats.json",
        _llm_review_stats_payload(
            llm_requested=True,
            llm_batches_attempted=2,
            llm_batches_succeeded=1,
            llm_batches_failed=1,
            responses_received=1,
            used_fallback=True,
            fallback_batches=1,
            fallback_items=1,
        ),
    )

    status, body, _ = _request("GET", api_env, f"/check-languages?domain={domain}&en_run_id=run-en&target_language=fr&target_run_id={target_run_id}")
    assert status == HTTPStatus.OK
    assert "LLM not executed: provider misconfigured (missing API key or provider)" not in body
    assert "Effective provider/model: llm / openrouter/free" in body
    assert "Fallback status: Partial fallback" in body


def test_prepare_action_only_starts_prepare_worker(api_env, monkeypatch):
    domain = SUPPORTED_MAIN_DOMAIN
    _seed_runs(domain)
    _seed_phase6_prereqs(domain, "run-en", "en")
    called = []

    def _fake_prepare(*args, **kwargs):
        called.append("prepare")

    monkeypatch.setattr("app.skeleton_server._prepare_check_languages_async", _fake_prepare)
    monkeypatch.setattr("app.skeleton_server._run_check_languages_llm_async", lambda *args, **kwargs: called.append("llm"))
    form = _query({"selected_domain": domain, "en_run_id": "run-en", "target_language": "fr", "action": "prepare_payload"})
    status_post, _, location = _request("POST", api_env, "/check-languages", form, {"Content-Type": "application/x-www-form-urlencoded"})
    assert status_post == HTTPStatus.FOUND
    assert "Language+check+payload+preparation+started." in location
    assert called == ["prepare"]


def test_run_llm_button_disabled_without_prepared_payload(api_env):
    domain = SUPPORTED_MAIN_DOMAIN
    _seed_runs(domain)
    _seed_phase6_prereqs(domain, "run-en", "en")
    target_run_id = "run-en-check-fr"
    _seed_pages(domain, target_run_id, "fr")
    status, body, _ = _request("GET", api_env, f"/check-languages?domain={domain}&en_run_id=run-en&target_language=fr&target_run_id={target_run_id}")
    assert status == HTTPStatus.OK
    assert 'id="checkLanguagesRunLlmButton"' in body
    assert 'id="checkLanguagesRunLlmButton" name="action" value="run_llm_review" type="submit" disabled="disabled"' in body


def test_payload_preview_and_replay_failure_are_visible(api_env):
    domain = SUPPORTED_MAIN_DOMAIN
    target_run_id = "run-en-check-fr"
    _seed_runs(domain)
    _seed_phase6_prereqs(domain, "run-en", "en")
    _seed_phase6_prereqs(domain, target_run_id, "fr")
    _write(domain, target_run_id, "check_languages_prepared_payload.json", {"ok": True})
    _write(domain, target_run_id, "check_languages_replay_failure.json", {"exception_class": "TimeoutError", "message": "readiness timeout"})
    _write(domain, "manual", "capture_runs.json", {
        "runs": [
            {"run_id": target_run_id, "created_at": "2026-03-12T00:00:00Z", "jobs": [{"job_id": "check-languages-1", "status": "failed", "type": "check_languages", "stage": "running_target_capture_failed", "workflow_state": "failed_before_llm", "en_run_id": "run-en", "target_language": "fr"}]},
            {"run_id": "run-en", "created_at": "2026-03-11T00:00:00Z", "jobs": []},
        ]
    })
    status, body, _ = _request("GET", api_env, f"/check-languages?domain={domain}&en_run_id=run-en&target_language=fr&target_run_id={target_run_id}")
    assert status == HTTPStatus.OK
    assert "Prepared payload preview" in body
    assert "check_languages_llm_input.json" in body
    assert "Preparation failure:" in body
    assert "failed_before_llm" in body


def test_payload_preview_is_pending_without_fake_path_during_preparation(api_env):
    domain = SUPPORTED_MAIN_DOMAIN
    target_run_id = "run-en-check-fr"
    _seed_runs(domain)
    _seed_phase6_prereqs(domain, "run-en", "en")
    _seed_phase6_prereqs(domain, target_run_id, "fr")
    _write(domain, "manual", "capture_runs.json", {
        "runs": [
            {
                "run_id": target_run_id,
                "created_at": "2026-03-12T00:00:00Z",
                "jobs": [
                    {
                        "job_id": "check-languages-1",
                        "status": "running",
                        "type": "check_languages",
                        "stage": "running_target_capture",
                        "workflow_state": "preparing_payload",
                        "en_run_id": "run-en",
                        "target_language": "fr",
                    }
                ],
            },
            {"run_id": "run-en", "created_at": "2026-03-11T00:00:00Z", "jobs": []},
        ]
    })

    status, body, _ = _request("GET", api_env, f"/check-languages?domain={domain}&en_run_id=run-en&target_language=fr&target_run_id={target_run_id}")
    assert status == HTTPStatus.OK
    assert "check_languages_llm_input.json" in body
    assert "status: <strong>pending</strong>" in body
    assert "Will be created after target capture and payload preparation complete." in body
    assert f"{domain}/{target_run_id}/check_languages_llm_input.json" not in body
    assert "<summary>Preview</summary>" not in body


def test_payload_preview_shows_real_artifact_path_when_input_exists(api_env):
    domain = SUPPORTED_MAIN_DOMAIN
    target_run_id = "run-en-check-fr"
    _seed_runs(domain)
    _seed_phase6_prereqs(domain, "run-en", "en")
    _seed_phase6_prereqs(domain, target_run_id, "fr")
    _write(domain, target_run_id, "check_languages_llm_input.json", {"target_language": "fr", "review_context_count": 0, "review_contexts": []})
    _write(domain, target_run_id, "check_languages_prepared_payload.json", {
        "source_hashes": {},
        "llm_input_artifact": f"gs://test-bucket/{domain}/{target_run_id}/check_languages_llm_input.json",
    })

    status, body, _ = _request("GET", api_env, f"/check-languages?domain={domain}&en_run_id=run-en&target_language=fr&target_run_id={target_run_id}")
    assert status == HTTPStatus.OK
    assert "status: <strong>valid</strong>" in body
    assert f"gs://test-bucket/{domain}/{target_run_id}/check_languages_llm_input.json" in body


def test_payload_preview_reports_llm_input_valid_status(api_env):
    domain = SUPPORTED_MAIN_DOMAIN
    target_run_id = "run-en-check-fr"
    _seed_runs(domain)
    _seed_phase6_prereqs(domain, "run-en", "en")
    _seed_phase6_prereqs(domain, target_run_id, "fr")
    _write(domain, target_run_id, "check_languages_llm_input.json", {"target_language": "fr", "review_context_count": 1, "review_contexts": [{"id": "ctx-1"}]})

    status, body, _ = _request("GET", api_env, f"/check-languages?domain={domain}&en_run_id=run-en&target_language=fr&target_run_id={target_run_id}")
    assert status == HTTPStatus.OK
    assert "status: <strong>valid</strong>" in body


def test_payload_preview_reports_llm_input_read_error_status(api_env, monkeypatch):
    domain = SUPPORTED_MAIN_DOMAIN
    target_run_id = "run-en-check-fr"
    _seed_runs(domain)
    _seed_phase6_prereqs(domain, "run-en", "en")
    _seed_phase6_prereqs(domain, target_run_id, "fr")
    _write(domain, target_run_id, "check_languages_llm_input.json", {"target_language": "fr", "review_context_count": 1, "review_contexts": [{"id": "ctx-1"}]})

    original_read = storage.read_json_artifact

    def _flaky_read(domain_arg: str, run_id_arg: str, filename: str):
        if filename == "check_languages_llm_input.json":
            raise RuntimeError("boom")
        return original_read(domain_arg, run_id_arg, filename)

    monkeypatch.setattr("app.skeleton_server.storage.read_json_artifact", _flaky_read)

    status, body, _ = _request("GET", api_env, f"/check-languages?domain={domain}&en_run_id=run-en&target_language=fr&target_run_id={target_run_id}")
    assert status == HTTPStatus.OK
    assert "status: <strong>read_error</strong>" in body
    assert "Will be created after target capture and payload preparation complete." not in body


def test_llm_input_diagnostics_do_not_downgrade_read_error_when_listing_is_unreliable(api_env, monkeypatch):
    domain = SUPPORTED_MAIN_DOMAIN
    target_run_id = "run-en-check-fr"
    _seed_runs(domain)
    _seed_phase6_prereqs(domain, "run-en", "en")
    _seed_phase6_prereqs(domain, target_run_id, "fr")
    _write(domain, target_run_id, "check_languages_llm_input.json", {"target_language": "fr", "review_context_count": 1, "review_contexts": [{"id": "ctx-1"}]})

    monkeypatch.setattr("app.skeleton_server._artifact_exists", lambda *args, **kwargs: False)
    original_read = storage.read_json_artifact

    def _broken_read(domain_arg: str, run_id_arg: str, filename: str):
        if filename == "check_languages_llm_input.json":
            raise RuntimeError("transient storage outage")
        return original_read(domain_arg, run_id_arg, filename)

    monkeypatch.setattr("app.skeleton_server.storage.read_json_artifact", _broken_read)

    status, body, _ = _request("GET", api_env, f"/check-languages?domain={domain}&en_run_id=run-en&target_language=fr&target_run_id={target_run_id}")
    assert status == HTTPStatus.OK
    assert "status: <strong>read_error</strong>" in body
    assert "<strong>check_languages_llm_input.json</strong> — status: <strong>missing</strong>" not in body


def test_fallback_success_recomputes_page_state_and_llm_input_status(api_env, monkeypatch):
    from app.skeleton_server import _stable_json_hash

    domain = SUPPORTED_MAIN_DOMAIN
    target_run_id = "run-en-check-fr"
    _seed_runs(domain)
    _seed_phase6_prereqs(domain, "run-en", "en")
    _seed_phase6_prereqs(domain, target_run_id, "fr")
    empty_hash = _stable_json_hash([])
    expected_hashes = {
        "en_eligible_dataset_sha256": empty_hash,
        "target_eligible_dataset_sha256": empty_hash,
        "en_collected_items_sha256": empty_hash,
        "target_collected_items_sha256": empty_hash,
        "en_page_screenshots_sha256": empty_hash,
        "target_page_screenshots_sha256": empty_hash,
    }
    _write(domain, target_run_id, "check_languages_llm_input.json", {"target_language": "fr", "review_context_count": 2, "review_contexts": [{"id": "ctx-1"}]})
    _write(domain, target_run_id, "check_languages_prepared_payload.json", {"source_hashes": expected_hashes})
    _write(domain, "manual", "capture_runs.json", {
        "runs": [
            {
                "run_id": target_run_id,
                "created_at": "2026-03-12T00:00:00Z",
                "jobs": [{"job_id": "check-languages-1", "status": "running", "type": "check_languages", "stage": "assembling_payload", "workflow_state": "preparing_payload", "en_run_id": "run-en", "target_language": "fr"}],
            },
            {"run_id": "run-en", "created_at": "2026-03-11T00:00:00Z", "jobs": []},
        ]
    })

    monkeypatch.setattr(
        "app.skeleton_server._check_languages_llm_input_artifact_status",
        lambda *args, **kwargs: {"status": "read_error", "exists": False, "payload": None, "error": "synthetic"},
    )

    status, body, _ = _request("GET", api_env, f"/check-languages?domain={domain}&en_run_id=run-en&target_language=fr&target_run_id={target_run_id}")
    assert status == HTTPStatus.OK
    assert 'Current state: <strong id="checkLanguagesState">prepared_for_llm</strong>' in body
    assert "status: <strong>valid</strong>" in body
    assert "Will be created after target capture and payload preparation complete." not in body


def test_fallback_diagnostics_preserve_read_error_instead_of_missing(api_env, monkeypatch):
    domain = SUPPORTED_MAIN_DOMAIN
    target_run_id = "run-en-check-fr"
    _seed_runs(domain)
    _seed_phase6_prereqs(domain, "run-en", "en")
    _seed_phase6_prereqs(domain, target_run_id, "fr")

    responses = iter(
        [
            {"status": "missing", "exists": False, "payload": None, "error": "first path miss"},
            {"status": "read_error", "exists": True, "payload": None, "error": "transient read error"},
        ]
    )
    monkeypatch.setattr("app.skeleton_server._check_languages_llm_input_artifact_status", lambda *args, **kwargs: next(responses))

    status, body, _ = _request("GET", api_env, f"/check-languages?domain={domain}&en_run_id=run-en&target_language=fr&target_run_id={target_run_id}")
    assert status == HTTPStatus.OK
    assert "status: <strong>read_error</strong>" in body
    assert "<strong>check_languages_llm_input.json</strong> — status: <strong>missing</strong>" not in body


def test_recompute_gate_action_renders_gate_breakdown(api_env):
    domain = SUPPORTED_MAIN_DOMAIN
    target_run_id = "run-en-check-fr"
    _seed_runs(domain)
    _seed_phase6_prereqs(domain, "run-en", "en")
    _seed_phase6_prereqs(domain, target_run_id, "fr")
    _write(domain, target_run_id, "check_languages_llm_input.json", {"target_language": "fr", "review_context_count": 1, "review_contexts": [{"id": "ctx-1"}]})
    _write(domain, "manual", "capture_runs.json", {
        "runs": [
            {
                "run_id": target_run_id,
                "created_at": "2026-03-12T00:00:00Z",
                "jobs": [{"job_id": "check-languages-1", "status": "succeeded", "type": "check_languages", "stage": "prepared_for_llm", "workflow_state": "prepared_for_llm", "en_run_id": "run-en", "target_language": "fr"}],
            },
            {"run_id": "run-en", "created_at": "2026-03-11T00:00:00Z", "jobs": []},
        ]
    })
    form = _query({"selected_domain": domain, "en_run_id": "run-en", "target_language": "fr", "target_run_id": target_run_id, "action": "recompute_gate"})
    status_post, _, location = _request("POST", api_env, "/check-languages", form, {"Content-Type": "application/x-www-form-urlencoded"})
    assert status_post == HTTPStatus.FOUND
    assert "show_gate_diagnostics=True" in location
    assert f"target_run_id={target_run_id}" in location
    status_get, body, _ = _request("GET", api_env, location)
    assert status_get == HTTPStatus.OK
    assert "domain present:" in body
    assert "selected_en_run_id present:" in body
    assert "final llm_enabled:" in body
    assert "check_languages_llm_input.json read status:" in body


def test_recompute_form_preserves_target_run_context_inputs(api_env):
    domain = SUPPORTED_MAIN_DOMAIN
    target_run_id = "run-en-check-fr"
    _seed_runs(domain)
    _seed_phase6_prereqs(domain, "run-en", "en")
    _seed_phase6_prereqs(domain, target_run_id, "fr")
    status, body, _ = _request("GET", api_env, f"/check-languages?domain={domain}&en_run_id=run-en&target_language=fr&target_run_id={target_run_id}&generated_target_url=https%3A%2F%2Ffr.bongacams.com%2F")
    assert status == HTTPStatus.OK
    assert f'<input type="hidden" name="target_run_id" value="{target_run_id}" />' in body
    assert '<input type="hidden" name="generated_target_url" value="https://fr.bongacams.com/" />' in body


def test_recomputed_gate_final_enabled_matches_conditions(api_env):
    from app.skeleton_server import _stable_json_hash

    domain = SUPPORTED_MAIN_DOMAIN
    target_run_id = "run-en-check-fr"
    _seed_runs(domain)
    _seed_phase6_prereqs(domain, "run-en", "en")
    _seed_phase6_prereqs(domain, target_run_id, "fr")
    empty_hash = _stable_json_hash([])
    expected_hashes = {
        "en_eligible_dataset_sha256": empty_hash,
        "target_eligible_dataset_sha256": empty_hash,
        "en_collected_items_sha256": empty_hash,
        "target_collected_items_sha256": empty_hash,
        "en_page_screenshots_sha256": empty_hash,
        "target_page_screenshots_sha256": empty_hash,
    }
    _write(domain, target_run_id, "check_languages_llm_input.json", {"target_language": "fr", "review_context_count": 2, "review_contexts": [{"id": "ctx-1"}]})
    _write(domain, target_run_id, "check_languages_prepared_payload.json", {"source_hashes": expected_hashes})

    status, body, _ = _request(
        "GET",
        api_env,
        f"/check-languages?domain={domain}&en_run_id=run-en&target_language=fr&target_run_id={target_run_id}&show_gate_diagnostics=1",
    )
    assert status == HTTPStatus.OK
    assert "hashes_ok_for_page: <strong>true</strong>" in body
    assert "llm_input_exists_for_page: <strong>true</strong>" in body
    assert "final llm_enabled: <strong>true</strong>" in body
    assert 'id="checkLanguagesRunLlmButton" name="action" value="run_llm_review" type="submit"' in body
    assert 'id="checkLanguagesRunLlmButton" name="action" value="run_llm_review" type="submit" disabled="disabled"' not in body


def test_prepared_payload_artifacts_override_stale_preparing_state_and_enable_llm(api_env):
    from app.skeleton_server import _stable_json_hash

    domain = SUPPORTED_MAIN_DOMAIN
    target_run_id = "run-en-check-fr"
    _seed_runs(domain)
    _seed_phase6_prereqs(domain, "run-en", "en")
    _seed_phase6_prereqs(domain, target_run_id, "fr")
    empty_hash = _stable_json_hash([])
    expected_hashes = {
        "en_eligible_dataset_sha256": empty_hash,
        "target_eligible_dataset_sha256": empty_hash,
        "en_collected_items_sha256": empty_hash,
        "target_collected_items_sha256": empty_hash,
        "en_page_screenshots_sha256": empty_hash,
        "target_page_screenshots_sha256": empty_hash,
    }
    _write(domain, target_run_id, "check_languages_llm_input.json", {"target_language": "fr", "review_context_count": 2, "review_contexts": [{"id": "ctx-1"}]})
    _write(domain, target_run_id, "check_languages_prepared_payload.json", {
        "source_hashes": expected_hashes,
        "llm_input_artifact": f"gs://test-bucket/{domain}/{target_run_id}/check_languages_llm_input.json",
        "llm_input_count": 2,
    })
    _write(domain, "manual", "capture_runs.json", {
        "runs": [
            {
                "run_id": target_run_id,
                "created_at": "2026-03-12T00:00:00Z",
                "jobs": [
                    {
                        "job_id": "check-languages-1",
                        "status": "running",
                        "type": "check_languages",
                        "stage": "assembling_payload",
                        "workflow_state": "preparing_payload",
                        "en_run_id": "run-en",
                        "target_language": "fr",
                    }
                ],
            },
            {"run_id": "run-en", "created_at": "2026-03-11T00:00:00Z", "jobs": []},
        ]
    })

    status, body, _ = _request("GET", api_env, f"/check-languages?domain={domain}&en_run_id=run-en&target_language=fr&target_run_id={target_run_id}")
    assert status == HTTPStatus.OK
    assert 'Current state: <strong id="checkLanguagesState">prepared_for_llm</strong>' in body
    assert 'id="checkLanguagesRunLlmButton" name="action" value="run_llm_review" type="submit"' in body
    assert 'id="checkLanguagesRunLlmButton" name="action" value="run_llm_review" type="submit" disabled="disabled"' not in body



def test_prepared_payload_uses_llm_input_read_when_artifact_listing_fails(api_env, monkeypatch):
    from app.skeleton_server import _stable_json_hash

    monkeypatch.setattr("app.skeleton_server._artifact_exists", lambda *args, **kwargs: False)

    domain = SUPPORTED_MAIN_DOMAIN
    target_run_id = "run-en-check-fr"
    _seed_runs(domain)
    _seed_phase6_prereqs(domain, "run-en", "en")
    _seed_phase6_prereqs(domain, target_run_id, "fr")
    empty_hash = _stable_json_hash([])
    expected_hashes = {
        "en_eligible_dataset_sha256": empty_hash,
        "target_eligible_dataset_sha256": empty_hash,
        "en_collected_items_sha256": empty_hash,
        "target_collected_items_sha256": empty_hash,
        "en_page_screenshots_sha256": empty_hash,
        "target_page_screenshots_sha256": empty_hash,
    }
    _write(domain, target_run_id, "check_languages_llm_input.json", {"target_language": "fr", "review_context_count": 2, "review_contexts": [{"id": "ctx-1"}]})
    _write(domain, target_run_id, "check_languages_prepared_payload.json", {
        "source_hashes": expected_hashes,
        "llm_input_artifact": f"gs://test-bucket/{domain}/{target_run_id}/check_languages_llm_input.json",
        "llm_input_count": 2,
    })
    _write(domain, "manual", "capture_runs.json", {
        "runs": [
            {
                "run_id": target_run_id,
                "created_at": "2026-03-12T00:00:00Z",
                "jobs": [
                    {
                        "job_id": "check-languages-1",
                        "status": "running",
                        "type": "check_languages",
                        "stage": "assembling_payload",
                        "workflow_state": "preparing_payload",
                        "en_run_id": "run-en",
                        "target_language": "fr",
                    }
                ],
            },
            {"run_id": "run-en", "created_at": "2026-03-11T00:00:00Z", "jobs": []},
        ]
    })

    status, body, _ = _request("GET", api_env, f"/check-languages?domain={domain}&en_run_id=run-en&target_language=fr&target_run_id={target_run_id}")
    assert status == HTTPStatus.OK
    assert 'Current state: <strong id="checkLanguagesState">prepared_for_llm</strong>' in body
    assert "status: <strong>valid</strong>" in body
    assert "Will be created after target capture and payload preparation complete." not in body
    assert 'id="checkLanguagesRunLlmButton" name="action" value="run_llm_review" type="submit" disabled="disabled"' not in body


def test_llm_input_fallback_read_enables_llm_when_primary_read_returns_none(api_env, monkeypatch):
    from app.skeleton_server import _stable_json_hash
    from app import skeleton_server as ss

    domain = SUPPORTED_MAIN_DOMAIN
    target_run_id = "run-en-check-fr"
    _seed_runs(domain)
    _seed_phase6_prereqs(domain, "run-en", "en")
    _seed_phase6_prereqs(domain, target_run_id, "fr")
    empty_hash = _stable_json_hash([])
    expected_hashes = {
        "en_eligible_dataset_sha256": empty_hash,
        "target_eligible_dataset_sha256": empty_hash,
        "en_collected_items_sha256": empty_hash,
        "target_collected_items_sha256": empty_hash,
        "en_page_screenshots_sha256": empty_hash,
        "target_page_screenshots_sha256": empty_hash,
    }
    _write(domain, target_run_id, "check_languages_llm_input.json", {"target_language": "fr", "review_context_count": 2, "review_contexts": [{"id": "ctx-1"}]})
    _write(domain, target_run_id, "check_languages_prepared_payload.json", {
        "source_hashes": expected_hashes,
        "llm_input_artifact": f"gs://test-bucket/{domain}/{target_run_id}/check_languages_llm_input.json",
        "llm_input_count": 2,
    })
    _write(domain, "manual", "capture_runs.json", {
        "runs": [
            {
                "run_id": target_run_id,
                "created_at": "2026-03-12T00:00:00Z",
                "jobs": [
                    {
                        "job_id": "check-languages-1",
                        "status": "running",
                        "type": "check_languages",
                        "stage": "assembling_payload",
                        "workflow_state": "preparing_payload",
                        "en_run_id": "run-en",
                        "target_language": "fr",
                    }
                ],
            },
            {"run_id": "run-en", "created_at": "2026-03-11T00:00:00Z", "jobs": []},
        ]
    })

    original_read_json_safe = ss._read_json_safe
    llm_input_reads = {"count": 0}

    def _fake_read_json_safe(read_domain, read_run_id, filename, fallback):
        if read_domain == domain and read_run_id == target_run_id and filename == "check_languages_llm_input.json":
            llm_input_reads["count"] += 1
            if llm_input_reads["count"] == 1:
                return None
            return {"target_language": "fr", "review_context_count": 2, "review_contexts": [{"id": "ctx-fallback"}]}
        return original_read_json_safe(read_domain, read_run_id, filename, fallback)

    monkeypatch.setattr("app.skeleton_server._read_json_safe", _fake_read_json_safe)

    status, body, _ = _request("GET", api_env, f"/check-languages?domain={domain}&en_run_id=run-en&target_language=fr&target_run_id={target_run_id}")
    assert status == HTTPStatus.OK
    assert llm_input_reads["count"] >= 2
    assert 'id="checkLanguagesRunLlmButton" name="action" value="run_llm_review" type="submit" disabled="disabled"' not in body

def test_payload_artifacts_do_not_override_active_capture_state(api_env):
    from app.skeleton_server import _stable_json_hash

    domain = SUPPORTED_MAIN_DOMAIN
    target_run_id = "run-en-check-fr"
    _seed_runs(domain)
    _seed_phase6_prereqs(domain, "run-en", "en")
    _seed_phase6_prereqs(domain, target_run_id, "fr")
    empty_hash = _stable_json_hash([])
    expected_hashes = {
        "en_eligible_dataset_sha256": empty_hash,
        "target_eligible_dataset_sha256": empty_hash,
        "en_collected_items_sha256": empty_hash,
        "target_collected_items_sha256": empty_hash,
        "en_page_screenshots_sha256": empty_hash,
        "target_page_screenshots_sha256": empty_hash,
    }
    _write(domain, target_run_id, "check_languages_llm_input.json", {"target_language": "fr", "review_context_count": 2, "review_contexts": [{"id": "ctx-1"}]})
    _write(domain, target_run_id, "check_languages_prepared_payload.json", {
        "source_hashes": expected_hashes,
        "llm_input_artifact": f"gs://test-bucket/{domain}/{target_run_id}/check_languages_llm_input.json",
        "llm_input_count": 2,
    })
    _write(domain, "manual", "capture_runs.json", {
        "runs": [
            {
                "run_id": target_run_id,
                "created_at": "2026-03-12T00:00:00Z",
                "jobs": [
                    {
                        "job_id": "check-languages-1",
                        "status": "running",
                        "type": "check_languages",
                        "stage": "running_target_capture",
                        "workflow_state": "running_target_capture",
                        "en_run_id": "run-en",
                        "target_language": "fr",
                    }
                ],
            },
            {"run_id": "run-en", "created_at": "2026-03-11T00:00:00Z", "jobs": []},
        ]
    })

    status, body, _ = _request("GET", api_env, f"/check-languages?domain={domain}&en_run_id=run-en&target_language=fr&target_run_id={target_run_id}")
    assert status == HTTPStatus.OK
    assert 'Current state: <strong id="checkLanguagesState">running_target_capture</strong>' in body
    assert 'id="checkLanguagesRunLlmButton" name="action" value="run_llm_review" type="submit" disabled="disabled"' in body


def test_payload_preview_avoids_fake_path_when_manifest_uri_missing(api_env):
    domain = SUPPORTED_MAIN_DOMAIN
    target_run_id = "run-en-check-fr"
    _seed_runs(domain)
    _seed_phase6_prereqs(domain, "run-en", "en")
    _seed_phase6_prereqs(domain, target_run_id, "fr")
    _write(domain, target_run_id, "check_languages_llm_input.json", {"target_language": "fr", "review_context_count": 0, "review_contexts": []})
    _write(domain, target_run_id, "check_languages_prepared_payload.json", {"source_hashes": {}})

    status, body, _ = _request("GET", api_env, f"/check-languages?domain={domain}&en_run_id=run-en&target_language=fr&target_run_id={target_run_id}")
    assert status == HTTPStatus.OK
    assert "status: <strong>valid</strong>" in body
    assert f"{domain}/{target_run_id}/check_languages_llm_input.json" not in body
    assert f"gs://test-bucket/{domain}/{target_run_id}/check_languages_llm_input.json" in body


def test_run_llm_uses_prepared_payload_as_actual_input(monkeypatch):
    domain = "https://bongacams.com/"
    target_run_id = "run-en-check-fr"
    _write(domain, target_run_id, "check_languages_prepared_payload.json", {"source_hashes": {}, "en_run_id": "run-en", "target_run_id": target_run_id})
    _write(domain, target_run_id, "check_languages_llm_input.json", {"review_contexts": [{"en_item": {"item_id": "i1"}, "target_item": {"item_id": "i1"}, "evidence_base": {}, "language": "fr"}]})
    _write(domain, "run-en", "eligible_dataset.json", [])
    _write(domain, target_run_id, "eligible_dataset.json", [])
    _write(domain, "run-en", "collected_items.json", [])
    _write(domain, target_run_id, "collected_items.json", [])
    _write(domain, "run-en", "page_screenshots.json", [])
    _write(domain, target_run_id, "page_screenshots.json", [])

    captured = {}
    monkeypatch.setenv("PHASE6_REVIEW_PROVIDER", "test-heuristic")
    monkeypatch.setattr("pipeline.run_phase6.run", lambda **kwargs: captured.update(kwargs))
    monkeypatch.setattr("app.skeleton_server._require_artifact_exists", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.skeleton_server._upsert_job_status", lambda *args, **kwargs: None)

    from app.skeleton_server import _run_check_languages_llm_async

    _run_check_languages_llm_async("job-llm", domain, "run-en", "fr", target_run_id, "https://fr.bongacams.com/")
    assert isinstance(captured.get("prepared_llm_payload"), dict)
    assert captured["prepared_llm_payload"]["review_contexts"][0]["language"] == "fr"


def test_run_llm_uses_gs_llm_input_artifact_from_prepared_payload(monkeypatch):
    domain = "https://bongacams.com/"
    target_run_id = "run-en-check-fr"
    _write(domain, target_run_id, "check_languages_prepared_payload.json", {
        "source_hashes": {},
        "en_run_id": "run-en",
        "target_run_id": target_run_id,
        "llm_input_artifact": f"gs://test-bucket/{domain}/{target_run_id}/check_languages_llm_input.json",
    })
    _write(domain, target_run_id, "check_languages_llm_input.json", {"review_contexts": [{"language": "fr"}]})
    _write(domain, "run-en", "eligible_dataset.json", [])
    _write(domain, target_run_id, "eligible_dataset.json", [])
    _write(domain, "run-en", "collected_items.json", [])
    _write(domain, target_run_id, "collected_items.json", [])
    _write(domain, "run-en", "page_screenshots.json", [])
    _write(domain, target_run_id, "page_screenshots.json", [])

    captured = {}
    monkeypatch.setenv("PHASE6_REVIEW_PROVIDER", "test-heuristic")
    monkeypatch.setattr("pipeline.run_phase6.run", lambda **kwargs: captured.update(kwargs))
    monkeypatch.setattr("app.skeleton_server._require_artifact_exists", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.skeleton_server._upsert_job_status", lambda *args, **kwargs: None)

    from app.skeleton_server import _run_check_languages_llm_async

    _run_check_languages_llm_async("job-llm", domain, "run-en", "fr", target_run_id, "https://fr.bongacams.com/")
    assert captured["prepared_llm_payload"]["review_contexts"][0]["language"] == "fr"


def test_run_llm_rejects_http_style_llm_input_artifact(monkeypatch):
    domain = "https://bongacams.com/"
    target_run_id = "run-en-check-fr"
    _write(domain, target_run_id, "check_languages_prepared_payload.json", {
        "source_hashes": {},
        "llm_input_artifact": f"{domain}/{target_run_id}/check_languages_llm_input.json",
    })

    monkeypatch.setenv("PHASE6_REVIEW_PROVIDER", "test-heuristic")
    monkeypatch.setattr("app.skeleton_server._upsert_job_status", lambda *args, **kwargs: None)

    from app.skeleton_server import _jobs, _run_check_languages_llm_async

    _run_check_languages_llm_async("job-llm-http", domain, "run-en", "fr", target_run_id, "https://fr.bongacams.com/")
    assert _jobs["job-llm-http"]["status"] == "error"
    assert "not a valid gs:// URI" in _jobs["job-llm-http"]["error"]


def test_prepare_payload_uses_written_gs_uri_for_llm_input_artifact(monkeypatch):
    domain = "https://bongacams.com/"
    en_run_id = "run-en"
    target_run_id = "run-en-check-fr"
    target_language = "fr"
    llm_input_uri = f"gs://test-bucket/{domain}/{target_run_id}/check_languages_llm_input.json"
    prepared_payload_record = {}

    def _fake_write_json_artifact(_domain, _run_id, filename, payload):
        if filename == "check_languages_llm_input.json":
            return llm_input_uri
        if filename == "check_languages_prepared_payload.json":
            prepared_payload_record["payload"] = payload
            return f"gs://test-bucket/{domain}/{target_run_id}/check_languages_prepared_payload.json"
        return f"gs://test-bucket/{domain}/{target_run_id}/{filename}"

    monkeypatch.setattr("app.skeleton_server._replay_scope_from_reference_run", lambda *args, **kwargs: [])
    monkeypatch.setattr("asyncio.run", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("pipeline.run_phase1.main", lambda *args, **kwargs: None)
    monkeypatch.setattr("pipeline.run_phase3.run", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.skeleton_server._require_artifact_exists", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.skeleton_server._check_languages_payload_status", lambda *args, **kwargs: {"ready": True, "files": []})
    monkeypatch.setattr("pipeline.run_phase6.build_prepared_llm_payload", lambda *args, **kwargs: {"review_context_count": 2})
    monkeypatch.setattr("app.skeleton_server._check_languages_source_hashes", lambda *args, **kwargs: {})
    monkeypatch.setattr("app.skeleton_server._upsert_job_status", lambda *args, **kwargs: None)
    monkeypatch.setattr("pipeline.storage.write_json_artifact", _fake_write_json_artifact)

    from app.skeleton_server import _prepare_check_languages_async

    _prepare_check_languages_async("job-prep", domain, en_run_id, target_language, target_run_id, "https://fr.bongacams.com/")
    assert prepared_payload_record["payload"]["llm_input_artifact"] == llm_input_uri


def test_run_llm_is_blocked_when_prepared_payload_is_stale(api_env):
    domain = SUPPORTED_MAIN_DOMAIN
    target_run_id = "run-en-check-fr"
    _seed_runs(domain)
    _seed_phase6_prereqs(domain, "run-en", "en")
    _seed_phase6_prereqs(domain, target_run_id, "fr")
    _write(domain, target_run_id, "check_languages_llm_input.json", {"review_contexts": []})
    _write(domain, target_run_id, "check_languages_prepared_payload.json", {"source_hashes": {"en_eligible_dataset_sha256": "old"}})

    form = _query({"selected_domain": domain, "en_run_id": "run-en", "target_language": "fr", "target_run_id": target_run_id, "action": "run_llm_review"})
    status_post, _, location = _request("POST", api_env, "/check-languages", form, {"Content-Type": "application/x-www-form-urlencoded"})
    assert status_post == HTTPStatus.FOUND
    assert "Prepared+payload+is+stale" in location


def test_replay_failure_diagnostics_include_specific_replay_unit(monkeypatch):
    monkeypatch.setattr("app.skeleton_server._replay_scope_from_reference_run", lambda *args, **kwargs: [
        type("J", (), {"context": type("C", (), {"url": "https://fr.bongacams.com/a", "state": "pricing"})(), "recipe_id": "recipe-1", "capture_point_id": "cp-1"})()
    ])

    async def _fake_main(*args, **kwargs):
        raise RuntimeError("navigation timeout at https://fr.bongacams.com/a")

    records = []
    monkeypatch.setattr("pipeline.run_phase1.main", _fake_main)
    monkeypatch.setattr("app.skeleton_server._upsert_job_status", lambda _d, _r, rec: records.append(rec))
    monkeypatch.setattr("app.skeleton_server._persist_check_languages_failure_artifacts", lambda *args, **kwargs: {})

    from app.skeleton_server import _prepare_check_languages_async

    _prepare_check_languages_async("job-prep", "https://bongacams.com/", "run-en", "fr", "run-en-check-fr", "https://fr.bongacams.com/")
    failed = [r for r in records if r.get("stage") == "running_target_capture_failed"]
    assert failed
    ctx = failed[-1]["error_details"]["replay_context"]
    assert ctx["recipe_id"] == "recipe-1"
    assert ctx["capture_point_id"] == "cp-1"
    assert ctx["state"] == "pricing"
    assert ctx["target_url"]


def test_about_page_renders_llm_wire_format_dictionary(api_env):
    status, body, _ = _request("GET", api_env, "/about")
    assert status == HTTPStatus.OK
    assert 'id="llm-wire-format-dictionary"' in body
    assert "LLM Wire Format Dictionary" in body
    assert '{"l":"&lt;target_language&gt;","i":[[id,en,tg,k,c,m,p]]}' in body
    assert '{"r":[[id,s,g,m,n]]}' in body
    assert "4=short_text" in body


def test_check_languages_llm_dictionary_link_is_before_status_block(api_env):
    domain = SUPPORTED_MAIN_DOMAIN
    _seed_runs(domain)
    _seed_phase6_prereqs(domain, "run-en", "en")
    status, body, _ = _request("GET", api_env, f"/check-languages?domain={domain}&en_run_id=run-en&target_language=fr")
    assert status == HTTPStatus.OK
    assert '<a href="/about#llm-wire-format-dictionary">View LLM wire format dictionary</a>' in body
    link_pos = body.index('href="/about#llm-wire-format-dictionary"')
    state_pos = body.index("State:")
    assert link_pos < state_pos
