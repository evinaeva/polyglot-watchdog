"""Minimal deterministic skeleton UI server for Polyglot Watchdog.

Phase 0 and Phase 1 are wired to real pipeline modules.
Phase 2 (template_rules) and Phase 3 (eligible_dataset) are wired to real pipeline modules.
Other phases remain as stubs or mock data.
AUTH_MODE = "ON"
"""

from __future__ import annotations

import csv
import io
import json
import os
import re
import base64
import hashlib
import hmac
import secrets
import sys
import threading
import time
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# Ensure project root is on sys.path for pipeline imports
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.recipes import delete_recipe, list_recipes, upsert_recipe, load_recipes_for_planner
from app.seed_urls import (
    normalize_seed_url,
    parse_seed_urls,
    parse_seed_urls_with_errors,
    read_seed_urls,
    validate_domain,
    write_seed_rows,
    write_seed_urls,
)
from app.testbench import get_modules, run_module_test
from pipeline.interactive_capture import GCSArtifactWriter
from pipeline.runtime_config import load_phase1_runtime_config

TEMPLATES_DIR = BASE_DIR / "web" / "templates"
STATIC_DIR = BASE_DIR / "web" / "static"
FIXTURE_DIR = STATIC_DIR / "watchdog-fixture"

SESSION_COOKIE = "pw_session"
CSRF_COOKIE = "pw_csrf"
WATCHDOG_PASSWORD_ENV = "WATCHDOG_PASSWORD"
SESSION_SIGNING_SECRET_ENV = "SESSION_SIGNING_SECRET"
AUTH_MODE = "OFF"
SESSION_MAX_AGE_SECONDS = max(int(os.environ.get("SESSION_MAX_AGE_SECONDS", "28800")), 300)


# In-memory job status store (cleared on restart — for UI feedback only)
_jobs: dict[str, dict] = {}
_template_cache: dict[Path, tuple[int, str]] = {}


def _read_json_safe(domain: str, run_id: str, filename: str, default):
    from pipeline.storage import read_json_artifact

    try:
        return read_json_artifact(domain, run_id, filename)
    except Exception as exc:
        print(f"[storage] read fallback domain={domain} run_id={run_id} file={filename}: {exc}", file=sys.stderr)
        return default




def _artifact_exists(domain: str, run_id: str, filename: str) -> bool:
    from pipeline.storage import artifact_path, list_run_artifacts

    try:
        return artifact_path(domain, run_id, filename) in list_run_artifacts(domain, run_id)
    except Exception:
        return False


def _capture_context_id_from_page(domain: str, page: dict) -> str:
    from pipeline.interactive_capture import CaptureContext, build_capture_context_id

    ctx = CaptureContext(
        domain=domain,
        url=str(page.get("url", "")),
        language=str(page.get("language", "")),
        viewport_kind=str(page.get("viewport_kind", "")),
        state=str(page.get("state", "")),
        user_tier=page.get("user_tier") or None,
    )
    return build_capture_context_id(ctx)


def _to_rule_type(decision: str) -> str:
    value = str(decision or "").strip().lower()
    mapping = {
        "eligible": "ALWAYS_COLLECT",
        "exclude": "IGNORE_ENTIRE_ELEMENT",
        "needs-fix": "MASK_VARIABLE",
    }
    return mapping.get(value, decision)
def _list_domains() -> list[str]:
    payload = _read_json_safe("_system", "manual", "domains.json", {"domains": []})
    values = payload.get("domains") if isinstance(payload, dict) else []
    return sorted({str(v).strip() for v in values if str(v).strip()})


def _register_domain(domain: str) -> None:
    from pipeline.storage import write_json_artifact

    domain = validate_domain(domain)
    domains = set(_list_domains())
    domains.add(domain)
    write_json_artifact("_system", "manual", "domains.json", {"domains": sorted(domains)})


def _load_runs(domain: str) -> dict:
    payload = _read_json_safe(domain, "manual", "capture_runs.json", {"runs": []})
    if not isinstance(payload, dict) or not isinstance(payload.get("runs"), list):
        return {"runs": []}
    return payload


def _save_runs(domain: str, payload: dict) -> None:
    from pipeline.storage import write_json_artifact

    write_json_artifact(domain, "manual", "capture_runs.json", payload)


def _upsert_job_status(domain: str, run_id: str, job_record: dict) -> None:
    runs_payload = _load_runs(domain)
    runs = runs_payload["runs"]
    run = next((r for r in runs if r.get("run_id") == run_id), None)
    if run is None:
        run = {"run_id": run_id, "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "jobs": []}
        runs.append(run)
    jobs = [j for j in run.get("jobs", []) if j.get("job_id") != job_record.get("job_id")]
    jobs.append(job_record)
    jobs.sort(key=lambda r: r.get("job_id", ""))
    run["jobs"] = jobs
    runs.sort(key=lambda r: r.get("run_id", ""), reverse=True)
    _save_runs(domain, {"runs": runs})




def _load_phase2_decisions(domain: str, run_id: str) -> list[dict]:
    payload = _read_json_safe(domain, run_id, "template_rules.json", [])
    if not isinstance(payload, list):
        return []
    rows: list[dict] = []
    for row in payload:
        if not isinstance(row, dict):
            continue
        rows.append({
            "item_id": str(row.get("item_id", "")),
            "url": str(row.get("url", "")),
            "rule_type": str(row.get("rule_type", "")),
            "updated_at": str(row.get("created_at", "")),
        })
    return rows


def _save_phase2_decisions(domain: str, run_id: str, decisions: list[dict]) -> None:
    # Canonical persistence for annotation decisions is template_rules.json via run_phase2.
    # This helper remains for compatibility in tests, but intentionally no-ops.
    _ = (domain, run_id, decisions)


def _decision_key(row: dict) -> tuple:
    return (
        str(row.get("capture_context_id", "")),
        str(row.get("item_id", "")),
        str(row.get("url", "")),
        str(row.get("state", "")),
        str(row.get("language", "")),
        str(row.get("viewport_kind", "")),
        str(row.get("user_tier") or ""),
    )


def _upsert_phase2_decision(domain: str, run_id: str, decision: dict) -> dict:
    # Canonical write happens via pipeline.run_phase2.run -> template_rules.json
    _ = (domain, run_id)
    return decision


def _estimate_severity(issue: dict) -> str:
    explicit = str(issue.get("severity", "")).strip().lower()
    if explicit in {"high", "medium", "low"}:
        return explicit
    confidence = float(issue.get("confidence", 0) or 0)
    if confidence >= 0.9:
        return "high"
    if confidence >= 0.7:
        return "medium"
    return "low"


def _issues_to_csv(issues: list[dict]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "category", "severity", "language", "state", "url", "message"])
    for issue in issues:
        evidence = issue.get("evidence", {}) if isinstance(issue.get("evidence"), dict) else {}
        writer.writerow([
            str(issue.get("id", "")),
            str(issue.get("category", "")),
            _estimate_severity(issue),
            str(issue.get("language", "")),
            str(issue.get("state", "")),
            str(evidence.get("url", "")),
            str(issue.get("message", "")).replace("\n", " "),
        ])
    return output.getvalue()


