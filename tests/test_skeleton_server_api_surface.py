"""Smoke test for app.skeleton_server import compatibility.

The symbol list intentionally mirrors public imports used across tests/test_*.py
plus additional compatibility names relied on via monkeypatch.
"""

from __future__ import annotations

import app.skeleton_server as skeleton_server


PUBLIC_TEST_API_SYMBOLS: dict[str, bool] = {
    "SkeletonHandler": True,
    "_build_check_languages_target_url": True,
    "_capture_context_id_from_page": True,
    "_check_languages_run_domains": True,
    "_check_languages_source_hashes": True,
    "_decision_key": True,
    "_en_standard_display_name_today": True,
    "_expand_capture_plan": True,
    "_filter_issues": True,
    "_issues_to_csv": True,
    "_jobs": False,
    "_load_check_language_runs": True,
    "_load_phase2_decisions": True,
    "_normalize_check_languages_domain": True,
    "_parse_gs_uri_safe": True,
    "_parse_rerun_payload": True,
    "_persist_capture_review": True,
    "_persist_check_languages_failure_artifacts": True,
    "_prepare_check_languages_async": True,
    "_replay_scope_from_reference_run": True,
    "_run_check_languages_async": True,
    "_run_check_languages_llm_async": True,
    "_stable_json_hash": True,
    "_to_rule_type": True,
    "_upsert_job_status": True,
    "_upsert_phase2_decision": True,
    "_workflow_status_payload": True,
}


def test_skeleton_server_api_surface_symbols_exist_with_expected_callability() -> None:
    for symbol_name, should_be_callable in PUBLIC_TEST_API_SYMBOLS.items():
        assert hasattr(skeleton_server, symbol_name), f"missing symbol: {symbol_name}"
        value = getattr(skeleton_server, symbol_name)
        assert callable(value) is should_be_callable, f"unexpected callable status for {symbol_name}"
