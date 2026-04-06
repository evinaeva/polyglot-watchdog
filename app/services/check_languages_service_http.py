from __future__ import annotations

"""HTTP-facing orchestration wrappers for check-languages flow.

This module is intended to host request/response orchestration logic that was
historically embedded in ``skeleton_server.py``.
"""


def start_check_languages(handler, payload: dict[str, str]) -> None:
    handler._start_check_languages(payload)


def serve_check_languages_page(handler, query: dict[str, list[str]]) -> None:
    handler._serve_check_languages_page(query)


def prepare_check_languages_async(runner, job_id: str, domain: str, en_run_id: str, target_language: str, target_run_id: str, target_url: str) -> None:
    runner(job_id, domain, en_run_id, target_language, target_run_id, target_url)


def run_check_languages_async(runner, job_id: str, domain: str, en_run_id: str, target_language: str, target_run_id: str, target_url: str) -> None:
    runner(job_id, domain, en_run_id, target_language, target_run_id, target_url)


def run_check_languages_llm_async(runner, job_id: str, domain: str, en_run_id: str, target_language: str, target_run_id: str, target_url: str) -> None:
    runner(job_id, domain, en_run_id, target_language, target_run_id, target_url)
