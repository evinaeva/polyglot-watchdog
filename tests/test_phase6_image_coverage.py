from unittest.mock import patch

from pipeline.phase4_ocr import build_phase4_ocr_rows
from pipeline.run_phase6 import run
from pipeline.schema_validator import validate


def _tiny_png_bytes() -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDAT\x08\x1dc``\x00\x00\x00\x02\x00\x01"
        b"\xe2!\xbc3\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def test_svg_text_prepass_is_deterministic_before_ocr():
    svg_data = "data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%3E%3Ctext%3ECTA%3C/text%3E%3C/svg%3E"
    eligible = [{"item_id": "img-1", "page_id": "p1", "url": "https://example.com/fr", "language": "fr"}]
    collected = [{
        "item_id": "img-1",
        "page_id": "p1",
        "element_type": "img",
        "tag": "img",
        "bbox": {"x": 0, "y": 0, "width": 1, "height": 1},
        "viewport_kind": "desktop",
        "state": "baseline",
        "user_tier": "guest",
        "attributes": {"src": svg_data, "alt": "cta"},
    }]
    screenshots = [{"page_id": "p1", "storage_uri": "gs://b/page.png"}]

    rows = build_phase4_ocr_rows(
        eligible,
        collected,
        screenshots,
        image_fetcher=lambda _: _tiny_png_bytes(),
        ocr_fn=lambda _: {"status": "failed", "ocr_text": "", "ocr_provider": "ocr.space", "ocr_engine": "3", "ocr_notes": [], "provider_meta": {}},
    )

    assert rows[0]["status"] == "ok"
    assert rows[0]["ocr_engine"] == "svg-prepass"
    assert rows[0]["svg_text"] == "CTA"


def test_coverage_gaps_are_emitted_separately_from_issues():
    en_item = {"item_id": "item-1", "page_id": "en-p", "url": "https://example.com/p", "language": "en", "text": "Buy", "element_type": "p", "tag": "p", "attributes": None}
    target_item = {"item_id": "item-1", "page_id": "fr-p", "url": "https://example.com/fr/p", "language": "fr", "text": "Acheter", "element_type": "img", "tag": "img", "attributes": {"src": "https://example.com/a.png", "alt": "acheter"}}
    artifacts = [
        [en_item],
        [target_item],
        [{"item_id": "item-1", "page_id": "en-p", "bbox": {"x": 0, "y": 0, "width": 1, "height": 1}}],
        [{"item_id": "item-1", "page_id": "fr-p", "bbox": {"x": 0, "y": 0, "width": 1, "height": 1}, "tag": "img", "element_type": "img", "attributes": {"src": "https://example.com/a.png", "alt": "acheter"}}],
        [{"page_id": "en-p", "storage_uri": "gs://b/en.png"}],
        [{"page_id": "fr-p", "storage_uri": "gs://b/fr.png"}],
        FileNotFoundError("missing"),
    ]
    writes = {}

    def _capture_write(domain, run_id, filename, payload):
        writes[filename] = payload
        return "gs://bucket/" + filename

    with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts), patch(
        "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
    ), patch("pipeline.run_phase6.write_json_artifact", side_effect=_capture_write), patch("pipeline.run_phase6.write_phase_manifest"):
        run("example.com", "run-en", "run-fr", review_mode="test-heuristic")

    assert "issues.json" in writes
    assert "coverage_gaps.json" in writes
    assert writes["coverage_gaps.json"][0]["image_text_review_status"] == "image_text_not_reviewed"


def test_non_image_items_do_not_appear_in_coverage_gaps():
    en_item = {"item_id": "item-1", "page_id": "en-p", "url": "https://example.com/p", "language": "en", "text": "Buy", "element_type": "p", "tag": "p", "attributes": None}
    target_item = {"item_id": "item-1", "page_id": "fr-p", "url": "https://example.com/fr/p", "language": "fr", "text": "Acheter", "element_type": "p", "tag": "p", "attributes": None}
    artifacts = [
        [en_item],
        [target_item],
        [{"item_id": "item-1", "page_id": "en-p", "bbox": {"x": 0, "y": 0, "width": 1, "height": 1}}],
        [{"item_id": "item-1", "page_id": "fr-p", "bbox": {"x": 0, "y": 0, "width": 1, "height": 1}, "tag": "p", "element_type": "p", "attributes": None}],
        [{"page_id": "en-p", "storage_uri": "gs://b/en.png"}],
        [{"page_id": "fr-p", "storage_uri": "gs://b/fr.png"}],
        FileNotFoundError("missing"),
    ]
    writes = {}

    def _capture_write(domain, run_id, filename, payload):
        writes[filename] = payload
        return "gs://bucket/" + filename

    with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts), patch(
        "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
    ), patch("pipeline.run_phase6.write_json_artifact", side_effect=_capture_write), patch("pipeline.run_phase6.write_phase_manifest"):
        run("example.com", "run-en", "run-fr", review_mode="test-heuristic")

    assert writes["coverage_gaps.json"] == []


