from unittest.mock import patch

from pipeline.run_phase6 import run


def _base_artifacts(target_item_overrides=None):
    en_item = {
        "item_id": "item-1",
        "page_id": "en-page-1",
        "url": "https://example.com/p",
        "language": "en",
        "viewport_kind": "desktop",
        "state": "baseline",
        "user_tier": "guest",
        "element_type": "p",
        "css_selector": "main > p",
        "bbox": {"x": 1, "y": 2, "width": 3, "height": 4},
        "text": "Buy now",
        "visible": True,
        "tag": "p",
        "attributes": None,
    }
    target_item = {
        "item_id": "item-1",
        "page_id": "fr-page-1",
        "url": "https://example.com/fr/p",
        "language": "fr",
        "viewport_kind": "desktop",
        "state": "baseline",
        "user_tier": "guest",
        "element_type": "p",
        "css_selector": "main > p",
        "bbox": {"x": 1, "y": 2, "width": 3, "height": 4},
        "text": "Acheter",
        "visible": True,
        "tag": "p",
        "attributes": None,
    }
    if target_item_overrides:
        target_item.update(target_item_overrides)

    return [
        [en_item],
        [target_item],
        [{"item_id": "item-1", "page_id": "en-page-1", "bbox": {"x": 1, "y": 2, "width": 3, "height": 4}}],
        [{"item_id": "item-1", "page_id": "fr-page-1", "bbox": {"x": 1, "y": 2, "width": 3, "height": 4}}],
        [{"page_id": "en-page-1", "storage_uri": "gs://b/en.png"}],
        [{"page_id": "fr-page-1", "storage_uri": "gs://b/fr.png"}],
    ]


def test_review_class_mapping_and_rich_evidence_for_placeholder():
    artifacts = _base_artifacts({"text": "Acheter %s"})
    artifacts[0][0]["text"] = "Buy now <name>"

    with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts), patch(
        "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
    ), patch("pipeline.run_phase6.write_json_artifact"), patch("pipeline.run_phase6.write_phase_manifest"):
        issues = run("example.com", "run-en", "run-fr")

    assert len(issues) == 1
    issue = issues[0]
    assert issue["category"] == "FORMATTING_MISMATCH"
    assert issue["evidence"]["review_class"] == "PLACEHOLDER"
    assert issue["evidence"]["reason"]
    assert "signals" in issue["evidence"]
    assert issue["evidence"]["pairing_basis"] == "item_id"
    assert issue["evidence"]["text_en"] == "Buy now <name>"
    assert issue["evidence"]["text_target"] == "Acheter %s"


def test_ocr_metadata_applies_only_to_image_items():
    artifacts = _base_artifacts({"tag": "img", "element_type": "img", "ocr_text": "X", "text": "Acheter"})

    with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts), patch(
        "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
    ), patch("pipeline.run_phase6.write_json_artifact"), patch("pipeline.run_phase6.write_phase_manifest"):
        issues = run("example.com", "run-en", "run-fr")

    assert len(issues) == 1
    issue = issues[0]
    assert issue["evidence"]["review_class"] == "OCR_NOISE"
    assert issue["category"] == "FORMATTING_MISMATCH"
    assert issue["evidence"]["ocr_text"] == "X"
    assert issue["evidence"]["ocr_engine"] == "OCR.Space:engine3"


def test_non_image_items_do_not_receive_ocr_signals():
    artifacts = _base_artifacts({"ocr_text": "X", "text": "Acheter"})

    with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts), patch(
        "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
    ), patch("pipeline.run_phase6.write_json_artifact"), patch("pipeline.run_phase6.write_phase_manifest"):
        issues = run("example.com", "run-en", "run-fr")

    assert issues == []


def test_provider_disabled_mode_is_deterministic_and_offline():
    artifacts = _base_artifacts({"text": "teh translation"})

    with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts), patch(
        "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
    ), patch("pipeline.run_phase6.write_json_artifact"), patch("pipeline.run_phase6.write_phase_manifest"), patch.dict(
        "os.environ", {"PHASE6_REVIEW_PROVIDER": "disabled"}, clear=False
    ):
        issues = run("example.com", "run-en", "run-fr")

    assert issues == []


def test_confidence_and_ordering_are_deterministic():
    artifacts = _base_artifacts({"text": "Buy now"})

    with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts), patch(
        "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
    ), patch("pipeline.run_phase6.write_json_artifact"), patch("pipeline.run_phase6.write_phase_manifest"):
        first = run("example.com", "run-en", "run-fr")

    with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts), patch(
        "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
    ), patch("pipeline.run_phase6.write_json_artifact"), patch("pipeline.run_phase6.write_phase_manifest"):
        second = run("example.com", "run-en", "run-fr")

    assert len(first) == 1
    assert first == second
    assert first[0]["confidence"] == 0.7
    assert first[0]["evidence"]["signals"] == {"identical_text": 0.2, "untranslated_indicator": 0.1}
