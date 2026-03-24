from unittest.mock import patch

from pipeline.phase4_ocr_provider import extract_text_with_ocrspace_fallback, ocrspace_extract_text


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


def test_ocrspace_usable_text_returns_primary_without_fallback():
    with patch(
        "pipeline.phase4_ocr_provider.ocrspace_extract_text",
        return_value={
            "status": "ok",
            "ocr_text": "primary",
            "ocr_provider": "ocr.space",
            "ocr_engine": "3",
            "ocr_notes": [],
            "provider_meta": {"provider": "ocr.space"},
        },
    ), patch(
        "pipeline.phase4_ocr_provider.google_vision_extract_text",
        side_effect=AssertionError("fallback should not be called"),
    ):
        result = extract_text_with_ocrspace_fallback(_tiny_png_bytes())

    assert result["status"] == "ok"
    assert result["ocr_provider"] == "ocr.space"


def test_ocrspace_empty_text_triggers_google_fallback(monkeypatch):
    with patch(
        "pipeline.phase4_ocr_provider.ocrspace_extract_text",
        return_value={
            "status": "failed",
            "ocr_text": "",
            "ocr_provider": "ocr.space",
            "ocr_engine": "3",
            "ocr_notes": ["empty_text"],
            "provider_meta": {"provider": "ocr.space"},
        },
    ), patch(
        "pipeline.phase4_ocr_provider.google_vision_extract_text",
        return_value={
            "status": "ok",
            "ocr_text": "Vision text",
            "ocr_provider": "google_vision",
            "ocr_engine": "text_detection",
            "ocr_notes": [],
            "provider_meta": {"provider": "google_vision"},
        },
    ) as fallback_call:
        result = extract_text_with_ocrspace_fallback(_tiny_png_bytes())

    assert fallback_call.call_count == 1
    assert result["status"] == "ok"
    assert result["ocr_provider"] == "google_vision"
    assert "fallback_from_ocr_space" in result["ocr_notes"]


def test_ocrspace_whitespace_text_triggers_google_fallback(monkeypatch):
    monkeypatch.setenv("OCR_SPACE_API_KEY", "test-key")

    def fake_request(*_args, **_kwargs):
        return _FakeResponse({"IsErroredOnProcessing": False, "ParsedResults": [{"ParsedText": "   \n\t"}]})

    with patch(
        "pipeline.phase4_ocr_provider.google_vision_extract_text",
        return_value={
            "status": "ok",
            "ocr_text": "fallback",
            "ocr_provider": "google_vision",
            "ocr_engine": "text_detection",
            "ocr_notes": [],
            "provider_meta": {"provider": "google_vision"},
        },
    ) as fallback_call, patch(
        "pipeline.phase4_ocr_provider._default_request", side_effect=fake_request
    ):
        result = extract_text_with_ocrspace_fallback(_tiny_png_bytes())

    assert fallback_call.call_count == 1
    assert result["ocr_provider"] == "google_vision"


def test_ocrspace_failure_triggers_google_fallback():
    with patch(
        "pipeline.phase4_ocr_provider.ocrspace_extract_text",
        return_value={
            "status": "failed",
            "ocr_text": "",
            "ocr_provider": "ocr.space",
            "ocr_engine": "3",
            "ocr_notes": ["request_failed"],
            "provider_meta": {"provider": "ocr.space"},
        },
    ), patch(
        "pipeline.phase4_ocr_provider.google_vision_extract_text",
        return_value={
            "status": "ok",
            "ocr_text": "bonjour",
            "ocr_provider": "google_vision",
            "ocr_engine": "text_detection",
            "ocr_notes": [],
            "provider_meta": {"provider": "google_vision"},
        },
    ) as fallback_call:
        result = extract_text_with_ocrspace_fallback(_tiny_png_bytes())

    assert fallback_call.call_count == 1
    assert result["ocr_provider"] == "google_vision"


def test_both_providers_fail_reports_truthful_fallback_metadata():
    with patch(
        "pipeline.phase4_ocr_provider.ocrspace_extract_text",
        return_value={
            "status": "failed",
            "ocr_text": "",
            "ocr_provider": "ocr.space",
            "ocr_engine": "3",
            "ocr_notes": ["request_failed"],
            "provider_meta": {"provider": "ocr.space", "error": "primary"},
        },
    ), patch(
        "pipeline.phase4_ocr_provider.google_vision_extract_text",
        return_value={
            "status": "failed",
            "ocr_text": "",
            "ocr_provider": "google_vision",
            "ocr_engine": "text_detection",
            "ocr_notes": ["request_failed"],
            "provider_meta": {"provider": "google_vision", "error": "fallback"},
        },
    ):
        result = extract_text_with_ocrspace_fallback(_tiny_png_bytes())

    assert result["status"] == "failed"
    assert result["ocr_provider"] == "google_vision"
    assert result["provider_meta"]["fallback_attempted"] is True
    assert result["provider_meta"]["attempted_providers"] == ["ocr.space", "google_vision"]


def test_both_providers_missing_keys_returns_skipped_status_transition(monkeypatch):
    monkeypatch.delenv("OCR_SPACE_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_VISION_API_KEY", raising=False)

    result = extract_text_with_ocrspace_fallback(_tiny_png_bytes())

    assert result["status"] == "skipped"
    assert result["ocr_text"] == ""
    assert "ocr_space_missing_api_key" in result["ocr_notes"]


def test_ocrspace_request_payload_keeps_engine_language_timeout(monkeypatch):
    captured = {}

    def fake_request(url, payload, headers, timeout_s):
        captured.update({"url": url, "payload": payload, "headers": headers, "timeout_s": timeout_s})
        return _FakeResponse({"IsErroredOnProcessing": False, "ParsedResults": [{"ParsedText": "ok"}]})

    monkeypatch.setenv("OCR_SPACE_API_KEY", "test-key")
    monkeypatch.delenv("OCR_SPACE_TIMEOUT_S", raising=False)

    result = ocrspace_extract_text(_tiny_png_bytes(), request_fn=fake_request)

    assert result["status"] == "ok"
    assert captured["payload"]["OCREngine"] == "3"
    assert captured["payload"]["language"] == "auto"
    assert captured["payload"]["base64Image"].startswith("data:image/png;base64,")
    assert captured["headers"]["apikey"] == "test-key"
    assert captured["timeout_s"] == 40.0
