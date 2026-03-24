import json
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

import pytest

from pipeline.run_phase1 import ensure_run_start_inputs_snapshot, load_planning_rows, load_planning_urls


def test_phase1_planning_reads_run_snapshot_only() -> None:
    seed_payload = {
        "domain": "example.com",
        "urls": [
            {"url": "https://example.com/b", "description": None, "recipe_ids": []},
            {"url": "https://example.com/a", "description": None, "recipe_ids": []},
        ],
    }
    inputs_manifest = {
        "artifacts": {
            "seed_urls_snapshot": {
                "uri": "gs://polyglot-watchdog-artifacts-1018698441568/example.com/run-1/inputs/seed_urls.snapshot.json",
                "sha256": "c4b4187d71728c2f079ea08382b0db84a65a0a0d284d06b196d26ef71451e988",
                "sha1": "c98dd62a03a7371aca317c2e37319a6f72c1323f",
            },
            "recipes_manifest": {
                "uri": "gs://polyglot-watchdog-artifacts-1018698441568/example.com/run-1/inputs/recipes_manifest.json",
                "sha256": "5b082be312c6e37393c0cf60685b083a5eaf6a3265e37c3b3e5b0fb0c0aec10b",
                "sha1": "223502c78e9248e74a08a3688ea8d50794a43316",
            },
        },
    }
    recipe_manifest = {"domain": "example.com", "active_recipe_ids": [], "recipes": []}

    with patch("pipeline.run_phase1.read_json_artifact", side_effect=[inputs_manifest, seed_payload, recipe_manifest]) as read_mock:
        urls = load_planning_urls("example.com", "run-1")

    assert urls == ["https://example.com/a", "https://example.com/b"]
    assert read_mock.call_args_list[0].args == ("example.com", "run-1", "inputs/inputs_manifest.json")
    assert read_mock.call_args_list[1].args == ("example.com", "run-1", "inputs/seed_urls.snapshot.json")
    assert read_mock.call_args_list[2].args == ("example.com", "run-1", "inputs/recipes_manifest.json")


def test_phase1_requires_snapshot_without_manual_fallback() -> None:
    with patch("pipeline.run_phase1.read_json_artifact", side_effect=[RuntimeError("missing snapshot")]), pytest.raises(RuntimeError):
        load_planning_urls("example.com", "run-2")


def test_phase1_load_planning_rows_preserves_recipe_ids() -> None:
    seed_payload = {
        "domain": "example.com",
        "urls": [
            {"url": "https://example.com/p", "description": None, "recipe_ids": ["b", "a", "a"]},
        ],
    }
    inputs_manifest = {
        "artifacts": {
            "seed_urls_snapshot": {
                "uri": "gs://polyglot-watchdog-artifacts-1018698441568/example.com/run-3/inputs/seed_urls.snapshot.json",
                "sha256": "c030d26b8300fb714afd4f2a3f8882c6dc4eefe2f4a8f029bb2d0c68d3af2577",
                "sha1": "4abb966cb38676a35d162ed1b361d06af29a96ac",
            },
            "recipes_manifest": {
                "uri": "gs://polyglot-watchdog-artifacts-1018698441568/example.com/run-3/inputs/recipes_manifest.json",
                "sha256": "bfa04a5d8bc17c2f5303fc797209232624b18b9aed38818edd2903c14cbdfb9b",
                "sha1": "4fe4c8095401244d6358c7e9092e5edafb5502b1",
            },
        },
    }
    recipe_manifest = {"domain": "example.com", "active_recipe_ids": ["a", "b"], "recipes": []}

    with patch("pipeline.run_phase1.read_json_artifact", side_effect=[inputs_manifest, seed_payload, recipe_manifest]):
        rows = load_planning_rows("example.com", "run-3")

    assert rows == [{"url": "https://example.com/p", "recipe_ids": ["a", "b"]}]


