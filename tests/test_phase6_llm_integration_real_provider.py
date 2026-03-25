import os

import pytest

from pipeline import run_phase6


def _artifact_reader(domain: str, en_run_id: str, target_run_id: str):
    en_eligible = [
        {
            "item_id": "i1",
            "language": "en",
            "url": "https://example.com/en",
            "text": "Buy now",
            "css_selector": "#cta",
            "element_type": "text",
            "tag": "div",
            "viewport_kind": "desktop",
            "state": "baseline",
            "user_tier": "guest",
            "stable_ordinal": 1,
        }
    ]
    target_eligible = [
        {
            "item_id": "i1",
            "language": "fr",
            "url": "https://example.com/fr",
            "text": "Acheter maintenant",
            "css_selector": "#cta",
            "element_type": "text",
            "tag": "div",
            "viewport_kind": "desktop",
            "state": "baseline",
            "user_tier": "guest",
            "stable_ordinal": 1,
        }
    ]
    en_collected = [{"item_id": "i1", "page_id": "p1", "bbox": {"x": 1, "y": 1, "width": 10, "height": 10}}]
    target_collected = [{"item_id": "i1", "page_id": "p1", "bbox": {"x": 1, "y": 1, "width": 10, "height": 10}}]
    en_screens = [{"page_id": "p1", "url": "https://example.com/en", "storage_uri": "gs://bucket/en.png"}]
    target_screens = [{"page_id": "p1", "url": "https://example.com/fr", "storage_uri": "gs://bucket/fr.png"}]

    mapping = {
        (domain, en_run_id, "eligible_dataset.json"): en_eligible,
        (domain, target_run_id, "eligible_dataset.json"): target_eligible,
        (domain, en_run_id, "collected_items.json"): en_collected,
        (domain, target_run_id, "collected_items.json"): target_collected,
        (domain, en_run_id, "page_screenshots.json"): en_screens,
        (domain, target_run_id, "page_screenshots.json"): target_screens,
    }

    def _read(d: str, r: str, f: str):
        return mapping[(d, r, f)]

    return _read


def test_phase6_llm_integration_real_provider(monkeypatch):
    """Gated real-provider validation for Phase 6 telemetry emission.

    This is intentionally not a full storage-backed e2e test. It executes the
    real provider path through `run_phase6.run(...)` when credentials are
    configured, while using lightweight in-memory artifact fixtures.
    """
    review_mode = os.environ.get("PHASE6_REVIEW_PROVIDER", "").strip()
    api_key = os.environ.get("PHASE6_REVIEW_API_KEY", "").strip()
    if not review_mode or not api_key:
        missing = [name for name in ("PHASE6_REVIEW_PROVIDER", "PHASE6_REVIEW_API_KEY") if not os.environ.get(name, "").strip()]
        pytest.skip(
            "Skipping real-provider validation: missing required env var(s): "
            + ", ".join(missing)
            + ". Set them to execute a live provider request."
        )

    domain = "example.com"
    en_run_id = "run-en"
    target_run_id = "run-fr"

    captured = {}

    monkeypatch.setattr(run_phase6, "read_json_artifact", _artifact_reader(domain, en_run_id, target_run_id))
    monkeypatch.setattr(run_phase6, "_load_blocked_overlay_pages", lambda *args, **kwargs: [])
    monkeypatch.setattr(run_phase6, "validate", lambda *args, **kwargs: None)
    monkeypatch.setattr(run_phase6, "write_phase_manifest", lambda *args, **kwargs: None)

    def _capture_write(d, r, filename, payload):
        captured[(d, r, filename)] = payload
        return f"gs://test-bucket/{d}/{r}/{filename}"

    monkeypatch.setattr(run_phase6, "write_json_artifact", _capture_write)

    run_phase6.run(domain, en_run_id, target_run_id, review_mode=review_mode)

    telemetry_key = (domain, target_run_id, "llm_review_stats.json")
    assert telemetry_key in captured
    stats = captured[telemetry_key]

    # Proven here: provider call path executed and telemetry was emitted.
    # Not proven here: full production storage wiring and multi-page workflows.
    assert int(stats.get("llm_batches_attempted", 0)) > 0
    assert int(stats.get("responses_received", 0)) > 0 or (
        int(stats.get("transport_failures", 0)) > 0
        or int(stats.get("parse_failures", 0)) > 0
        or int(stats.get("provider_failures", 0)) > 0
    )
    assert str(stats.get("effective_model", "")).strip()
