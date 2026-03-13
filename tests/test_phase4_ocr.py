from unittest.mock import patch

from pipeline.phase4_ocr import build_phase4_ocr_rows
from pipeline.phase4_ocr_provider import ocrspace_extract_text
from pipeline.run_phase6 import run


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _tiny_png_bytes() -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDAT\x08\x1dc``\x00\x00\x00\x02\x00\x01"
        b"\xe2!\xbc3\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def test_ocrspace_request_path_with_engine3_and_base64(monkeypatch):
    captured = {}

    def fake_request(url, payload, headers, timeout_s):
        captured.update({"url": url, "payload": payload, "headers": headers, "timeout_s": timeout_s})
        return _FakeResponse({"IsErroredOnProcessing": False, "ParsedResults": [{"ParsedText": "  Hello   world\n"}]})

    monkeypatch.setenv("OCR_SPACE_API_KEY", "test-key")
    result = ocrspace_extract_text(_tiny_png_bytes(), request_fn=fake_request)

    assert result["status"] == "ok"
    assert result["ocr_text"] == "Hello world"
    assert captured["payload"]["OCREngine"] == "3"
    assert captured["payload"]["base64Image"].startswith("data:image/png;base64,")
    assert captured["headers"]["apikey"] == "test-key"


def test_ocrspace_missing_key_and_malformed_response_are_non_fatal(monkeypatch):
    monkeypatch.delenv("OCR_SPACE_API_KEY", raising=False)
    skipped = ocrspace_extract_text(_tiny_png_bytes())
    assert skipped["status"] == "skipped"

    monkeypatch.setenv("OCR_SPACE_API_KEY", "test-key")
    malformed = ocrspace_extract_text(_tiny_png_bytes(), request_fn=lambda *_: _FakeResponse(["not-a-dict"]))
    assert malformed["status"] == "failed"
    assert malformed["ocr_notes"] == ["malformed_response"]


def test_phase4_rows_include_only_image_backed_items_and_stable_shape():
    eligible = [
        {"item_id": "img-1", "page_id": "p1", "url": "https://example.com", "language": "fr"},
        {"item_id": "txt-1", "page_id": "p1", "url": "https://example.com", "language": "fr"},
    ]
    collected = [
        {"item_id": "img-1", "page_id": "p1", "element_type": "img", "tag": "img", "bbox": {"x": 0, "y": 0, "width": 1, "height": 1}, "viewport_kind": "desktop", "state": "baseline", "user_tier": "guest"},
        {"item_id": "txt-1", "page_id": "p1", "element_type": "p", "tag": "p", "bbox": {"x": 0, "y": 0, "width": 1, "height": 1}, "viewport_kind": "desktop", "state": "baseline", "user_tier": "guest"},
    ]
    screenshots = [{"page_id": "p1", "storage_uri": "gs://b/page.png"}]

    rows = build_phase4_ocr_rows(
        eligible,
        collected,
        screenshots,
        image_fetcher=lambda _: _tiny_png_bytes(),
        ocr_fn=lambda _: {"status": "ok", "ocr_text": "cta", "ocr_provider": "ocr.space", "ocr_engine": "3", "ocr_notes": [], "provider_meta": {}},
    )

    assert [r["item_id"] for r in rows] == ["img-1"]
    assert rows[0].keys() == {
        "item_id", "page_id", "url", "language", "viewport_kind", "state", "user_tier", "source_image_uri",
        "ocr_text", "ocr_provider", "ocr_engine", "ocr_notes", "provider_meta", "status",
    }


def test_phase6_consumes_phase4_ocr_artifact_without_contract_changes():
    en_item = {"item_id": "item-1", "page_id": "en-page-1", "url": "https://example.com/p", "language": "en", "text": "Buy", "element_type": "p", "tag": "p", "attributes": None}
    target_item = {"item_id": "item-1", "page_id": "fr-page-1", "url": "https://example.com/fr/p", "language": "fr", "text": "Acheter", "element_type": "img", "tag": "img", "attributes": None}
    artifacts = [
        [en_item],
        [target_item],
        [{"item_id": "item-1", "page_id": "en-page-1", "bbox": {"x": 0, "y": 0, "width": 1, "height": 1}}],
        [{"item_id": "item-1", "page_id": "fr-page-1", "bbox": {"x": 0, "y": 0, "width": 1, "height": 1}}],
        [{"page_id": "en-page-1", "storage_uri": "gs://b/en.png"}],
        [{"page_id": "fr-page-1", "storage_uri": "gs://b/fr.png"}],
        [{"item_id": "item-1", "status": "ok", "ocr_text": "X", "ocr_engine": "3"}],
    ]

    with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts), patch(
        "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
    ), patch("pipeline.run_phase6.write_json_artifact"), patch("pipeline.run_phase6.write_phase_manifest"):
        issues = run("example.com", "run-en", "run-fr")

    assert len(issues) == 1
    assert issues[0]["category"] == "FORMATTING_MISMATCH"
    assert issues[0]["evidence"]["ocr_text"] == "X"
