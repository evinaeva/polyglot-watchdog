from dataclasses import dataclass

from app.skeleton_server import _decision_key, _expand_capture_plan, _upsert_job_status, _upsert_phase2_decision, _to_rule_type, _load_phase2_decisions


@dataclass(frozen=True)
class _Ctx:
    url: str
    language: str
    viewport_kind: str
    state: str
    user_tier: str | None


@dataclass(frozen=True)
class _Job:
    context: _Ctx
    mode: str
    recipe_id: str | None = None


def test_upsert_job_status_last_write_wins(monkeypatch):
    state = {"runs": [{"run_id": "r1", "jobs": [{"job_id": "j1", "status": "queued"}]}]}

    def fake_load(domain):
        return state

    def fake_save(domain, payload):
        state.clear()
        state.update(payload)

    monkeypatch.setattr("app.skeleton_server._load_runs", fake_load)
    monkeypatch.setattr("app.skeleton_server._save_runs", fake_save)

    _upsert_job_status("example.com", "r1", {"job_id": "j1", "status": "running"})
    _upsert_job_status("example.com", "r1", {"job_id": "j1", "status": "succeeded"})

    jobs = state["runs"][0]["jobs"]
    assert jobs == [{"job_id": "j1", "status": "succeeded"}]


def test_phase2_decision_upsert_is_passthrough_for_canonical_template_rules():
    decision = {
        "capture_context_id": "ctx1",
        "item_id": "i1",
        "url": "https://example.com/a",
        "state": "baseline",
        "language": "en",
        "viewport_kind": "desktop",
        "user_tier": "guest",
        "rule_type": "MASK_VARIABLE",
    }
    out = _upsert_phase2_decision("example.com", "run-1", decision)
    assert out == decision
    assert _decision_key(out) == _decision_key(decision)


def test_expand_capture_plan_cross_product_is_deterministic(monkeypatch):
    def fake_build(domain, planning_rows, language, viewport, tier, recipes):
        return [
            _Job(
                context=_Ctx(
                    url=planning_rows[0]["url"],
                    language=language,
                    viewport_kind=viewport,
                    state="baseline",
                    user_tier=tier,
                ),
                mode="baseline",
                recipe_id=None,
            )
        ]

    monkeypatch.setattr("pipeline.run_phase1.build_planned_jobs", fake_build)
    rows = [{"url": "https://example.com/a", "recipe_ids": []}]
    out1 = _expand_capture_plan("example.com", rows, ["fr", "en"], ["mobile", "desktop"], ["pro", "guest"], {})
    out2 = _expand_capture_plan("example.com", rows, ["fr", "en"], ["mobile", "desktop"], ["pro", "guest"], {})
    assert out1 == out2
    assert len(out1) == 8


def test_expand_capture_plan_deduplicates_jobs(monkeypatch):
    duplicate_job = _Job(
        context=_Ctx(
            url="https://example.com/a",
            language="en",
            viewport_kind="desktop",
            state="baseline",
            user_tier="guest",
        ),
        mode="baseline",
        recipe_id=None,
    )

    monkeypatch.setattr("pipeline.run_phase1.build_planned_jobs", lambda *args, **kwargs: [duplicate_job, duplicate_job])
    out = _expand_capture_plan("example.com", [{"url": "https://example.com/a", "recipe_ids": []}], ["en"], ["desktop"], ["guest"], {})
    assert len(out) == 1


def test_to_rule_type_maps_operator_decisions():
    assert _to_rule_type("eligible") == "ALWAYS_COLLECT"
    assert _to_rule_type("exclude") == "IGNORE_ENTIRE_ELEMENT"
    assert _to_rule_type("needs-fix") == "MASK_VARIABLE"
    assert _to_rule_type("ALWAYS_COLLECT") == "ALWAYS_COLLECT"


def test_load_phase2_decisions_reads_template_rules(monkeypatch):
    monkeypatch.setattr("app.skeleton_server._artifact_exists_strict", lambda d, r, f: True)
    monkeypatch.setattr("app.skeleton_server._read_json_required", lambda d, r, f: [{"item_id": "i1", "url": "https://a", "rule_type": "MASK_VARIABLE", "created_at": "t"}])
    rows = _load_phase2_decisions("example.com", "run-1")
    assert rows == [{"item_id": "i1", "url": "https://a", "rule_type": "MASK_VARIABLE", "updated_at": "t"}]


def test_capture_context_payload_includes_language():
    page = {"url": "https://example.com/a", "language": "fr", "viewport_kind": "desktop", "state": "baseline", "user_tier": None}
    from app.skeleton_server import _capture_context_id_from_page
    value = _capture_context_id_from_page("example.com", page)
    assert isinstance(value, str) and value


def test_load_phase2_decisions_rejects_malformed_rows(monkeypatch):
    monkeypatch.setattr("app.skeleton_server._artifact_exists_strict", lambda d, r, f: True)
    monkeypatch.setattr("app.skeleton_server._read_json_required", lambda d, r, f: [{"item_id": "i1", "url": "https://a"}])
    import pytest
    with pytest.raises(ValueError, match="template_rules.json artifact_invalid"):
        _load_phase2_decisions("example.com", "run-1")