def test_manifest_counters_cover_reviewed_not_reviewed_and_blocked():
    en_item = {"item_id": "en-1", "page_id": "en-p", "url": "https://example.com/p", "language": "en", "text": "Buy", "element_type": "p", "tag": "p", "attributes": None}
    target_items = [
        {"item_id": "t-reviewed", "page_id": "p-reviewed", "url": "https://example.com/fr/rev", "language": "fr", "text": "A", "element_type": "img", "tag": "img", "attributes": {"src": "https://example.com/a.png", "alt": "a"}},
        {"item_id": "t-unreviewed", "page_id": "p-unreviewed", "url": "https://example.com/fr/unrev", "language": "fr", "text": "B", "element_type": "img", "tag": "img", "attributes": {"src": "https://example.com/b.png", "alt": "b"}},
        {"item_id": "t-blocked", "page_id": "p-blocked", "url": "https://example.com/fr/blocked", "language": "fr", "text": "C", "element_type": "img", "tag": "img", "attributes": {"src": "https://example.com/c.png", "alt": "c"}},
    ]
    artifacts = [
        [en_item],
        target_items,
        [{"item_id": "en-1", "page_id": "en-p", "bbox": {"x": 0, "y": 0, "width": 1, "height": 1}}],
        [
            {"item_id": "t-reviewed", "page_id": "p-reviewed", "bbox": {"x": 0, "y": 0, "width": 1, "height": 1}, "tag": "img", "element_type": "img", "attributes": {"src": "https://example.com/a.png", "alt": "a"}},
            {"item_id": "t-unreviewed", "page_id": "p-unreviewed", "bbox": {"x": 0, "y": 0, "width": 1, "height": 1}, "tag": "img", "element_type": "img", "attributes": {"src": "https://example.com/b.png", "alt": "b"}},
            {"item_id": "t-blocked", "page_id": "p-blocked", "bbox": {"x": 0, "y": 0, "width": 1, "height": 1}, "tag": "img", "element_type": "img", "attributes": {"src": "https://example.com/c.png", "alt": "c"}},
        ],
        [{"page_id": "en-p", "storage_uri": "gs://b/en.png"}],
        [
            {"page_id": "p-reviewed", "storage_uri": "gs://b/rev.png", "url": "https://example.com/fr/rev"},
            {"page_id": "p-unreviewed", "storage_uri": "gs://b/unrev.png", "url": "https://example.com/fr/unrev"},
            {"page_id": "p-blocked", "storage_uri": "gs://b/blocked.png", "url": "https://example.com/fr/blocked"},
        ],
        [
            {"item_id": "t-reviewed", "page_id": "p-reviewed", "url": "https://example.com/fr/rev", "language": "fr", "viewport_kind": "desktop", "state": "baseline", "user_tier": "guest", "source_image_uri": "gs://b/rev.png", "ocr_text": "ok", "ocr_provider": "ocr.space", "ocr_engine": "3", "ocr_notes": [], "provider_meta": {}, "status": "ok", "asset_hash": "ha", "src": "https://example.com/a.png", "alt": "a", "is_svg": False, "svg_text": ""},
            {"item_id": "t-blocked", "page_id": "p-blocked", "url": "https://example.com/fr/blocked", "language": "fr", "viewport_kind": "desktop", "state": "baseline", "user_tier": "guest", "source_image_uri": "gs://b/blocked.png", "ocr_text": "", "ocr_provider": "ocr.space", "ocr_engine": "3", "ocr_notes": [], "provider_meta": {}, "status": "failed", "asset_hash": "hc", "src": "https://example.com/c.png", "alt": "c", "is_svg": False, "svg_text": ""},
        ],
    ]
    manifest_payload = {}
    coverage_payload = []

    def _capture_write(domain, run_id, filename, payload):
        nonlocal coverage_payload
        if filename == "coverage_gaps.json":
            coverage_payload = payload
        return "gs://bucket/" + filename

    def _capture_manifest(domain, run_id, phase, payload):
        manifest_payload.update(payload)
        return "gs://bucket/manifest.json"

    blocked = [{"capture_context_id": "ctx-1", "url": "https://example.com/fr/blocked", "storage_uri": "gs://b/blocked.png"}]
    with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts), patch(
        "pipeline.run_phase6._load_blocked_overlay_pages", return_value=blocked
    ), patch("pipeline.run_phase6.write_json_artifact", side_effect=_capture_write), patch("pipeline.run_phase6.write_phase_manifest", side_effect=_capture_manifest):
        run("example.com", "run-en", "run-fr", review_mode="test-heuristic")

    validate("coverage_gaps", coverage_payload)
    assert manifest_payload["summary_counters"]["image_text_reviewed"] == 1
    assert manifest_payload["summary_counters"]["image_text_not_reviewed"] == 1
    assert manifest_payload["summary_counters"]["image_text_review_blocked"] == 1
