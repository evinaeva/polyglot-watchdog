from unittest.mock import patch

from pipeline.phase4_ocr import build_phase4_ocr_rows
from pipeline.run_phase6 import run


def test_svg_text_review_status_reviewed():
    eligible = [{"item_id": "svg-1", "page_id": "p1", "url": "https://example.com", "language": "fr"}]
    collected = [{
        "item_id": "svg-1",
        "page_id": "p1",
        "element_type": "img",
        "tag": "svg",
        "text": "<svg><text>Hello SVG</text></svg>",
        "bbox": {"x": 0, "y": 0, "width": 1, "height": 1},
        "viewport_kind": "desktop",
        "state": "baseline",
        "user_tier": "guest",
        "attributes": {"src": "", "alt": ""},
    }]
    rows = build_phase4_ocr_rows(eligible, collected, [{"page_id": "p1", "storage_uri": ""}], image_fetcher=lambda _: b"", ocr_fn=lambda _: {})
    assert rows[0]["image_text_review_status"] == "image_text_reviewed"
    assert rows[0]["svg_text"] == "Hello SVG"


def test_phase6_writes_coverage_gaps_separate_from_issues():
    en_item = {
        "item_id": "e1", "page_id": "en1", "url": "https://example.com/p", "language": "en", "text": "Buy",
        "element_type": "p", "tag": "p", "attributes": None,
        "page_canonical_key": "pc", "logical_match_key": "lm", "path_signature": "main>p",
        "container_signature": "main", "normalized_ordinal": 1, "semantic_hint": "",
    }
    target_item = {
        "item_id": "t1", "page_id": "fr1", "url": "https://example.com/fr/p", "language": "fr", "text": "Acheter",
        "element_type": "img", "tag": "img", "attributes": {"src": "https://example.com/img.png"},
        "page_canonical_key": "pc", "logical_match_key": "lm", "path_signature": "main>div>p",
        "container_signature": "main", "normalized_ordinal": 1, "semantic_hint": "",
    }
    phase4 = [{
        "item_id": "t1", "page_id": "fr1", "url": "https://example.com/fr/p", "language": "fr", "viewport_kind": "desktop",
        "state": "baseline", "user_tier": "guest", "source_image_uri": "gs://b/img.png", "ocr_text": "", "ocr_provider": "ocr.space",
        "ocr_engine": "3", "ocr_notes": ["missing_source_image"], "provider_meta": {}, "status": "failed",
        "asset_hash": "h", "src": "https://example.com/img.png", "alt": "", "is_svg": False, "svg_text": "",
        "image_text_review_status": "image_text_review_blocked",
    }]
    artifacts = [
        [en_item], [target_item],
        [{"item_id": "e1", "page_id": "en1", "bbox": {"x": 0, "y": 0, "width": 1, "height": 1}}],
        [{"item_id": "t1", "page_id": "fr1", "bbox": {"x": 0, "y": 0, "width": 1, "height": 1}}],
        [{"page_id": "en1", "storage_uri": "gs://b/en.png"}],
        [{"page_id": "fr1", "storage_uri": "gs://b/fr.png"}],
        phase4,
    ]
    writes = []

    def _write(domain, run_id, filename, payload):
        writes.append((filename, payload))

    with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts), patch(
        "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
    ), patch("pipeline.run_phase6.write_json_artifact", side_effect=_write), patch("pipeline.run_phase6.write_phase_manifest"):
        issues = run("example.com", "run-en", "run-fr", review_mode="test-heuristic")

    assert isinstance(issues, list)
    coverage = next(payload for name, payload in writes if name == "coverage_gaps.json")
    assert coverage[0]["status"] == "image_text_review_blocked"


def test_phase6_reports_gap_when_phase4_row_missing_for_image_item():
    en_item = {
        "item_id": "e1", "page_id": "en1", "url": "https://example.com/p", "language": "en", "text": "Buy",
        "element_type": "p", "tag": "p", "attributes": None,
        "page_canonical_key": "pc", "logical_match_key": "lm", "path_signature": "main>p",
        "container_signature": "main", "normalized_ordinal": 1, "semantic_hint": "",
    }
    target_item = {
        "item_id": "t1", "page_id": "fr1", "url": "https://example.com/fr/p", "language": "fr", "text": "Acheter",
        "element_type": "img", "tag": "img", "attributes": {"src": "https://example.com/a.png"},
        "page_canonical_key": "pc", "logical_match_key": "lm", "path_signature": "main>img",
        "container_signature": "main", "normalized_ordinal": 1, "semantic_hint": "",
    }
    artifacts = [
        [en_item], [target_item],
        [{"item_id": "e1", "page_id": "en1", "bbox": {"x": 0, "y": 0, "width": 1, "height": 1}}],
        [{"item_id": "t1", "page_id": "fr1", "bbox": {"x": 0, "y": 0, "width": 1, "height": 1}}],
        [{"page_id": "en1", "storage_uri": "gs://b/en.png"}],
        [{"page_id": "fr1", "storage_uri": "gs://b/fr.png"}],
        [],
    ]
    writes = []

    def _write(domain, run_id, filename, payload):
        writes.append((filename, payload))

    with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts), patch(
        "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
    ), patch("pipeline.run_phase6.write_json_artifact", side_effect=_write), patch("pipeline.run_phase6.write_phase_manifest"):
        run("example.com", "run-en", "run-fr", review_mode="test-heuristic")

    coverage = next(payload for name, payload in writes if name == "coverage_gaps.json")
    assert coverage[0]["status"] == "image_text_not_reviewed"
    assert coverage[0]["reason"] == ["phase4_ocr_missing_row"]
