from unittest.mock import patch

from app.skeleton_server import _build_capture_plan, _filter_issues, _load_collected_rows, _load_issues, _load_template_rule_decisions, _merge_pull_rows, MOCK_DOMAINS
from pipeline.interactive_capture import CaptureContext, CaptureJob


def test_load_collected_rows_sorted():
    rows = [{"item_id": "b"}, {"item_id": "a"}]
    with patch("pipeline.storage.read_json_artifact", return_value=rows):
        out = _load_collected_rows("example.com", "run")
    assert [r["item_id"] for r in out] == ["a", "b"]


def test_load_issues_sorted():
    rows = [{"id": "2"}, {"id": "1"}]
    with patch("pipeline.storage.read_json_artifact", return_value=rows):
        out = _load_issues("example.com", "run")
    assert [r["id"] for r in out] == ["1", "2"]


def test_capture_plan_is_deterministic():
    jobs = [
        CaptureJob(context=CaptureContext(domain="example.com", url="https://example.com/b", language="en", viewport_kind="desktop", state="baseline", user_tier=None), mode="baseline", recipe_id=None),
        CaptureJob(context=CaptureContext(domain="example.com", url="https://example.com/a", language="en", viewport_kind="desktop", state="baseline", user_tier=None), mode="baseline", recipe_id=None),
    ]
    with patch("pipeline.run_phase1.load_planning_rows", return_value=[{"url": "https://example.com/a", "recipe_ids": []}]), patch(
        "app.recipes.load_recipes_for_planner", return_value={}
    ), patch("pipeline.run_phase1.build_planned_jobs", return_value=jobs):
        plan = _build_capture_plan({"domain": "example.com", "run_id": "run-1", "languages": ["en"], "viewports": ["desktop"]})
    assert [row["url"] for row in plan] == ["https://example.com/a", "https://example.com/b"]


def test_load_template_rule_decisions_last_write_wins():
    rules = [
        {"item_id": "i1", "rule_type": "MASK_VARIABLE", "created_at": "2026-01-01T00:00:00Z"},
        {"item_id": "i1", "rule_type": "IGNORE_ENTIRE_ELEMENT", "created_at": "2026-01-01T01:00:00Z"},
    ]
    with patch("pipeline.storage.read_json_artifact", return_value=rules):
        out = _load_template_rule_decisions("example.com", "run")
    assert out["i1"] == "IGNORE_ENTIRE_ELEMENT"


def test_filter_issues_by_query_matches_multiple_fields():
    issues = [{"id": "id-1", "category": "SPELLING", "url": "https://example.com/a", "message": "Bad CTA"}]
    assert len(_filter_issues(issues, "cta")) == 1
    assert len(_filter_issues(issues, "spelling")) == 1
    assert len(_filter_issues(issues, "missing")) == 0


def test_capture_plan_expands_user_tiers():
    def _jobs_for_tier(domain, planning_rows, language, viewport_kind, user_tier, recipes):
        return [
            CaptureJob(
                context=CaptureContext(
                    domain=domain,
                    url="https://example.com/a",
                    language=language,
                    viewport_kind=viewport_kind,
                    state="baseline",
                    user_tier=user_tier,
                ),
                mode="baseline",
                recipe_id=None,
            )
        ]

    with patch("pipeline.run_phase1.load_planning_rows", return_value=[{"url": "https://example.com/a", "recipe_ids": []}]), patch(
        "app.recipes.load_recipes_for_planner", return_value={}
    ), patch("pipeline.run_phase1.build_planned_jobs", side_effect=_jobs_for_tier):
        plan = _build_capture_plan({
            "domain": "example.com",
            "run_id": "run-1",
            "languages": ["en"],
            "viewports": ["desktop"],
            "user_tiers": ["free", "paid"],
        })

    assert [row["user_tier"] for row in plan] == ["free", "paid"]


def test_mock_domains_non_empty_for_ui_dropdown():
    assert sorted(MOCK_DOMAINS)


def test_merge_pull_rows_preserves_existing_decision_when_no_persisted_rule():
    rows = [{"item_id": "i1", "decision": "MASK_VARIABLE"}]
    merged = _merge_pull_rows(rows, {})
    assert merged[0]["decision"] == "MASK_VARIABLE"


def test_load_template_rule_decisions_ignores_non_rfc3339_z_created_at():
    rules = [{"item_id": "i1", "rule_type": "MASK_VARIABLE", "created_at": "2026-1-1T1:2:3+00:00"}]
    with patch("pipeline.storage.read_json_artifact", return_value=rules):
        out = _load_template_rule_decisions("example.com", "run")
    assert out == {}
