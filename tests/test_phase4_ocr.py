from unittest.mock import patch

from pipeline.phase4_ocr import build_phase4_ocr_rows
from pipeline.phase4_ocr_provider import ocrspace_extract_text
from pipeline.run_phase6 import run
from pipeline.schema_validator import SchemaValidationError, validate


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



def _phase4_row(status: str = "ok") -> dict:
    row = {
        "item_id": "img-1",
        "page_id": "p1",
        "url": "https://example.com",
        "language": "fr",
        "viewport_kind": "desktop",
        "state": "baseline",
        "user_tier": "guest",
        "source_image_uri": "gs://bucket/page.png",
        "ocr_text": "cta" if status == "ok" else "",
        "ocr_provider": "ocr.space",
        "ocr_engine": "3",
        "ocr_notes": [],
        "provider_meta": {"provider": "ocr.space"},
        "status": status,
    }
    if status == "skipped":
        row["ocr_notes"] = ["missing_api_key"]
    if status == "failed":
        row["ocr_notes"] = ["request_failed"]
    return row


def test_phase4_ocr_schema_accepts_ok_skipped_failed_rows():
    rows = [_phase4_row("ok"), _phase4_row("skipped"), _phase4_row("failed")]
    validate("phase4_ocr", rows)


def test_phase4_ocr_schema_rejects_invalid_status():
    rows = [_phase4_row("unknown")]
    try:
        validate("phase4_ocr", rows)
        assert False, "expected schema validation to fail for invalid status"
    except SchemaValidationError:
        pass


def test_phase4_ocr_schema_rejects_missing_required_field():
    row = _phase4_row("ok")
    del row["ocr_engine"]
    try:
        validate("phase4_ocr", [row])
        assert False, "expected schema validation to fail for missing required field"
    except SchemaValidationError:
        pass


def test_phase4_output_rows_validate_against_contract_schema():
    eligible = [{"item_id": "img-1", "page_id": "p1", "url": "https://example.com", "language": "fr"}]
    collected = [{"item_id": "img-1", "page_id": "p1", "element_type": "img", "tag": "img", "bbox": {"x": 0, "y": 0, "width": 1, "height": 1}, "viewport_kind": "desktop", "state": "baseline", "user_tier": "guest"}]
    screenshots = [{"page_id": "p1", "storage_uri": "gs://b/page.png"}]

    rows = build_phase4_ocr_rows(
        eligible,
        collected,
        screenshots,
        image_fetcher=lambda _: _tiny_png_bytes(),
        ocr_fn=lambda _: {"status": "ok", "ocr_text": "cta", "ocr_provider": "ocr.space", "ocr_engine": "3", "ocr_notes": [], "provider_meta": {"provider": "ocr.space"}},
    )

    validate("phase4_ocr", rows)


def test_phase6_ocr_fixture_row_is_schema_valid():
    validate("phase4_ocr", [{
        "item_id": "item-1",
        "page_id": "fr-page-1",
        "url": "https://example.com/fr/p",
        "language": "fr",
        "viewport_kind": "desktop",
        "state": "baseline",
        "user_tier": "guest",
        "source_image_uri": "gs://b/fr.png",
        "ocr_text": "X",
        "ocr_provider": "ocr.space",
        "ocr_engine": "3",
        "ocr_notes": [],
        "provider_meta": {"provider": "ocr.space"},
        "status": "ok",
    }])

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
        [{
            "item_id": "item-1",
            "page_id": "fr-page-1",
            "url": "https://example.com/fr/p",
            "language": "fr",
            "viewport_kind": "desktop",
            "state": "baseline",
            "user_tier": "guest",
            "source_image_uri": "gs://b/fr.png",
            "ocr_text": "X",
            "ocr_provider": "ocr.space",
            "ocr_engine": "3",
            "ocr_notes": [],
            "provider_meta": {"provider": "ocr.space"},
            "status": "ok",
        }],
    ]

    with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts), patch(
        "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
    ), patch("pipeline.run_phase6.write_json_artifact"), patch("pipeline.run_phase6.write_phase_manifest"):
        issues = run("example.com", "run-en", "run-fr")

    assert len(issues) == 1
    assert issues[0]["category"] == "FORMATTING_MISMATCH"
    assert issues[0]["evidence"]["ocr_text"] == "X"


def test_phase6_continues_when_phase4_ocr_artifact_is_absent():
    en_item = {"item_id": "item-1", "page_id": "en-page-1", "url": "https://example.com/p", "language": "en", "text": "Buy", "element_type": "p", "tag": "p", "attributes": None}
    target_item = {"item_id": "item-1", "page_id": "fr-page-1", "url": "https://example.com/fr/p", "language": "fr", "text": "Acheter", "element_type": "img", "tag": "img", "attributes": None}
    artifacts = [
        [en_item],
        [target_item],
        [{"item_id": "item-1", "page_id": "en-page-1", "bbox": {"x": 0, "y": 0, "width": 1, "height": 1}}],
        [{"item_id": "item-1", "page_id": "fr-page-1", "bbox": {"x": 0, "y": 0, "width": 1, "height": 1}}],
        [{"page_id": "en-page-1", "storage_uri": "gs://b/en.png"}],
        [{"page_id": "fr-page-1", "storage_uri": "gs://b/fr.png"}],
    ]

    with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts + [FileNotFoundError("missing")]), patch(
        "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
    ), patch("pipeline.run_phase6.write_json_artifact"), patch("pipeline.run_phase6.write_phase_manifest"):
        issues = run("example.com", "run-en", "run-fr")

    assert issues == []


