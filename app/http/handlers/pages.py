from __future__ import annotations

from urllib.parse import parse_qs


def handle_get(handler: object, parsed) -> bool:
    if parsed.path == "/check-languages":
        if not handler._require_auth(api=False):
            return True
        handler._serve_check_languages_page(parse_qs(parsed.query))
        return True
    if parsed.path == "/result-files":
        if not handler._require_auth(api=False):
            return True
        handler._serve_result_files_page(parse_qs(parsed.query))
        return True

    page_templates = {
        "/": "index.html",
        "/crawler": "crawler.html",
        "/pulling": "pulling.html",
        "/about": "about.html",
        "/testbench": "testbench.html",
        "/urls": "urls.html",
        "/runs": "runs.html",
        "/workflow": "workflow.html",
        "/contexts": "contexts.html",
        "/issues/detail": "issues/detail.html",
    }
    if parsed.path == "/pulls":
        if not handler._require_auth(api=False):
            return True
        handler._serve_pulls_page(parse_qs(parsed.query))
        return True
    if parsed.path in page_templates:
        if not handler._require_auth(api=False):
            return True
        handler._serve_template(page_templates[parsed.path])
        return True
    if parsed.path == "/watchdog-fixture" or parsed.path.startswith("/watchdog-fixture/"):
        fixture_relative = parsed.path.removeprefix("/watchdog-fixture").lstrip("/")
        handler._serve_fixture(fixture_relative)
        return True
    if parsed.path in {"/favicon.ico", "/favicon.png"}:
        handler._serve_favicon()
        return True
    if parsed.path.startswith("/static/"):
        handler._serve_static(parsed.path.removeprefix("/static/"))
        return True
    return False
