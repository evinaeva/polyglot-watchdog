import json
from pathlib import Path
from unittest.mock import patch

import pytest

from pipeline.run_phase1 import load_planning_rows, load_planning_urls


def test_phase1_uses_seed_urls_as_primary_planning_input() -> None:
    seed_payload = {
        "domain": "example.com",
        "urls": [
            {"url": "https://example.com/b", "description": None, "recipe_ids": []},
            {"url": "https://example.com/a", "description": None, "recipe_ids": []},
        ],
    }

    with patch("pipeline.run_phase1.read_json_artifact", side_effect=[seed_payload]) as read_mock:
        urls = load_planning_urls("example.com", "run-1")

    assert urls == ["https://example.com/a", "https://example.com/b"]
    assert read_mock.call_args_list[0].args == ("example.com", "manual", "seed_urls.json")


def test_phase1_requires_seed_urls_without_legacy_fallback() -> None:
    with patch("pipeline.run_phase1.read_json_artifact", side_effect=[RuntimeError("missing seed")]), pytest.raises(RuntimeError):
        load_planning_urls("example.com", "run-2")


def test_phase1_load_planning_rows_preserves_recipe_ids() -> None:
    seed_payload = {
        "domain": "example.com",
        "urls": [
            {"url": "https://example.com/p", "description": None, "recipe_ids": ["b", "a", "a"]},
        ],
    }

    with patch("pipeline.run_phase1.read_json_artifact", side_effect=[seed_payload]):
        rows = load_planning_rows("example.com", "run-3")

    assert rows == [{"url": "https://example.com/p", "recipe_ids": ["a", "b"]}]


def test_phase1_planner_rejects_duplicate_urls() -> None:
    from pipeline.interactive_capture import DeterministicPlanner, DeterminismError

    planner = DeterministicPlanner()
    with pytest.raises(DeterminismError):
        planner.expand_jobs(
            seed_urls={"domain": "example.com", "urls": [{"url": "https://example.com/a", "recipe_ids": []}, {"url": "https://example.com/a", "recipe_ids": []}]},
            recipes={},
            languages=["en"],
            viewports=["desktop"],
            user_tiers=["guest"],
        )


def test_phase1_planning_rows_match_snapshot_fixture() -> None:
    fixture = json.loads(Path("tests/fixtures/phase1_planning_snapshot.json").read_text(encoding="utf-8"))
    with patch("pipeline.run_phase1.read_json_artifact", side_effect=[fixture["seed_payload"]]):
        rows = load_planning_rows("example.com", "run-snapshot")

    assert rows == fixture["expected_rows"]