def test_phase6_continues_when_phase4_ocr_artifact_not_found_style_error():
    class NotFound(Exception):
        pass

    en_item = {"item_id": "item-1", "page_id": "en-page-1", "url": "https://example.com/p", "language": "en", "text": "Buy", "element_type": "p", "tag": "p", "attributes": None}
    target_item = {"item_id": "item-1", "page_id": "fr-page-1", "url": "https://example.com/fr/p", "language": "fr", "text": "Acheter", "element_type": "img", "tag": "img", "attributes": None}
    artifacts = [
        [en_item],
        [target_item],
        [{"item_id": "item-1", "page_id": "en-page-1", "bbox": {"x": 0, "y": 0, "width": 1, "height": 1}}],
        [{"item_id": "item-1", "page_id": "fr-page-1", "bbox": {"x": 0, "y": 0, "width": 1, "height": 1}}],
        [{"page_id": "en-page-1", "storage_uri": "gs://b/en.png"}],
        [{"page_id": "fr-page-1", "storage_uri": "gs://b/fr.png"}],
    ]

    with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts + [NotFound("missing")]), patch(
        "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
    ), patch("pipeline.run_phase6.write_json_artifact"), patch("pipeline.run_phase6.write_phase_manifest"):
        issues = run("example.com", "run-en", "run-fr")

    assert issues == []


def test_phase6_rejects_invalid_present_phase4_ocr_artifact():
    en_item = {"item_id": "item-1", "page_id": "en-page-1", "url": "https://example.com/p", "language": "en", "text": "Buy", "element_type": "p", "tag": "p", "attributes": None}
    target_item = {"item_id": "item-1", "page_id": "fr-page-1", "url": "https://example.com/fr/p", "language": "fr", "text": "Acheter", "element_type": "img", "tag": "img", "attributes": None}
    artifacts = [
        [en_item],
        [target_item],
        [{"item_id": "item-1", "page_id": "en-page-1", "bbox": {"x": 0, "y": 0, "width": 1, "height": 1}}],
        [{"item_id": "item-1", "page_id": "fr-page-1", "bbox": {"x": 0, "y": 0, "width": 1, "height": 1}}],
        [{"page_id": "en-page-1", "storage_uri": "gs://b/en.png"}],
        [{"page_id": "fr-page-1", "storage_uri": "gs://b/fr.png"}],
        [{"item_id": "item-1", "status": "ok"}],
    ]

    with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts), patch(
        "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
    ), patch("pipeline.run_phase6.write_json_artifact"), patch("pipeline.run_phase6.write_phase_manifest"):
        try:
            run("example.com", "run-en", "run-fr")
            assert False, "expected invalid present OCR artifact to fail schema validation"
        except SchemaValidationError as exc:
            assert "phase4_ocr" in str(exc)


def test_phase6_rejects_non_list_present_phase4_ocr_artifact():
    en_item = {"item_id": "item-1", "page_id": "en-page-1", "url": "https://example.com/p", "language": "en", "text": "Buy", "element_type": "p", "tag": "p", "attributes": None}
    target_item = {"item_id": "item-1", "page_id": "fr-page-1", "url": "https://example.com/fr/p", "language": "fr", "text": "Acheter", "element_type": "img", "tag": "img", "attributes": None}
    artifacts = [
        [en_item],
        [target_item],
        [{"item_id": "item-1", "page_id": "en-page-1", "bbox": {"x": 0, "y": 0, "width": 1, "height": 1}}],
        [{"item_id": "item-1", "page_id": "fr-page-1", "bbox": {"x": 0, "y": 0, "width": 1, "height": 1}}],
        [{"page_id": "en-page-1", "storage_uri": "gs://b/en.png"}],
        [{"page_id": "fr-page-1", "storage_uri": "gs://b/fr.png"}],
        {"item_id": "item-1", "status": "ok"},
    ]

    with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts), patch(
        "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
    ), patch("pipeline.run_phase6.write_json_artifact"), patch("pipeline.run_phase6.write_phase_manifest"):
        try:
            run("example.com", "run-en", "run-fr")
            assert False, "expected non-list OCR artifact to fail schema validation"
        except SchemaValidationError as exc:
            assert "phase4_ocr" in str(exc)


def test_phase6_raises_unexpected_ocr_artifact_read_errors():
    en_item = {"item_id": "item-1", "page_id": "en-page-1", "url": "https://example.com/p", "language": "en", "text": "Buy", "element_type": "p", "tag": "p", "attributes": None}
    target_item = {"item_id": "item-1", "page_id": "fr-page-1", "url": "https://example.com/fr/p", "language": "fr", "text": "Acheter", "element_type": "img", "tag": "img", "attributes": None}
    artifacts = [
        [en_item],
        [target_item],
        [{"item_id": "item-1", "page_id": "en-page-1", "bbox": {"x": 0, "y": 0, "width": 1, "height": 1}}],
        [{"item_id": "item-1", "page_id": "fr-page-1", "bbox": {"x": 0, "y": 0, "width": 1, "height": 1}}],
        [{"page_id": "en-page-1", "storage_uri": "gs://b/en.png"}],
        [{"page_id": "fr-page-1", "storage_uri": "gs://b/fr.png"}],
    ]

    with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts + [RuntimeError("boom")]), patch(
        "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
    ), patch("pipeline.run_phase6.write_json_artifact"), patch("pipeline.run_phase6.write_phase_manifest"):
        try:
            run("example.com", "run-en", "run-fr")
            assert False, "expected unexpected OCR artifact read failures to propagate"
        except RuntimeError as exc:
            assert str(exc) == "boom"