def _filter_issues(issues: list[dict], query: dict[str, list[str]]) -> list[dict]:
    q = query.get("q", [""])[0].strip().lower()
    issue_type = query.get("type", [""])[0].strip().lower()
    language = query.get("language", [""])[0].strip().lower()
    severity = query.get("severity", [""])[0].strip().lower()
    state = query.get("state", [""])[0].strip().lower()
    url_filter = query.get("url", [""])[0].strip().lower()
    domain_filter = query.get("domain_filter", [""])[0].strip().lower()

    filtered = []
    for issue in issues:
        evidence = issue.get("evidence", {}) if isinstance(issue.get("evidence"), dict) else {}
        issue_url = str(evidence.get("url", ""))
        derived = {
            "language": str(issue.get("language", "")).lower(),
            "severity": _estimate_severity(issue),
            "type": str(issue.get("category", "")).lower(),
            "state": str(issue.get("state", "")).lower(),
            "url": issue_url.lower(),
        }
        if issue_type and derived["type"] != issue_type:
            continue
        if language and derived["language"] != language:
            continue
        if severity and derived["severity"] != severity:
            continue
        if state and derived["state"] != state:
            continue
        if domain_filter and domain_filter not in derived["url"]:
            continue
        if url_filter and url_filter not in derived["url"]:
            continue
        if q and q not in str(issue.get("category", "")).lower() and q not in str(issue.get("message", "")).lower() and q not in derived["url"]:
            continue
        filtered.append(issue)
    return sorted(filtered, key=lambda item: str(item.get("id", "")))



def _expand_capture_plan(domain: str, planning_rows: list[dict], languages: list[str], viewports: list[str], tiers: list[str], recipes: dict) -> list[dict]:
    from pipeline.run_phase1 import build_planned_jobs

    # NOTE: we intentionally expand cross-product at this layer to guarantee deterministic
    # operator-visible plan ordering: language -> viewport -> user_tier.
    expanded_jobs = []
    seen: set[tuple[str, str, str, str, str, str, str]] = set()
    for language in sorted(languages):
        for viewport in sorted(viewports):
            for tier in sorted(tiers):
                jobs = build_planned_jobs(domain, planning_rows, language, viewport, tier or None, recipes)
                for job in jobs:
                    key = (
                        str(job.context.url),
                        str(job.context.language),
                        str(job.context.viewport_kind),
                        str(job.context.state),
                        str(job.context.user_tier or ""),
                        str(job.recipe_id or ""),
                        str(job.mode),
                    )
                    if key in seen:
                        continue
                    seen.add(key)
                    expanded_jobs.append(job)
    return [
        {
            "url": job.context.url,
            "language": job.context.language,
            "viewport_kind": job.context.viewport_kind,
            "state": job.context.state,
            "user_tier": job.context.user_tier,
            "mode": job.mode,
            "recipe_id": job.recipe_id,
        }
        for job in expanded_jobs
    ]

