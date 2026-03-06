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

TEMPLATES_DIR = BASE_DIR / "web" / "templates"
STATIC_DIR = BASE_DIR / "web" / "static"

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


def _run_phase1_async(job_id: str, domain: str, run_id: str, language: str,
                     viewport_kind: str, state: str, user_tier) -> None:
    """Run Phase 1 in a background thread."""
    _jobs[job_id] = {"status": "running", "phase": "1", "domain": domain, "run_id": run_id}
    try:
        from pipeline.run_phase1 import run as phase1_run
        phase1_run(
            domain=domain,
            run_id=run_id,
            language=language,
            viewport_kind=viewport_kind,
            state=state,
            user_tier=user_tier,
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
        if parsed.path in {"/", "/crawler", "/pulling", "/about"}:
            template_name = "index.html" if parsed.path == "/" else f"{parsed.path.strip('/')}.html"
            self._serve_template(template_name)
            return
        if parsed.path.startswith("/static/"):
            self._serve_static(parsed.path.removeprefix("/static/"))
            return
        if parsed.path == "/healthz":
            self._json_response({"status": "ok"})
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
        # Job status endpoint
        if parsed.path == "/api/job":
            job_id = parse_qs(parsed.query).get("id", [""])[0]
            if job_id in _jobs:
                self._json_response(_jobs[job_id])
            else:
                self._json_response({"status": "not_found"}, status=HTTPStatus.NOT_FOUND)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def do_POST(self) -> None:  # noqa: N802
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
            language = payload.get("language", "en")
            viewport_kind = payload.get("viewport_kind", "desktop")
            state = payload.get("state", "guest")
            user_tier = payload.get("user_tier") or None
            job_id = f"phase1-{run_id}-{language}-{viewport_kind}-{state}"
            t = threading.Thread(
                target=_run_phase1_async,
                args=(job_id, domain, run_id, language, viewport_kind, state, user_tier),
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
        content_type = "text/plain; charset=utf-8"
        if path.suffix == ".css":
            content_type = "text/css; charset=utf-8"
        elif path.suffix == ".js":
            content_type = "application/javascript; charset=utf-8"
        elif path.suffix == ".svg":
            content_type = "image/svg+xml"
        self._send_file(path, content_type)

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
