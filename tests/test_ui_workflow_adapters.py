from dataclasses import dataclass

from app.skeleton_server import _decision_key, _expand_capture_plan, _upsert_job_status, _upsert_phase2_decision


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


def test_phase2_decisions_are_context_keyed(monkeypatch):
    saved = {"decisions": []}

    monkeypatch.setattr("app.skeleton_server._load_phase2_decisions", lambda domain, run_id: list(saved["decisions"]))
    monkeypatch.setattr("app.skeleton_server._save_phase2_decisions", lambda domain, run_id, decisions: saved.__setitem__("decisions", list(decisions)))

    first = {
        "capture_context_id": "ctx1",
        "item_id": "i1",
        "url": "https://example.com/a",
        "state": "baseline",
        "language": "en",
        "viewport_kind": "desktop",
        "user_tier": "guest",
        "rule_type": "MASK_VARIABLE",
    }
    second = dict(first)
    second["rule_type"] = "ALWAYS_COLLECT"

    _upsert_phase2_decision("example.com", "run-1", first)
    _upsert_phase2_decision("example.com", "run-1", second)

    assert len(saved["decisions"]) == 1
    assert saved["decisions"][0]["rule_type"] == "ALWAYS_COLLECT"
    assert _decision_key(saved["decisions"][0]) == _decision_key(first)


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
