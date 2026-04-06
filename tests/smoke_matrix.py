from __future__ import annotations

from dataclasses import dataclass


EXISTING_COVERAGE_TESTS: tuple[str, ...] = (
    "tests/test_stage_a_read_routes_api.py",
    "tests/test_stage_b_operator_flow_api.py",
    "tests/test_stage_c_operator_workflow.py",
    "tests/test_check_languages_page.py",
    "tests/test_workflow_happy_path_e2e.py",
    "tests/test_operator_ui_runtime_regressions.py",
)


@dataclass(frozen=True)
class SmokeRoute:
    category: str
    method: str
    path: str
    expected_json_keys: tuple[str, ...] = ()
    covered_by: tuple[str, ...] = ()


_STAGE_A = ("tests/test_stage_a_read_routes_api.py",)
_STAGE_B = ("tests/test_stage_b_operator_flow_api.py",)
_STAGE_C = ("tests/test_stage_c_operator_workflow.py",)
_CHECK_LANG = ("tests/test_check_languages_page.py",)
_E2E = ("tests/test_workflow_happy_path_e2e.py",)
_UI = ("tests/test_operator_ui_runtime_regressions.py",)


SMOKE_MATRIX: tuple[SmokeRoute, ...] = (
    SmokeRoute(category="pages", method="GET", path="/", covered_by=_STAGE_C + _UI),
    SmokeRoute(category="pages", method="GET", path="/workflow", covered_by=_STAGE_C + _UI),
    SmokeRoute(category="pages", method="GET", path="/check-languages", covered_by=_CHECK_LANG),
    SmokeRoute(category="pages", method="GET", path="/pulls", covered_by=_STAGE_C + _UI),
    SmokeRoute(category="pages", method="GET", path="/result-files", covered_by=_STAGE_C),
    SmokeRoute(category="pages", method="GET", path="/urls", covered_by=_STAGE_C + _UI),
    SmokeRoute(category="pages", method="GET", path="/runs", covered_by=_STAGE_C + _UI),
    SmokeRoute(category="api_read", method="GET", path="/api/domains", expected_json_keys=("items",), covered_by=_STAGE_A + _STAGE_C + _UI),
    SmokeRoute(category="api_read", method="GET", path="/api/capture/runs", expected_json_keys=("runs",), covered_by=_STAGE_B + _STAGE_C + _UI),
    SmokeRoute(category="api_read", method="GET", path="/api/workflow/status", expected_json_keys=("capture", "run"), covered_by=_STAGE_B + _E2E + _UI),
    SmokeRoute(category="api_read", method="GET", path="/api/issues", expected_json_keys=("count", "issues"), covered_by=_STAGE_A + _STAGE_C + _E2E + _UI),
    SmokeRoute(category="api_read", method="GET", path="/api/pulls", expected_json_keys=("rows",), covered_by=_STAGE_A + _STAGE_C + _E2E + _UI),
    SmokeRoute(category="api_write", method="POST", path="/api/seed-urls/add", expected_json_keys=("domain", "updated_at", "urls"), covered_by=_STAGE_B + _E2E + _UI),
    SmokeRoute(category="api_write", method="POST", path="/api/seed-urls/row-upsert", expected_json_keys=("domain", "updated_at", "urls"), covered_by=_STAGE_B + _UI),
    SmokeRoute(category="api_write", method="POST", path="/api/seed-urls/clear", expected_json_keys=("domain", "updated_at", "urls"), covered_by=_STAGE_B),
    SmokeRoute(category="api_write", method="POST", path="/api/recipes/upsert", expected_json_keys=("recipe", "recipes"), covered_by=_STAGE_B + _E2E),
    SmokeRoute(category="api_write", method="POST", path="/api/recipes/delete", expected_json_keys=("status", "recipes"), covered_by=_STAGE_B),
    SmokeRoute(category="api_write", method="POST", path="/api/capture/start", expected_json_keys=("status", "job_id", "run_id"), covered_by=_STAGE_B + _E2E),
    SmokeRoute(category="api_write", method="POST", path="/api/workflow/generate-eligible-dataset", expected_json_keys=("status", "job_id", "run_id"), covered_by=_STAGE_B + _E2E),
    SmokeRoute(category="api_write", method="POST", path="/api/workflow/generate-issues", expected_json_keys=("status", "job_id", "run_id"), covered_by=_STAGE_B + _E2E),
)
