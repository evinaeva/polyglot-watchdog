from __future__ import annotations

import base64
import os
import unicodedata
from typing import Optional

import httpx


OCR_SPACE_ENDPOINT_DEFAULT = "https://api.ocr.space/parse/image"
_GOOGLE_VISION_CLIENT = None


def _sanitize_ocr_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text or "")
    return "\n".join(" ".join(line.split()) for line in text.splitlines()).strip()


def _default_request(url: str, payload: dict, headers: dict, timeout_s: float) -> httpx.Response:
    return httpx.post(url, data=payload, headers=headers, timeout=timeout_s)


def _google_client():
    global _GOOGLE_VISION_CLIENT
    if _GOOGLE_VISION_CLIENT is None:
        from google.cloud import vision  # type: ignore

        _GOOGLE_VISION_CLIENT = vision.ImageAnnotatorClient()
    return _GOOGLE_VISION_CLIENT


def _parse_google_text(response) -> Optional[str]:
    full = getattr(response, "full_text_annotation", None)
    if full:
        text = _sanitize_ocr_text(str(getattr(full, "text", "")))
        if text:
            return text
    annotations = getattr(response, "text_annotations", None)
    if annotations and len(annotations) > 0:
        first = annotations[0]
        text = _sanitize_ocr_text(str(getattr(first, "description", "")))
        if text:
            return text
    return None


def _googlevision_extract_text(image_bytes: bytes) -> dict:
    try:
        from google.cloud import vision  # type: ignore

        client = _google_client()
        request = vision.AnnotateImageRequest(
            image=vision.Image(content=image_bytes),
            features=[vision.Feature(type_=vision.Feature.Type.TEXT_DETECTION)],
        )
        response = client.annotate_image(request=request)
        error = getattr(getattr(response, "error", None), "message", "")
        if error:
            return {
                "status": "failed",
                "ocr_text": "",
                "ocr_provider": "google.vision",
                "ocr_engine": "text_detection",
                "ocr_notes": ["google_error"],
                "provider_meta": {"provider": "google.vision", "error_message": error},
            }
        parsed_text = _parse_google_text(response)
        if not parsed_text:
            return {
                "status": "failed",
                "ocr_text": "",
                "ocr_provider": "google.vision",
                "ocr_engine": "text_detection",
                "ocr_notes": ["empty_text"],
                "provider_meta": {"provider": "google.vision"},
            }
        return {
            "status": "ok",
            "ocr_text": parsed_text,
            "ocr_provider": "google.vision",
            "ocr_engine": "text_detection",
            "ocr_notes": ["fallback_from_ocrspace"],
            "provider_meta": {"provider": "google.vision"},
        }
    except Exception as exc:
        return {
            "status": "failed",
            "ocr_text": "",
            "ocr_provider": "google.vision",
            "ocr_engine": "text_detection",
            "ocr_notes": ["request_failed"],
            "provider_meta": {"provider": "google.vision", "error": str(exc)},
        }


def _fallback_to_google_if_needed(image_bytes: bytes, ocrspace_result: dict) -> dict:
    google_result = _googlevision_extract_text(image_bytes)
    if google_result.get("status") == "ok":
        return {
            "status": "ok",
            "ocr_text": str(google_result.get("ocr_text", "")),
            "ocr_provider": "ocr.space",
            "ocr_engine": "3",
            "ocr_notes": [*ocrspace_result.get("ocr_notes", []), "fallback_google_vision"],
            "provider_meta": {
                "provider": "ocr.space",
                "fallback": {
                    "provider": "google.vision",
                    "status": google_result.get("status"),
                    "notes": google_result.get("ocr_notes", []),
                    "trigger_status": ocrspace_result.get("status"),
                    "trigger_notes": ocrspace_result.get("ocr_notes", []),
                },
            },
        }
    ocrspace_result["provider_meta"] = {
        **ocrspace_result.get("provider_meta", {}),
        "fallback": {
            "provider": "google.vision",
            "status": google_result.get("status"),
            "notes": google_result.get("ocr_notes", []),
        },
    }
    return ocrspace_result


def ocrspace_extract_text(
    image_bytes: bytes,
    *,
    request_fn=None,
) -> dict:
    api_key = os.getenv("OCR_SPACE_API_KEY", "").strip()
    if not api_key:
        result = {
            "status": "skipped",
            "ocr_text": "",
            "ocr_provider": "ocr.space",
            "ocr_engine": "3",
            "ocr_notes": ["missing_api_key"],
            "provider_meta": {"provider": "ocr.space"},
        }
        return _fallback_to_google_if_needed(image_bytes, result)

    endpoint = os.getenv("OCR_SPACE_ENDPOINT", OCR_SPACE_ENDPOINT_DEFAULT).strip() or OCR_SPACE_ENDPOINT_DEFAULT
    timeout_s = float(os.getenv("OCR_SPACE_TIMEOUT_S", "20"))
    payload = {
        "filetype": "png",
        "OCREngine": "3",
        "base64Image": "data:image/png;base64," + base64.b64encode(image_bytes).decode("utf-8"),
    }
    headers = {"apikey": api_key}

    request = request_fn or _default_request
    try:
        response = request(endpoint, payload, headers, timeout_s)
        response.raise_for_status()
        result = response.json()
    except Exception as exc:
        result = {
            "status": "failed",
            "ocr_text": "",
            "ocr_provider": "ocr.space",
            "ocr_engine": "3",
            "ocr_notes": ["request_failed"],
            "provider_meta": {"provider": "ocr.space", "error": str(exc)},
        }
        return _fallback_to_google_if_needed(image_bytes, result)

    if not isinstance(result, dict):
        outcome = {
            "status": "failed",
            "ocr_text": "",
            "ocr_provider": "ocr.space",
            "ocr_engine": "3",
            "ocr_notes": ["malformed_response"],
            "provider_meta": {"provider": "ocr.space"},
        }
        return _fallback_to_google_if_needed(image_bytes, outcome)

    if result.get("IsErroredOnProcessing"):
        outcome = {
            "status": "failed",
            "ocr_text": "",
            "ocr_provider": "ocr.space",
            "ocr_engine": "3",
            "ocr_notes": ["errored_on_processing"],
            "provider_meta": {"provider": "ocr.space", "error_message": result.get("ErrorMessage")},
        }
        return _fallback_to_google_if_needed(image_bytes, outcome)

    parsed_results = result.get("ParsedResults")
    parsed_text = ""
    if isinstance(parsed_results, list) and parsed_results:
        first = parsed_results[0] if isinstance(parsed_results[0], dict) else {}
        parsed_text = _sanitize_ocr_text(str(first.get("ParsedText", "")))

    if not parsed_text:
        outcome = {
            "status": "failed",
            "ocr_text": "",
            "ocr_provider": "ocr.space",
            "ocr_engine": "3",
            "ocr_notes": ["empty_text"],
            "provider_meta": {"provider": "ocr.space"},
        }
        return _fallback_to_google_if_needed(image_bytes, outcome)

    return {
        "status": "ok",
        "ocr_text": parsed_text,
        "ocr_provider": "ocr.space",
        "ocr_engine": "3",
        "ocr_notes": [],
        "provider_meta": {"provider": "ocr.space", "endpoint": endpoint},
    }