class _ReviewConfigStore:
    def _client(self):
        from google.cloud import storage  # type: ignore

        return storage.Client()

    def write_json(self, bucket: str, key: str, value):
        import json

        client = self._client()
        blob = client.bucket(bucket).blob(key)
        blob.upload_from_string(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")), content_type="application/json; charset=utf-8")
        return f"gs://{bucket}/{key}"


def _parse_rerun_payload(payload: dict) -> dict:
    required = ["domain", "run_id", "url", "viewport_kind", "state", "language", "capture_context_id"]
    missing = [k for k in required if not str(payload.get(k, "")).strip()]
    if missing:
        raise ValueError(f"missing required fields: {', '.join(missing)}")
    runtime_payload = {
        "domain": str(payload.get("domain", "")).strip(),
        "run_id": str(payload.get("run_id", "")).strip(),
        "language": str(payload.get("language", "")).strip(),
        "viewport_kind": str(payload.get("viewport_kind", "")).strip(),
        "state": str(payload.get("state", "")).strip(),
        "user_tier": payload.get("user_tier") or None,
        "url": str(payload.get("url", "")).strip(),
        "capture_context_id": str(payload.get("capture_context_id", "")).strip() or None,
    }
    load_phase1_runtime_config(runtime_payload)
    return runtime_payload


def _persist_capture_review(payload: dict) -> dict:
    from pipeline.schema_validator import validate

    domain = validate_domain(str(payload.get("domain", "")))
    capture_context_id = str(payload.get("capture_context_id", "")).strip()
    language = str(payload.get("language", "")).strip()
    status = str(payload.get("status", "")).strip()
    reviewer = str(payload.get("reviewer", "operator")).strip() or "operator"
    timestamp = str(payload.get("timestamp", "")).strip()
    if not capture_context_id:
        raise ValueError("capture_context_id is required")
    if not language:
        raise ValueError("language is required")
    if not timestamp:
        raise ValueError("timestamp is required")

    record = {
        "capture_context_id": capture_context_id,
        "status": status,
        "reviewer": reviewer,
        "timestamp": timestamp,
    }
    validate("capture_review_status", record)

    from pipeline.storage import BUCKET_NAME

    review_bucket = os.environ.get("REVIEW_BUCKET", BUCKET_NAME)
    writer = GCSArtifactWriter(_ReviewConfigStore(), BUCKET_NAME, review_bucket)
    uri = writer.set_review_status(domain, capture_context_id, language, record)
    return {"record": record, "storage_uri": uri}


def _run_phase0_async(job_id: str, domain: str, run_id: str) -> None:
    """Run Phase 0 in a background thread."""
    _jobs[job_id] = {"status": "running", "phase": "0", "domain": domain, "run_id": run_id}
    try:
        from pipeline.run_phase0 import run as phase0_run
        phase0_run(domain=domain, run_id=run_id)
        _jobs[job_id]["status"] = "done"
        _upsert_job_status(domain, run_id, {"job_id": job_id, "status": "succeeded", "phase": "0"})
    except Exception as exc:
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = str(exc)
        _upsert_job_status(domain, run_id, {"job_id": job_id, "status": "failed", "error": str(exc), "phase": "0"})


def _run_phase1_async(job_id: str, runtime_payload: dict) -> None:
    """Run Phase 1 in a background thread."""
    _jobs[job_id] = {"status": "running", "phase": "1", "domain": runtime_payload.get("domain"), "run_id": runtime_payload.get("run_id")}
    _upsert_job_status(str(runtime_payload.get("domain")), str(runtime_payload.get("run_id")), {"job_id": job_id, "status": "running", "context": runtime_payload})
    try:
        from pipeline.run_phase1 import run_with_config

        config = load_phase1_runtime_config(runtime_payload)
        run_with_config(config)
        _jobs[job_id]["status"] = "done"
        _upsert_job_status(str(runtime_payload.get("domain")), str(runtime_payload.get("run_id")), {"job_id": job_id, "status": "succeeded", "context": runtime_payload})
    except Exception as exc:
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = str(exc)
        _upsert_job_status(str(runtime_payload.get("domain")), str(runtime_payload.get("run_id")), {"job_id": job_id, "status": "failed", "error": str(exc), "context": runtime_payload})


def _run_rerun_async(job_id: str, runtime_payload: dict) -> None:
    _jobs[job_id] = {"status": "running", "phase": "rerun", "domain": runtime_payload.get("domain"), "run_id": runtime_payload.get("run_id")}
    _upsert_job_status(str(runtime_payload.get("domain")), str(runtime_payload.get("run_id")), {"job_id": job_id, "status": "running", "context": runtime_payload, "type": "rerun"})
    try:
        from pipeline.run_phase1 import run_exact_context

        run_exact_context(
            domain=str(runtime_payload.get("domain")),
            run_id=str(runtime_payload.get("run_id")),
            url=str(runtime_payload.get("url")),
            viewport_kind=str(runtime_payload.get("viewport_kind")),
            state=str(runtime_payload.get("state")),
            user_tier=runtime_payload.get("user_tier"),
            language=str(runtime_payload.get("language")),
            original_context_id=runtime_payload.get("capture_context_id"),
        )
        _jobs[job_id]["status"] = "done"
        _upsert_job_status(str(runtime_payload.get("domain")), str(runtime_payload.get("run_id")), {"job_id": job_id, "status": "succeeded", "context": runtime_payload, "type": "rerun"})
    except Exception as exc:
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = str(exc)
        _upsert_job_status(str(runtime_payload.get("domain")), str(runtime_payload.get("run_id")), {"job_id": job_id, "status": "failed", "error": str(exc), "context": runtime_payload, "type": "rerun"})


def _run_phase3_async(job_id: str, domain: str, run_id: str) -> None:
    """Run Phase 3 in a background thread."""
    _jobs[job_id] = {"status": "running", "phase": "3", "domain": domain, "run_id": run_id}
    try:
        from pipeline.run_phase3 import run as phase3_run
        phase3_run(domain=domain, run_id=run_id)
        _jobs[job_id]["status"] = "done"
        _upsert_job_status(domain, run_id, {"job_id": job_id, "status": "succeeded", "phase": "3"})
    except Exception as exc:
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = str(exc)


class SkeletonHandler(BaseHTTPRequestHandler):
    def _read_template_cached(self, path: Path) -> str:
        stat = path.stat()
        cached = _template_cache.get(path)
        if cached and cached[0] == stat.st_mtime_ns:
            return cached[1]
        contents = path.read_text(encoding="utf-8")
        _template_cache[path] = (stat.st_mtime_ns, contents)
        return contents

    def _auth_enabled(self) -> bool:
        mode = os.environ.get("AUTH_MODE", AUTH_MODE).strip().upper()
        return mode != "OFF"

    def _is_production(self) -> bool:
        return bool(os.environ.get("K_SERVICE")) or os.environ.get("ENV", "").lower() == "production"

    def _get_cookie(self, key: str) -> str:
        raw_cookie = self.headers.get("Cookie", "")
        for chunk in raw_cookie.split(";"):
            part = chunk.strip()
            if not part or "=" not in part:
                continue
            name, value = part.split("=", 1)
            if name.strip() == key:
                return value.strip()
        return ""

    def _build_cookie_header(self, key: str, value: str, *, max_age: int, http_only: bool) -> str:
        same_site = "Lax"
        # Lax keeps normal same-site UX while reducing CSRF risks for cross-site requests.
        parts = [f"{key}={value}", "Path=/", f"Max-Age={max_age}", f"SameSite={same_site}"]
        if http_only:
            parts.append("HttpOnly")
        if self._is_production():
            parts.append("Secure")
        return "; ".join(parts)

    def _expire_cookie_header(self, key: str, *, http_only: bool) -> str:
        parts = [f"{key}=", "Path=/", "Max-Age=0", "SameSite=Lax"]
        if http_only:
            parts.append("HttpOnly")
        if self._is_production():
            parts.append("Secure")
        return "; ".join(parts)

    def _session_signing_secret(self) -> str:
        return os.environ.get(SESSION_SIGNING_SECRET_ENV, "").strip()

    def _login_password(self) -> str:
        return os.environ.get(WATCHDOG_PASSWORD_ENV, "").strip()

    def _generate_session_token(self) -> str:
        secret = self._session_signing_secret().encode("utf-8")
        nonce = secrets.token_urlsafe(24)
        expires_at = int(time.time()) + SESSION_MAX_AGE_SECONDS
        payload = f"{nonce}:{expires_at}".encode("utf-8")
        sig = hmac.new(secret, payload, hashlib.sha256).hexdigest()
        raw = f"{nonce}:{expires_at}:{sig}".encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("utf-8")

    def _is_authenticated(self) -> bool:
        token = self._get_cookie(SESSION_COOKIE)
        if not token:
            return False
        secret = self._session_signing_secret()
        if not secret:
            return False
        try:
            decoded = base64.urlsafe_b64decode(token.encode("utf-8")).decode("utf-8")
            nonce, expires_raw, signature = decoded.split(":", 2)
            expires_at = int(expires_raw)
        except Exception:
            return False
        expected_sig = hmac.new(secret.encode("utf-8"), f"{nonce}:{expires_at}".encode("utf-8"), hashlib.sha256).hexdigest()
        if not secrets.compare_digest(signature, expected_sig):
            return False
        return expires_at > int(time.time())

    def _require_auth(self, *, api: bool) -> bool:
        if not self._auth_enabled():
            return True
        if self._is_authenticated():
            return True
        if api:
            self._json_response({"error": "unauthorized"}, status=HTTPStatus.UNAUTHORIZED)
        else:
            self.send_response(HTTPStatus.FOUND)
            self.send_header("Location", "/login")
            self.end_headers()
        return False

    def _ensure_csrf_cookie(self) -> str:
        token = self._get_cookie(CSRF_COOKIE)
        if token:
            return token
        return secrets.token_urlsafe(32)

    def _validate_csrf(self, token: str) -> bool:
        if not self._auth_enabled():
            return True
        cookie_token = self._get_cookie(CSRF_COOKIE)
        return bool(cookie_token and token and secrets.compare_digest(cookie_token, token))

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)

        # Health check — must be first to ensure it is always reachable.
        if parsed.path == "/healthz":
            self._json_response({"status": "ok"})
            return

        if parsed.path == "/login":
            if not self._auth_enabled():
                self.send_response(HTTPStatus.FOUND)
                self.send_header("Location", "/")
                self.end_headers()
                return
            if self._is_authenticated():
                self.send_response(HTTPStatus.FOUND)
                self.send_header("Location", "/")
                self.end_headers()
                return
            csrf_token = self._ensure_csrf_cookie()
            self._serve_template("login.html", replacements={"{{error_block}}": "", "{{csrf_token}}": csrf_token}, extra_set_cookies=[self._build_cookie_header(CSRF_COOKIE, csrf_token, max_age=SESSION_MAX_AGE_SECONDS, http_only=False)])
            return

        if parsed.path in {"/", "/crawler", "/pulling", "/about", "/testbench", "/urls"}:
            if not self._require_auth(api=False):
                return
            template_name = "index.html" if parsed.path == "/" else f"{parsed.path.strip('/')}.html"
            self._serve_template(template_name)
            return
        if parsed.path == "/watchdog-fixture" or parsed.path.startswith("/watchdog-fixture/"):
            fixture_relative = parsed.path.removeprefix("/watchdog-fixture").lstrip("/")
            self._serve_fixture(fixture_relative)
            return
        if parsed.path.startswith("/static/"):
            self._serve_static(parsed.path.removeprefix("/static/"))
            return
        if parsed.path == "/api/domains":
            if not self._require_auth(api=True):
                return
            self._json_response({"items": _list_domains()})
            return
        if parsed.path == "/api/url-inventory":
            if not self._require_auth(api=True):
                return
            domain = parse_qs(parsed.query).get("domain", [""])[0]
            try:
                payload = read_seed_urls(validate_domain(domain))
            except ValueError as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            urls = [row.get("url", "") for row in payload.get("urls", []) if isinstance(row, dict)]
            self._json_response({"domain": domain, "urls": sorted(urls)})
            return
        if parsed.path == "/api/pulls":
            if not self._require_auth(api=True):
                return
            query = parse_qs(parsed.query)
            domain = query.get("domain", [""])[0]
            run_id = query.get("run_id", [""])[0]
            if not domain or not run_id:
                self._json_response({"error": "domain and run_id required"}, status=HTTPStatus.BAD_REQUEST)
                return
            if not _artifact_exists(domain, run_id, "collected_items.json"):
                self._json_response({"error": "collected_items artifact missing", "status": "not_ready"}, status=HTTPStatus.NOT_FOUND)
                return
            items = _read_json_safe(domain, run_id, "collected_items.json", [])
            universal_sections = _read_json_safe(domain, run_id, "universal_sections.json", [])
            decisions = _load_phase2_decisions(domain, run_id)
            decisions_by_item_url = {(str(row.get("item_id", "")), str(row.get("url", ""))): row for row in decisions}
            url_filter = query.get("url", [""])[0].strip().lower()
            state_filter = query.get("state", [""])[0].strip().lower()
            language_filter = query.get("language", [""])[0].strip().lower()
            viewport_filter = query.get("viewport_kind", [""])[0].strip().lower()
            tier_filter = query.get("user_tier", [""])[0].strip().lower()
            rows = []
            for row in items:
                if not isinstance(row, dict):
                    continue
                if url_filter and url_filter not in str(row.get("url", "")).lower():
                    continue
                if state_filter and state_filter != str(row.get("state", "")).lower():
                    continue
                if language_filter and language_filter != str(row.get("language", "")).lower():
                    continue
                if viewport_filter and viewport_filter != str(row.get("viewport_kind", "")).lower():
                    continue
                if tier_filter and tier_filter != str(row.get("user_tier") or "").lower():
                    continue
                decision = decisions_by_item_url.get((str(row.get("item_id", "")), str(row.get("url", ""))), {})
                rows.append({
                    "item_id": row.get("item_id", ""),
                    "url": row.get("url", ""),
                    "state": row.get("state", ""),
                    "language": row.get("language", ""),
                    "viewport_kind": row.get("viewport_kind", ""),
                    "user_tier": row.get("user_tier"),
                    "element_type": row.get("element_type", ""),
                    "text": row.get("text", ""),
                    "not_found": bool(row.get("not_found", False)),
                    "decision": decision.get("rule_type", ""),
                })
            for section in universal_sections if isinstance(universal_sections, list) else []:
                if not isinstance(section, dict):
                    continue
                section_id = str(section.get("section_id", "")).strip()
                if not section_id:
                    continue
                rows.append({
                    "item_id": f"universal-{section_id}",
                    "url": section.get("representative_url", ""),
                    "state": "universal",
                    "language": "en",
                    "viewport_kind": "any",
                    "user_tier": None,
                    "element_type": "universal_section",
                    "text": section.get("label", "universal section"),
                    "not_found": False,
                    "decision": "",
                })
            rows.sort(key=lambda item: item.get("item_id", ""))
            self._json_response({"rows": rows, "missing_universal_sections": not _artifact_exists(domain, run_id, "universal_sections.json")})
            return
        if parsed.path == "/api/rules":
            if not self._require_auth(api=True):
                return
            query = parse_qs(parsed.query)
            domain = query.get("domain", [""])[0]
            run_id = query.get("run_id", [""])[0]
            if not domain or not run_id:
                self._json_response({"error": "domain and run_id required"}, status=HTTPStatus.BAD_REQUEST)
                return
            rules = _load_phase2_decisions(domain, run_id)
            self._json_response({"rules": rules})
            return
        if parsed.path in {"/api/issues", "/api/issues/export"}:
            if not self._require_auth(api=True):
                return
            query = parse_qs(parsed.query)
            domain = query.get("domain", [""])[0]
            run_id = query.get("run_id", [""])[0]
            if not domain or not run_id:
                self._json_response({"error": "domain and run_id required"}, status=HTTPStatus.BAD_REQUEST)
                return
            if not _artifact_exists(domain, run_id, "issues.json"):
                self._json_response({"error": "issues artifact missing", "status": "not_ready"}, status=HTTPStatus.NOT_FOUND)
                return
            issues = _read_json_safe(domain, run_id, "issues.json", [])
            filtered = _filter_issues(issues if isinstance(issues, list) else [], query)
            if parsed.path.endswith("/export") and query.get("format", ["json"])[0].strip().lower() == "csv":
                encoded = _issues_to_csv(filtered).encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/csv; charset=utf-8")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)
                return
            self._json_response({"issues": filtered, "count": len(filtered)})
            return
        if parsed.path == "/api/issues/detail":
            if not self._require_auth(api=True):
                return
            query = parse_qs(parsed.query)
            domain = query.get("domain", [""])[0]
            run_id = query.get("run_id", [""])[0]
            issue_id = query.get("id", [""])[0]
            if not domain or not run_id or not issue_id:
                self._json_response({"error": "domain, run_id and id required"}, status=HTTPStatus.BAD_REQUEST)
                return
            if not _artifact_exists(domain, run_id, "issues.json"):
                self._json_response({"error": "issues artifact missing", "status": "not_ready"}, status=HTTPStatus.NOT_FOUND)
                return
            issues = _read_json_safe(domain, run_id, "issues.json", [])
            issue = next((i for i in issues if isinstance(i, dict) and str(i.get("id", "")) == issue_id), None)
            if issue is None:
                self._json_response({"error": "issue not found"}, status=HTTPStatus.NOT_FOUND)
                return
            evidence = issue.get("evidence", {}) if isinstance(issue.get("evidence"), dict) else {}
            item_id = str(evidence.get("item_id", ""))
            page_screens = _read_json_safe(domain, run_id, "page_screenshots.json", [])
            collected = _read_json_safe(domain, run_id, "collected_items.json", [])
            item = next((r for r in collected if isinstance(r, dict) and str(r.get("item_id", "")) == item_id), None)
            page = None
            if item is not None:
                page = next((p for p in page_screens if isinstance(p, dict) and p.get("page_id") == item.get("page_id")), None)
            self._json_response({
                "issue": issue,
                "drilldown": {
                    "screenshot_uri": (page or {}).get("storage_uri") or evidence.get("storage_uri", ""),
                    "page": page,
                    "element": item,
                    "artifact_refs": {
                        "issues": f"{domain}/{run_id}/issues.json",
                        "page_screenshots": f"{domain}/{run_id}/page_screenshots.json",
                        "collected_items": f"{domain}/{run_id}/collected_items.json",
                    },
                },
            })
            return

        if parsed.path == "/api/seed-urls":
            if not self._require_auth(api=True):
                return
            domain = parse_qs(parsed.query).get("domain", [""])[0]
            try:
                valid_domain = validate_domain(domain)
            except ValueError as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            try:
                payload = read_seed_urls(valid_domain)
            except Exception as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            self._json_response(payload)
            return
        if parsed.path == "/api/testbench/modules":
            if not self._require_auth(api=True):
                return
            self._json_response({"modules": get_modules()})
            return
        if parsed.path == "/api/recipes":
            if not self._require_auth(api=True):
                return
            domain = parse_qs(parsed.query).get("domain", [""])[0]
            try:
                valid_domain = validate_domain(domain)
                self._json_response({"recipes": list_recipes(valid_domain)})
            except ValueError as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        # Job status endpoint
        if parsed.path == "/api/capture/runs":
            if not self._require_auth(api=True):
                return
            domain = parse_qs(parsed.query).get("domain", [""])[0]
            try:
                self._json_response(_load_runs(validate_domain(domain)))
            except ValueError as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        if parsed.path == "/api/capture/contexts":
            if not self._require_auth(api=True):
                return
            query = parse_qs(parsed.query)
            domain = query.get("domain", [""])[0]
            run_id = query.get("run_id", [""])[0]
            if not domain or not run_id:
                self._json_response({"error": "domain and run_id required"}, status=HTTPStatus.BAD_REQUEST)
                return
            if not _artifact_exists(domain, run_id, "page_screenshots.json"):
                self._json_response({"error": "page_screenshots artifact missing", "status": "not_ready"}, status=HTTPStatus.NOT_FOUND)
                return
            pages = _read_json_safe(domain, run_id, "page_screenshots.json", [])
            elements = _read_json_safe(domain, run_id, "collected_items.json", [])
            by_page = {}
            for row in elements:
                page_id = row.get("page_id") if isinstance(row, dict) else None
                if not page_id:
                    continue
                by_page[page_id] = by_page.get(page_id, 0) + 1
            contexts = []
            for page in pages:
                if not isinstance(page, dict):
                    continue
                capture_context_id = _capture_context_id_from_page(domain, page)
                contexts.append({
                    "capture_context_id": capture_context_id,
                    "page_id": page.get("page_id"),
                    "url": page.get("url"),
                    "viewport_kind": page.get("viewport_kind"),
                    "state": page.get("state"),
                    "language": page.get("language"),
                    "user_tier": page.get("user_tier"),
                    "storage_uri": page.get("storage_uri"),
                    "elements_count": by_page.get(page.get("page_id"), 0),
                })
            self._json_response({"contexts": contexts})
            return
        if parsed.path == "/api/job":
            if not self._require_auth(api=True):
                return
            job_id = parse_qs(parsed.query).get("id", [""])[0]
            if job_id in _jobs:
                self._json_response(_jobs[job_id])
            else:
                self._json_response({"status": "not_found"}, status=HTTPStatus.NOT_FOUND)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def do_PUT(self) -> None:  # noqa: N802
        if not self._require_auth(api=True):
            return
        csrf_header = self.headers.get("X-CSRF-Token", "")
        if not self._validate_csrf(csrf_header):
            self._json_response({"error": "csrf validation failed"}, status=HTTPStatus.FORBIDDEN)
            return

        if self.path == "/api/seed-urls":
            payload = self._read_json_payload()
            domain = str(payload.get("domain", ""))
            urls_multiline = str(payload.get("urls_multiline", ""))
            try:
                valid_domain = validate_domain(domain)
                parsed_urls = parse_seed_urls_with_errors(urls_multiline)
                saved = write_seed_urls(valid_domain, parsed_urls["urls"])
                saved["validation_errors"] = parsed_urls["errors"]
                _register_domain(valid_domain)
            except ValueError as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            except Exception as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            self._json_response(saved)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/login":
            if not self._auth_enabled():
                self.send_response(HTTPStatus.FOUND)
                self.send_header("Location", "/")
                self.end_headers()
                return
            form = self._read_form_payload()
            password = str(form.get("password", "")).strip()
            csrf_token = str(form.get("csrf_token", "")).strip()

            if not self._validate_csrf(csrf_token):
                refreshed_csrf = self._ensure_csrf_cookie()
                self._serve_template(
                    "login.html",
                    status=HTTPStatus.FORBIDDEN,
                    replacements={
                        "{{error_block}}": '<div class="error">❌ Security error (CSRF). Please try again.</div>',
                        "{{csrf_token}}": refreshed_csrf,
                    },
                    extra_set_cookies=[self._build_cookie_header(CSRF_COOKIE, refreshed_csrf, max_age=SESSION_MAX_AGE_SECONDS, http_only=False)],
                )
                return

            expected_password = self._login_password()
            signing_secret = self._session_signing_secret()
            if not expected_password or not signing_secret:
                self._json_response(
                    {
                        "error": (
                            f"missing required environment variable: {WATCHDOG_PASSWORD_ENV} or {SESSION_SIGNING_SECRET_ENV}"
                        )
                    },
                    status=HTTPStatus.INTERNAL_SERVER_ERROR,
                )
                return

            if secrets.compare_digest(password, expected_password):
                session_token = self._generate_session_token()
                new_csrf = secrets.token_urlsafe(32)
                self.send_response(HTTPStatus.FOUND)
                self.send_header("Location", "/")
                self.send_header("Set-Cookie", self._build_cookie_header(SESSION_COOKIE, session_token, max_age=SESSION_MAX_AGE_SECONDS, http_only=True))
                self.send_header("Set-Cookie", self._build_cookie_header(CSRF_COOKIE, new_csrf, max_age=SESSION_MAX_AGE_SECONDS, http_only=False))
                self.end_headers()
                return

            refreshed_csrf = self._ensure_csrf_cookie()
            self._serve_template(
                "login.html",
                status=HTTPStatus.UNAUTHORIZED,
                replacements={
                    "{{error_block}}": '<div class="error">❌ Invalid password</div>',
                    "{{csrf_token}}": refreshed_csrf,
                },
                extra_set_cookies=[self._build_cookie_header(CSRF_COOKIE, refreshed_csrf, max_age=SESSION_MAX_AGE_SECONDS, http_only=False)],
            )
            return

        if self.path == "/logout":
            if not self._auth_enabled():
                self._json_response({"status": "auth disabled"})
                return
            if not self._require_auth(api=False):
                return
            csrf_header = self.headers.get("X-CSRF-Token", "")
            if not self._validate_csrf(csrf_header):
                self._json_response({"error": "csrf validation failed"}, status=HTTPStatus.FORBIDDEN)
                return
            self.send_response(HTTPStatus.FOUND)
            self.send_header("Location", "/login")
            self.send_header("Set-Cookie", self._expire_cookie_header(SESSION_COOKIE, http_only=True))
            self.send_header("Set-Cookie", self._expire_cookie_header(CSRF_COOKIE, http_only=False))
            self.end_headers()
            return

        if not self._require_auth(api=True):
            return
        csrf_header = self.headers.get("X-CSRF-Token", "")
        if not self._validate_csrf(csrf_header):
            self._json_response({"error": "csrf validation failed"}, status=HTTPStatus.FORBIDDEN)
            return

        if self.path == "/api/seed-urls/add":
            payload = self._read_json_payload()
            domain = str(payload.get("domain", ""))
            urls_multiline = str(payload.get("urls_multiline", ""))
            try:
                valid_domain = validate_domain(domain)
                parsed_urls = parse_seed_urls_with_errors(urls_multiline)
                incoming = parsed_urls["urls"]
                existing = read_seed_urls(valid_domain)
                existing_urls = {str(row.get("url", "")) for row in existing.get("urls", []) if isinstance(row, dict) and row.get("url")}
                merged = sorted(existing_urls | set(incoming))
                saved = write_seed_urls(valid_domain, merged)
                _register_domain(valid_domain)
            except ValueError as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            except Exception as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            saved["validation_errors"] = parsed_urls["errors"]
            self._json_response(saved)
            return

        if self.path == "/api/seed-urls/delete":
            payload = self._read_json_payload()
            domain = str(payload.get("domain", ""))
            try:
                valid_domain = validate_domain(domain)
                normalized = normalize_seed_url(str(payload.get("url", "")))
                if normalized is None:
                    raise ValueError("url is required")
                existing = read_seed_urls(valid_domain)
                remaining = [
                    str(row.get("url"))
                    for row in existing.get("urls", [])
                    if isinstance(row, dict) and row.get("url") and str(row.get("url")) != normalized
                ]
                saved = write_seed_urls(valid_domain, remaining)
                _register_domain(valid_domain)
            except ValueError as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            except Exception as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            self._json_response(saved)
            return

        if self.path == "/api/seed-urls/clear":
            payload = self._read_json_payload()
            domain = str(payload.get("domain", ""))
            try:
                valid_domain = validate_domain(domain)
                saved = write_seed_urls(valid_domain, [])
                _register_domain(valid_domain)
            except ValueError as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            except Exception as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            self._json_response(saved)
            return


        if self.path == "/api/recipes/upsert":
            payload = self._read_json_payload()
            domain = str(payload.get("domain", ""))
            recipe = payload.get("recipe")
            try:
                valid_domain = validate_domain(domain)
                if not isinstance(recipe, dict):
                    raise ValueError("recipe object is required")
                saved = upsert_recipe(valid_domain, recipe)
                _register_domain(valid_domain)
                self._json_response({"recipe": saved, "recipes": list_recipes(valid_domain)})
            except ValueError as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            except Exception as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if self.path == "/api/recipes/delete":
            payload = self._read_json_payload()
            domain = str(payload.get("domain", ""))
            recipe_id = str(payload.get("recipe_id", "")).strip()
            try:
                valid_domain = validate_domain(domain)
                if not recipe_id:
                    raise ValueError("recipe_id is required")
                recipes = delete_recipe(valid_domain, recipe_id)
                self._json_response({"recipes": recipes})
            except ValueError as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            except Exception as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if self.path == "/api/seed-urls/row-upsert":
            payload = self._read_json_payload()
            domain = str(payload.get("domain", ""))
            row = payload.get("row")
            try:
                valid_domain = validate_domain(domain)
                if not isinstance(row, dict):
                    raise ValueError("row object is required")
                existing = read_seed_urls(valid_domain)
                rows = [r for r in existing.get("urls", []) if isinstance(r, dict)]
                normalized_url = normalize_seed_url(str(row.get("url", "")))
                if normalized_url is None:
                    raise ValueError("row.url is required")
                merged = [r for r in rows if str(r.get("url")) != normalized_url]
                merged.append({
                    "url": normalized_url,
                    "description": row.get("description"),
                    "recipe_ids": row.get("recipe_ids", []),
                    "active": bool(row.get("active", True)),
                })
                saved = write_seed_rows(valid_domain, merged)
                _register_domain(valid_domain)
                self._json_response(saved)
            except ValueError as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            except Exception as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if self.path == "/api/capture/plan":
            payload = self._read_json_payload()
            try:
                domain = validate_domain(str(payload.get("domain", "")).strip())
                languages = sorted({str(v).strip() for v in payload.get("languages", []) if str(v).strip()})
                viewports = sorted({str(v).strip() for v in payload.get("viewports", []) if str(v).strip()})
                tiers = sorted({str(v).strip() for v in payload.get("user_tiers", []) if str(v).strip()}) or [""]
                include_recipes = bool(payload.get("include_recipes", False))
                if not languages or not viewports:
                    raise ValueError("languages and viewports are required")
                seed_payload = read_seed_urls(domain)
                planning_rows = []
                for row in seed_payload.get("urls", []):
                    if not isinstance(row, dict) or not row.get("active", True):
                        continue
                    recipe_ids = list(row.get("recipe_ids", [])) if include_recipes else []
                    planning_rows.append({"url": row.get("url"), "recipe_ids": recipe_ids})
                recipes = load_recipes_for_planner(domain)
                output = _expand_capture_plan(domain, planning_rows, languages, viewports, tiers, recipes)
                self._json_response({"jobs": output, "count": len(output)})
            except ValueError as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            except Exception as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if self.path == "/api/capture/start":
            payload = self._read_json_payload()
            domain = str(payload.get("domain", "")).strip()
            run_id = str(payload.get("run_id", "")).strip() or str(uuid.uuid4())
            language = str(payload.get("language", "en")).strip() or "en"
            viewport_kind = str(payload.get("viewport_kind", "desktop")).strip() or "desktop"
            state = str(payload.get("state", "guest")).strip() or "guest"
            user_tier = payload.get("user_tier") or None
            runtime_payload = {"domain": domain, "run_id": run_id, "language": language, "viewport_kind": viewport_kind, "state": state, "user_tier": user_tier}
            try:
                load_phase1_runtime_config(runtime_payload)
                _register_domain(validate_domain(domain))
                job_id = f"phase1-{run_id}-{language}-{viewport_kind}-{state}"
                _upsert_job_status(domain, run_id, {"job_id": job_id, "status": "queued", "context": runtime_payload})
                t = threading.Thread(target=_run_phase1_async, args=(job_id, runtime_payload), daemon=True)
                t.start()
                self._json_response({"status": "started", "job_id": job_id, "run_id": run_id})
            except ValueError as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            except Exception as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if self.path == "/api/capture/review":
            payload = self._read_json_payload()
            try:
                result = _persist_capture_review(payload)
                self._json_response(result)
            except ValueError as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            except Exception as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if self.path == "/api/capture/rerun":
            payload = self._read_json_payload()
            try:
                runtime_payload = _parse_rerun_payload(payload)
                from pipeline.run_phase1 import build_exact_context_job

                job = build_exact_context_job(
                    domain=runtime_payload["domain"],
                    url=runtime_payload["url"],
                    language=runtime_payload["language"],
                    viewport_kind=runtime_payload["viewport_kind"],
                    state=runtime_payload["state"],
                    user_tier=runtime_payload["user_tier"],
                )
                job_id = f"rerun-{runtime_payload['run_id']}-{runtime_payload['language']}-{runtime_payload['state']}"
                _upsert_job_status(runtime_payload["domain"], runtime_payload["run_id"], {"job_id": job_id, "status": "queued", "context": runtime_payload, "type": "rerun"})
                t = threading.Thread(target=_run_rerun_async, args=(job_id, runtime_payload), daemon=True)
                t.start()
                self._json_response({"status": "started", "job_id": job_id, "resolved_context": {
                    "url": job.context.url,
                    "viewport_kind": job.context.viewport_kind,
                    "state": job.context.state,
                    "user_tier": job.context.user_tier,
                    "language": job.context.language,
                }, "job_count": 1})
            except ValueError as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            except Exception as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if self.path == "/api/rules":
            payload = self._read_json_payload()
            domain = str(payload.get("domain", "")).strip()
            run_id = str(payload.get("run_id", "")).strip()
            item_id = str(payload.get("item_id", "")).strip()
            url = str(payload.get("url", "")).strip()
            rule_type = _to_rule_type(str(payload.get("rule_type", "")).strip())
            allowed = {"IGNORE_ENTIRE_ELEMENT", "MASK_VARIABLE", "ALWAYS_COLLECT"}
            if not domain or not run_id or not item_id or not url or rule_type not in allowed:
                self._json_response({"status": "error", "message": "domain, run_id, item_id, url and valid rule_type required"}, status=HTTPStatus.BAD_REQUEST)
                return
            decision = {
                "capture_context_id": str(payload.get("capture_context_id", "")),
                "item_id": item_id,
                "url": url,
                "state": str(payload.get("state", "")),
                "language": str(payload.get("language", "")),
                "viewport_kind": str(payload.get("viewport_kind", "")),
                "user_tier": payload.get("user_tier"),
                "rule_type": rule_type,
                "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            _upsert_phase2_decision(domain, run_id, decision)
            phase2_applied = True
            phase2_error = ""
            try:
                from pipeline.run_phase2 import run as phase2_run
                phase2_run(domain=domain, run_id=run_id, item_id=item_id, url=url, rule_type=rule_type, note=None)
            except Exception as exc:
                phase2_applied = False
                phase2_error = str(exc)
            self._json_response({"status": "ok", "decision": decision, "phase2_applied": phase2_applied, "phase2_error": phase2_error})
            return

        # Phase 0 trigger — real pipeline
        if self.path == "/api/phase0/run":
            payload = self._read_json_payload()
            domain = payload.get("domain", "").strip()
            if not domain:
                self._json_response({"status": "error", "message": "domain required"}, status=HTTPStatus.BAD_REQUEST)
                return
            run_id = payload.get("run_id") or str(uuid.uuid4())
            job_id = f"phase0-{run_id}"
            t = threading.Thread(
                target=_run_phase0_async, args=(job_id, domain, run_id), daemon=True
            )
            t.start()
            self._json_response({"status": "started", "job_id": job_id, "run_id": run_id})
            return

        # Phase 1 trigger — real pipeline
        if self.path == "/api/phase1/run":
            payload = self._read_json_payload()
            domain = payload.get("domain", "").strip()
            run_id = payload.get("run_id", "").strip()
            if not domain or not run_id:
                self._json_response({"status": "error", "message": "domain and run_id required"}, status=HTTPStatus.BAD_REQUEST)
                return
            runtime_payload = {
                "domain": domain,
                "run_id": run_id,
                "language": payload.get("language", "en"),
                "viewport_kind": payload.get("viewport_kind", "desktop"),
                "state": payload.get("state", "guest"),
                "user_tier": payload.get("user_tier") or None,
            }
            try:
                config = load_phase1_runtime_config(runtime_payload)
            except ValueError as exc:
                self._json_response({"status": "error", "message": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            job_id = f"phase1-{config.run_id}-{config.language}-{config.viewport_kind}-{config.state}"
            _register_domain(domain)
            _upsert_job_status(domain, run_id, {"job_id": job_id, "status": "queued", "context": runtime_payload})
            t = threading.Thread(
                target=_run_phase1_async,
                args=(job_id, runtime_payload),
                daemon=True,
            )
            t.start()
            self._json_response({"status": "started", "job_id": job_id, "run_id": run_id})
            return

        # Phase 2 — save a single template rule to GCS
        if self.path == "/api/phase2/rule":
            payload = self._read_json_payload()
            domain = payload.get("domain", "").strip()
            run_id = payload.get("run_id", "").strip()
            item_id = payload.get("item_id", "").strip()
            url = payload.get("url", "").strip()
            rule_type = payload.get("rule_type", "").strip()
            note = payload.get("note") or None
            allowed = {"IGNORE_ENTIRE_ELEMENT", "MASK_VARIABLE", "ALWAYS_COLLECT"}
            if not all([domain, run_id, item_id, url]) or rule_type not in allowed:
                self._json_response({"status": "error", "message": "domain, run_id, item_id, url and valid rule_type required"}, status=HTTPStatus.BAD_REQUEST)
                return
            try:
                from pipeline.run_phase2 import run as phase2_run
                rule = phase2_run(domain=domain, run_id=run_id, item_id=item_id, url=url, rule_type=rule_type, note=note)
                self._json_response({"status": "ok", "rule": rule})
            except Exception as exc:
                self._json_response({"status": "error", "message": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        # Testbench module run endpoint
        if self.path == "/api/testbench/run":
            payload = self._read_json_payload()
            module_id = str(payload.get("module_id", "")).strip()
            case_key = payload.get("case_key") or payload.get("case_id")
            inline_payload = payload.get("input") if isinstance(payload.get("input"), dict) else None
            if not module_id:
                self._json_response({"status": "error", "message": "module_id required"}, status=HTTPStatus.BAD_REQUEST)
                return
            result = run_module_test(module_id, case_key if isinstance(case_key, str) else None, inline_payload)
            self._json_response(result)
            return

        # Phase 3 trigger — EN Reference Build
        if self.path == "/api/phase3/run":
            payload = self._read_json_payload()
            domain = payload.get("domain", "").strip()
            run_id = payload.get("run_id", "").strip()
            if not domain or not run_id:
                self._json_response({"status": "error", "message": "domain and run_id required"}, status=HTTPStatus.BAD_REQUEST)
                return
            job_id = f"phase3-{run_id}"
            t = threading.Thread(
                target=_run_phase3_async, args=(job_id, domain, run_id), daemon=True
            )
            t.start()
            self._json_response({"status": "started", "job_id": job_id, "run_id": run_id})
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def _serve_template(
        self,
        name: str,
        *,
        status: HTTPStatus = HTTPStatus.OK,
        replacements: dict[str, str] | None = None,
        extra_set_cookies: list[str] | None = None,
    ) -> None:
        path = TEMPLATES_DIR / name
        if not path.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "Template not found")
            return
        html = self._read_template_cached(path)
        html = re.sub(
            r"(<body\b[^>]*>)",
            r"\1\n<script>document.documentElement.classList.add('i18n-loading');</script>",
            html,
            count=1,
            flags=re.IGNORECASE,
        )
        loader_html = '<div class="i18n-loader-overlay" aria-hidden="true"><div class="i18n-loader"></div></div>'
        html = html.replace("</body>", f"  {loader_html}\n</body>", 1)
        header_path = TEMPLATES_DIR / "_header.html"
        header_html = self._read_template_cached(header_path) if header_path.exists() else ""
        html = html.replace("{{header}}", header_html)
        html = html.replace(
            "{{logout_button}}",
            '<button id="logoutButton" type="button" data-i18n="nav.logout">Logout</button>' if self._auth_enabled() else "",
        )
        if replacements:
            for key, value in replacements.items():
                html = html.replace(key, value)
        data = html.encode("utf-8")
        self.send_response(status)
        if extra_set_cookies:
            for set_cookie in extra_set_cookies:
                self.send_header("Set-Cookie", set_cookie)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _serve_static(self, relative_path: str) -> None:
        path = STATIC_DIR / relative_path
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Static file not found")
            return
        content_type = self._get_content_type(path)
        self._send_file(path, content_type)

    def _serve_fixture(self, relative_path: str) -> None:
        normalized = relative_path.strip("/")
        if not normalized:
            normalized = "index.html"
        elif not Path(normalized).suffix:
            normalized = f"{normalized}/index.html"

        path = FIXTURE_DIR / normalized
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Fixture file not found")
            return
        self._send_file(path, self._get_content_type(path))

    def _get_content_type(self, path: Path) -> str:
        content_type = "text/plain; charset=utf-8"
        if path.suffix == ".html":
            content_type = "text/html; charset=utf-8"
        elif path.suffix == ".css":
            content_type = "text/css; charset=utf-8"
        elif path.suffix == ".js":
            content_type = "application/javascript; charset=utf-8"
        elif path.suffix == ".svg":
            content_type = "image/svg+xml"
        elif path.suffix == ".json":
            content_type = "application/json; charset=utf-8"
        return content_type

    def _send_file(self, path: Path, content_type: str) -> None:
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json_response(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _read_json_payload(self) -> dict[str, str]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return {}
        if not isinstance(payload, dict):
            return {}
        return payload

    def _read_form_payload(self) -> dict[str, str]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        parsed = parse_qs(raw)
        return {key: values[0] for key, values in parsed.items() if values}

    def log_message(self, format, *args):  # noqa: A002
        pass  # suppress default request logging for cleaner Cloud Run logs


def run(host: str = "0.0.0.0", port: int = 8080) -> None:
    server = ThreadingHTTPServer((host, port), SkeletonHandler)
    print(f"Polyglot Watchdog UI running on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    run(port=port)