def test_phase1_snapshot_created_once_and_reused() -> None:
    seed_payload = {
        "domain": "example.com",
        "urls": [{"url": "https://example.com/a", "description": None, "recipe_ids": ["checkout"]}],
    }
    recipes = {
        "checkout": SimpleNamespace(
            recipe_id="checkout",
            url_pattern="https://example.com/a",
            steps=(SimpleNamespace(action="click", selector="#buy", wait_for=None),),
            capture_points=(SimpleNamespace(state="profile_open"),),
        ),
    }
    created_manifest = {
        "artifacts": {
            "seed_urls_snapshot": {"uri": "gs://b/example.com/run-4/inputs/seed_urls.snapshot.json", "sha256": "s", "sha1": "s1"},
            "recipes_manifest": {"uri": "gs://b/example.com/run-4/inputs/recipes_manifest.json", "sha256": "r", "sha1": "r1"},
        },
    }

    with patch("pipeline.run_phase1.read_json_artifact", side_effect=[RuntimeError("missing"), seed_payload]) as read_mock, \
            patch("pipeline.run_phase1.load_recipes_for_planner", return_value=recipes), \
            patch("pipeline.run_phase1.write_json_artifact", side_effect=["seed-uri", "recipe-uri", "manifest-uri"]) as write_mock:
        ensure_run_start_inputs_snapshot("example.com", "run-4")

    assert read_mock.call_args_list[0].args == ("example.com", "run-4", "inputs/inputs_manifest.json")
    assert read_mock.call_args_list[1].args == ("example.com", "manual", "seed_urls.json")
    assert write_mock.call_count == 3

    with patch("pipeline.run_phase1.read_json_artifact", return_value=created_manifest) as read_mock, \
            patch("pipeline.run_phase1.write_json_artifact") as write_mock:
        ensure_run_start_inputs_snapshot("example.com", "run-4")

    assert read_mock.call_args_list[0].args == ("example.com", "run-4", "inputs/inputs_manifest.json")
    write_mock.assert_not_called()


def test_phase1_snapshot_hashes_are_deterministic_for_same_snapshot() -> None:
    seed_payload = {
        "domain": "example.com",
        "urls": [{"url": "https://example.com/a", "description": None, "recipe_ids": ["checkout"]}],
    }
    recipes = {
        "checkout": SimpleNamespace(
            recipe_id="checkout",
            url_pattern="https://example.com/a",
            steps=(SimpleNamespace(action="click", selector="#buy", wait_for=None),),
            capture_points=(SimpleNamespace(state="profile_open"),),
        ),
    }
    captured_manifests: list[dict] = []

    def _capture_manifest(domain: str, run_id: str, filename: str, payload: object) -> str:
        if filename == "inputs/inputs_manifest.json":
            captured_manifests.append(payload)  # type: ignore[arg-type]
        return f"gs://x/{domain}/{run_id}/{filename}"

    with patch("pipeline.run_phase1.read_json_artifact", side_effect=[RuntimeError("missing"), seed_payload]), \
            patch("pipeline.run_phase1.load_recipes_for_planner", return_value=recipes), \
            patch("pipeline.run_phase1.write_json_artifact", side_effect=_capture_manifest):
        ensure_run_start_inputs_snapshot("example.com", "run-a")
    with patch("pipeline.run_phase1.read_json_artifact", side_effect=[RuntimeError("missing"), seed_payload]), \
            patch("pipeline.run_phase1.load_recipes_for_planner", return_value=recipes), \
            patch("pipeline.run_phase1.write_json_artifact", side_effect=_capture_manifest):
        ensure_run_start_inputs_snapshot("example.com", "run-b")

    assert len(captured_manifests) == 2
    assert captured_manifests[0]["artifacts"]["seed_urls_snapshot"]["sha256"] == captured_manifests[1]["artifacts"]["seed_urls_snapshot"]["sha256"]
    assert captured_manifests[0]["artifacts"]["recipes_manifest"]["sha256"] == captured_manifests[1]["artifacts"]["recipes_manifest"]["sha256"]


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
