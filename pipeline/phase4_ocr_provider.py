from __future__ import annotations

import base64
import os
import unicodedata

import httpx


OCR_SPACE_ENDPOINT_DEFAULT = "https://api.ocr.space/parse/image"


def _sanitize_ocr_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text or "")
    return "\n".join(" ".join(line.split()) for line in text.splitlines()).strip()


def _default_request(url: str, payload: dict, headers: dict, timeout_s: float) -> httpx.Response:
    return httpx.post(url, data=payload, headers=headers, timeout=timeout_s)


def ocrspace_extract_text(
    image_bytes: bytes,
    *,
    request_fn=None,
) -> dict:
    api_key = os.getenv("OCR_SPACE_API_KEY", "").strip()
    if not api_key:
        return {
            "status": "skipped",
            "ocr_text": "",
            "ocr_provider": "ocr.space",
            "ocr_engine": "3",
            "ocr_notes": ["missing_api_key"],
            "provider_meta": {"provider": "ocr.space"},
        }

    endpoint = os.getenv("OCR_SPACE_ENDPOINT", OCR_SPACE_ENDPOINT_DEFAULT).strip() or OCR_SPACE_ENDPOINT_DEFAULT
    timeout_s = float(os.getenv("OCR_SPACE_TIMEOUT_S", "40"))
    payload = {
        "filetype": "png",
        "OCREngine": "3",
        "language": "auto",
        "base64Image": "data:image/png;base64," + base64.b64encode(image_bytes).decode("utf-8"),
    }
    headers = {"apikey": api_key}

    request = request_fn or _default_request
    try:
        response = request(endpoint, payload, headers, timeout_s)
        response.raise_for_status()
        result = response.json()
    except Exception as exc:
        return {
            "status": "failed",
            "ocr_text": "",
            "ocr_provider": "ocr.space",
            "ocr_engine": "3",
            "ocr_notes": ["request_failed"],
            "provider_meta": {"provider": "ocr.space", "error": str(exc)},
        }

    if not isinstance(result, dict):
        return {
            "status": "failed",
            "ocr_text": "",
            "ocr_provider": "ocr.space",
            "ocr_engine": "3",
            "ocr_notes": ["malformed_response"],
            "provider_meta": {"provider": "ocr.space"},
        }

    if result.get("IsErroredOnProcessing"):
        return {
            "status": "failed",
            "ocr_text": "",
            "ocr_provider": "ocr.space",
            "ocr_engine": "3",
            "ocr_notes": ["errored_on_processing"],
            "provider_meta": {"provider": "ocr.space", "error_message": result.get("ErrorMessage")},
        }

    parsed_results = result.get("ParsedResults")
    parsed_text = ""
    if isinstance(parsed_results, list) and parsed_results:
        first = parsed_results[0] if isinstance(parsed_results[0], dict) else {}
        parsed_text = _sanitize_ocr_text(str(first.get("ParsedText", "")))

    if not parsed_text:
        return {
            "status": "failed",
            "ocr_text": "",
            "ocr_provider": "ocr.space",
            "ocr_engine": "3",
            "ocr_notes": ["empty_text"],
            "provider_meta": {"provider": "ocr.space"},
        }

    return {
        "status": "ok",
        "ocr_text": parsed_text,
        "ocr_provider": "ocr.space",
        "ocr_engine": "3",
        "ocr_notes": [],
        "provider_meta": {"provider": "ocr.space", "endpoint": endpoint},
    }


def vision_extract_text(
    image_bytes: bytes,  # noqa: ARG001
) -> dict:
    # The baseline implementation intentionally avoids direct Vision API calls
    # unless explicit integration is configured.
    return {
        "status": "skipped",
        "ocr_text": "",
        "ocr_provider": "vision",
        "ocr_engine": "",
        "ocr_notes": ["vision_not_configured"],
        "provider_meta": {"provider": "vision"},
    }


def extract_text_with_fallback(
    image_bytes: bytes,
    *,
    ocrspace_fn=ocrspace_extract_text,
    vision_fn=vision_extract_text,
) -> dict:
    primary = ocrspace_fn(image_bytes)
    if primary.get("status") == "ok":
        return primary

    # Attempt Vision fallback for non-OK OCR.Space outcomes. Preserve the
    # original OCR.Space status if fallback does not produce usable text.
    fallback = vision_fn(image_bytes)
    if fallback.get("status") == "ok":
        return fallback
    return primary
