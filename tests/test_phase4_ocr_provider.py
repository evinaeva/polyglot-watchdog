from pipeline.phase4_ocr_provider import extract_text_with_fallback, ocrspace_extract_text


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


def test_ocrspace_success_skips_vision_fallback():
    calls = {"vision": 0}

    def ocrspace_ok(_):
        return {
            "status": "ok",
            "ocr_text": "hello",
            "ocr_provider": "ocr.space",
            "ocr_engine": "3",
            "ocr_notes": [],
            "provider_meta": {"provider": "ocr.space"},
        }

    def vision_unused(_):
        calls["vision"] += 1
        return {
            "status": "ok",
            "ocr_text": "vision",
            "ocr_provider": "vision",
            "ocr_engine": "builtin",
            "ocr_notes": [],
            "provider_meta": {"provider": "vision"},
        }

    result = extract_text_with_fallback(_tiny_png_bytes(), ocrspace_fn=ocrspace_ok, vision_fn=vision_unused)

    assert result["status"] == "ok"
    assert result["ocr_provider"] == "ocr.space"
    assert calls["vision"] == 0


def test_missing_api_key_attempts_vision_fallback(monkeypatch):
    monkeypatch.delenv("OCR_SPACE_API_KEY", raising=False)
    calls = {"vision": 0}

    def vision_fail(_):
        calls["vision"] += 1
        return {
            "status": "failed",
            "ocr_text": "",
            "ocr_provider": "vision",
            "ocr_engine": "builtin",
            "ocr_notes": ["request_failed"],
            "provider_meta": {"provider": "vision"},
        }

    result = extract_text_with_fallback(_tiny_png_bytes(), vision_fn=vision_fail)

    assert calls["vision"] == 1
    assert result["status"] == "skipped"
    assert result["ocr_notes"] == ["missing_api_key"]


def test_ocrspace_request_failure_attempts_vision_fallback():
    calls = {"vision": 0}

    def ocrspace_failed(_):
        return {
            "status": "failed",
            "ocr_text": "",
            "ocr_provider": "ocr.space",
            "ocr_engine": "3",
            "ocr_notes": ["request_failed"],
            "provider_meta": {"provider": "ocr.space"},
        }

    def vision_fail(_):
        calls["vision"] += 1
        return {
            "status": "failed",
            "ocr_text": "",
            "ocr_provider": "vision",
            "ocr_engine": "builtin",
            "ocr_notes": ["request_failed"],
            "provider_meta": {"provider": "vision"},
        }

    result = extract_text_with_fallback(_tiny_png_bytes(), ocrspace_fn=ocrspace_failed, vision_fn=vision_fail)

    assert calls["vision"] == 1
    assert result["status"] == "failed"
    assert result["ocr_provider"] == "ocr.space"


def test_ocrspace_empty_text_attempts_vision_fallback():
    calls = {"vision": 0}

    def ocrspace_empty(_):
        return {
            "status": "failed",
            "ocr_text": "",
            "ocr_provider": "ocr.space",
            "ocr_engine": "3",
            "ocr_notes": ["empty_text"],
            "provider_meta": {"provider": "ocr.space"},
        }

    def vision_fail(_):
        calls["vision"] += 1
        return {
            "status": "failed",
            "ocr_text": "",
            "ocr_provider": "vision",
            "ocr_engine": "builtin",
            "ocr_notes": ["request_failed"],
            "provider_meta": {"provider": "vision"},
        }

    result = extract_text_with_fallback(_tiny_png_bytes(), ocrspace_fn=ocrspace_empty, vision_fn=vision_fail)

    assert calls["vision"] == 1
    assert result["status"] == "failed"
    assert result["ocr_notes"] == ["empty_text"]


def test_both_providers_fail_preserves_truthful_primary_outcome():
    calls = {"vision": 0}

    def vision_fail(_):
        calls["vision"] += 1
        return {
            "status": "failed",
            "ocr_text": "",
            "ocr_provider": "vision",
            "ocr_engine": "builtin",
            "ocr_notes": ["request_failed"],
            "provider_meta": {"provider": "vision"},
        }

    def ocrspace_skipped(_):
        return {
            "status": "skipped",
            "ocr_text": "",
            "ocr_provider": "ocr.space",
            "ocr_engine": "3",
            "ocr_notes": ["missing_api_key"],
            "provider_meta": {"provider": "ocr.space"},
        }

    skipped_result = extract_text_with_fallback(_tiny_png_bytes(), ocrspace_fn=ocrspace_skipped, vision_fn=vision_fail)
    assert skipped_result["status"] == "skipped"
    assert skipped_result["ocr_notes"] == ["missing_api_key"]

    def ocrspace_failed(_):
        return {
            "status": "failed",
            "ocr_text": "",
            "ocr_provider": "ocr.space",
            "ocr_engine": "3",
            "ocr_notes": ["request_failed"],
            "provider_meta": {"provider": "ocr.space"},
        }

    failed_result = extract_text_with_fallback(_tiny_png_bytes(), ocrspace_fn=ocrspace_failed, vision_fn=vision_fail)
    assert failed_result["status"] == "failed"
    assert failed_result["ocr_notes"] == ["request_failed"]
    assert calls["vision"] == 2


def test_ocrspace_default_timeout_is_40_and_payload_has_language_auto(monkeypatch):
    captured = {}

    def fake_request(url, payload, headers, timeout_s):
        captured.update({"url": url, "payload": payload, "headers": headers, "timeout_s": timeout_s})
        return _FakeResponse({"IsErroredOnProcessing": False, "ParsedResults": [{"ParsedText": "ok"}]})

    monkeypatch.setenv("OCR_SPACE_API_KEY", "test-key")
    monkeypatch.delenv("OCR_SPACE_TIMEOUT_S", raising=False)

    result = ocrspace_extract_text(_tiny_png_bytes(), request_fn=fake_request)

    assert result["status"] == "ok"
    assert captured["timeout_s"] == 40.0
    assert captured["payload"]["language"] == "auto"
