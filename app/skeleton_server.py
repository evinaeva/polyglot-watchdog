"""Minimal deterministic skeleton UI server for Polyglot Watchdog.

Phase 0 and Phase 1 are wired to real pipeline modules.
Phase 2 (template_rules) and Phase 3 (eligible_dataset) are wired to real pipeline modules.
Other phases remain as stubs or mock data.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# Ensure project root is on sys.path for pipeline imports
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.recipes import delete_recipe, list_recipes, upsert_recipe
from app.seed_urls import (
    normalize_seed_url,
    parse_seed_urls,
    read_seed_urls,
    validate_domain,
    write_seed_urls,
)
from app.testbench import get_modules, run_module_test
from pipeline.interactive_capture import GCSArtifactWriter
from pipeline.runtime_config import load_phase1_runtime_config

TEMPLATES_DIR = BASE_DIR / "web" / "templates"
STATIC_DIR = BASE_DIR / "web" / "static"
FIXTURE_DIR = STATIC_DIR / "watchdog-fixture"

MOCK_DOMAINS = ["de.example.com", "en.example.com", "fr.example.com"]
MOCK_URL_INVENTORY = {
    "en.example.com": [
        "https://en.example.com/",
        "https://en.example.com/catalog",
        "https://en.example.com/contact",
    ],
    "fr.example.com": [
        "https://fr.example.com/",
        "https://fr.example.com/catalog",
    ],
}

MOCK_PULLS = [
    {
        "item_id": f"item-{index:04d}",
        "url": f"https://en.example.com/catalog/item-{index:04d}",
        "element_type": "img" if index % 4 == 0 else "button" if index % 4 == 1 else "input" if index % 4 == 2 else "text",
        "text": f"Sample content line  {index:04d}",
        "screenshot_thumbnail": "/static/mock-screenshot.svg",
        "screenshot_full": "/static/mock-screenshot.svg",
        "decision": "",
    }
    for index in range(1, 46)
]

MOCK_ISSUES = [
    {
        "id": "issue-0001",
        "category": "SPELLING",
        "message": "Potential typo in CTA button.",
        "url": "https://fr.example.com/catalog",
    },
    {
        "id": "issue-0002",
        "category": "GRAMMAR",
        "message": "Sentence agreement mismatch in product details.",
        "url": "https://de.example.com/catalog",
    },
]

RULE_DECISIONS: dict[str, str] = {}

# In-memory job status store (cleared on restart — for UI feedback only)
_jobs: dict[str, dict] = {}


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
    required = ["domain", "run_id", "url", "viewport_kind", "state", "language"]
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
    except Exception as exc:
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = str(exc)


def _run_phase1_async(job_id: str, runtime_payload: dict) -> None:
    """Run Phase 1 in a background thread."""
    _jobs[job_id] = {"status": "running", "phase": "1", "domain": runtime_payload.get("domain"), "run_id": runtime_payload.get("run_id")}
    try:
        from pipeline.run_phase1 import run_with_config

        config = load_phase1_runtime_config(runtime_payload)
        run_with_config(config)
        _jobs[job_id]["status"] = "done"
    except Exception as exc:
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = str(exc)


def _run_rerun_async(job_id: str, runtime_payload: dict) -> None:
    _jobs[job_id] = {"status": "running", "phase": "rerun", "domain": runtime_payload.get("domain"), "run_id": runtime_payload.get("run_id")}
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
        )
        _jobs[job_id]["status"] = "done"
    except Exception as exc:
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = str(exc)


def _run_phase3_async(job_id: str, domain: str, run_id: str) -> None:
    """Run Phase 3 in a background thread."""
    _jobs[job_id] = {"status": "running", "phase": "3", "domain": domain, "run_id": run_id}
    try:
        from pipeline.run_phase3 import run as phase3_run
        phase3_run(domain=domain, run_id=run_id)
        _jobs[job_id]["status"] = "done"
    except Exception as exc:
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = str(exc)


class SkeletonHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)

        # Health check — must be first to ensure it is always reachable.
        if parsed.path == "/healthz":
            self._json_response({"status": "ok"})
            return

        if parsed.path in {"/", "/crawler", "/pulling", "/about", "/testbench", "/urls"}:
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
            self._json_response({"items": sorted(MOCK_DOMAINS)})
            return
        if parsed.path == "/api/url-inventory":
            domain = parse_qs(parsed.query).get("domain", ["en.example.com"])[0]
            urls = sorted(MOCK_URL_INVENTORY.get(domain, []))
            self._json_response({"domain": domain, "urls": urls})
            return
        if parsed.path == "/api/pulls":
            rows = []
            for row in sorted(MOCK_PULLS, key=lambda item: item["item_id"]):
                merged = dict(row)
                merged["decision"] = RULE_DECISIONS.get(row["item_id"], row["decision"])
                rows.append(merged)
            self._json_response({"rows": rows})
            return
        if parsed.path == "/api/rules":
            rules = [
                {
                    "rule_id": f"rule-{item_id}",
                    "item_id": item_id,
                    "rule_type": rule_type,
                    "url": next((row["url"] for row in MOCK_PULLS if row["item_id"] == item_id), ""),
                }
                for item_id, rule_type in sorted(RULE_DECISIONS.items(), key=lambda item: item[0])
            ]
            self._json_response({"rules": rules})
            return
        if parsed.path == "/api/issues":
            query = parse_qs(parsed.query)
            has_filters = any(value for values in query.values() for value in values if value.strip())
            issues = sorted(MOCK_ISSUES, key=lambda issue: issue["id"]) if has_filters else []
            self._json_response({"issues": issues})
            return
        if parsed.path == "/api/seed-urls":
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
            self._json_response({"modules": get_modules()})
            return
        if parsed.path == "/api/recipes":
            domain = parse_qs(parsed.query).get("domain", [""])[0]
            try:
                valid_domain = validate_domain(domain)
                self._json_response({"recipes": list_recipes(valid_domain)})
            except ValueError as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        # Job status endpoint
        if parsed.path == "/api/job":
            job_id = parse_qs(parsed.query).get("id", [""])[0]
            if job_id in _jobs:
                self._json_response(_jobs[job_id])
            else:
                self._json_response({"status": "not_found"}, status=HTTPStatus.NOT_FOUND)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def do_PUT(self) -> None:  # noqa: N802
        if self.path == "/api/seed-urls":
            payload = self._read_json_payload()
            domain = str(payload.get("domain", ""))
            urls_multiline = str(payload.get("urls_multiline", ""))
            try:
                valid_domain = validate_domain(domain)
                urls = parse_seed_urls(urls_multiline)
                saved = write_seed_urls(valid_domain, urls)
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
        if self.path == "/api/seed-urls/add":
            payload = self._read_json_payload()
            domain = str(payload.get("domain", ""))
            urls_multiline = str(payload.get("urls_multiline", ""))
            try:
                valid_domain = validate_domain(domain)
                incoming = parse_seed_urls(urls_multiline)
                existing = read_seed_urls(valid_domain)
                existing_urls = {str(row.get("url", "")) for row in existing.get("urls", []) if isinstance(row, dict) and row.get("url")}
                merged = sorted(existing_urls | set(incoming))
                saved = write_seed_urls(valid_domain, merged)
            except ValueError as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            except Exception as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                return
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
            item_id = payload.get("item_id", "")
            rule_type = payload.get("rule_type", "")
            allowed = {"IGNORE_ENTIRE_ELEMENT", "MASK_VARIABLE", "ALWAYS_COLLECT"}
            if item_id and rule_type in allowed:
                RULE_DECISIONS[item_id] = rule_type
                self._json_response({"status": "ok", "item_id": item_id, "rule_type": rule_type})
                return
            self._json_response({"status": "error", "message": "invalid payload"}, status=HTTPStatus.BAD_REQUEST)
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
                # Also update in-memory decisions for UI consistency
                RULE_DECISIONS[item_id] = rule_type
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

    def _serve_template(self, name: str) -> None:
        path = TEMPLATES_DIR / name
        if not path.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "Template not found")
            return
        self._send_file(path, "text/html; charset=utf-8")

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

    def log_message(self, format, *args):  # noqa: A002
        pass  # suppress default request logging for cleaner Cloud Run logs


def run(host: str = "0.0.0.0", port: int = 8080) -> None:
    server = ThreadingHTTPServer((host, port), SkeletonHandler)
    print(f"Polyglot Watchdog UI running on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    run(port=port)
