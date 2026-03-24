from __future__ import annotations

import base64
import os
import unicodedata

import httpx


OCR_SPACE_ENDPOINT_DEFAULT = "https://api.ocr.space/parse/image"
GOOGLE_VISION_ENGINE_DEFAULT = "text_detection"


def _sanitize_ocr_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text or "")
    return "\n".join(" ".join(line.split()) for line in text.splitlines()).strip()


def _is_usable_text(text: str) -> bool:
    return bool("".join((text or "").split()))


def _default_request(url: str, payload: dict, headers: dict, timeout_s: float) -> httpx.Response:
    return httpx.post(url, data=payload, headers=headers, timeout=timeout_s)


def _ocrspace_extract_text(
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

    if not _is_usable_text(parsed_text):
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


def _google_vision_extract_text(image_bytes: bytes, *, vision_client_factory=None) -> dict:
    try:
        if vision_client_factory is None:
            from google.cloud import vision  # type: ignore

            vision_client_factory = vision.ImageAnnotatorClient
            image = vision.Image(content=image_bytes)
        else:
            image = image_bytes

        client = vision_client_factory()
        response = client.text_detection(image=image)
    except Exception as exc:
        return {
            "status": "failed",
            "ocr_text": "",
            "ocr_provider": "google_vision",
            "ocr_engine": GOOGLE_VISION_ENGINE_DEFAULT,
            "ocr_notes": ["request_failed"],
            "provider_meta": {"provider": "google_vision", "error": str(exc)},
        }

    error = getattr(getattr(response, "error", None), "message", "")
    if error:
        return {
            "status": "failed",
            "ocr_text": "",
            "ocr_provider": "google_vision",
            "ocr_engine": GOOGLE_VISION_ENGINE_DEFAULT,
            "ocr_notes": ["errored_on_processing"],
            "provider_meta": {"provider": "google_vision", "error_message": str(error)},
        }

    annotations = getattr(response, "text_annotations", None)
    first = annotations[0] if annotations else None
    text = _sanitize_ocr_text(str(getattr(first, "description", "") or ""))
    if not _is_usable_text(text):
        return {
            "status": "failed",
            "ocr_text": "",
            "ocr_provider": "google_vision",
            "ocr_engine": GOOGLE_VISION_ENGINE_DEFAULT,
            "ocr_notes": ["empty_text"],
            "provider_meta": {"provider": "google_vision"},
        }

    return {
        "status": "ok",
        "ocr_text": text,
        "ocr_provider": "google_vision",
        "ocr_engine": GOOGLE_VISION_ENGINE_DEFAULT,
        "ocr_notes": [],
        "provider_meta": {"provider": "google_vision"},
    }


def ocrspace_extract_text(
    image_bytes: bytes,
    *,
    request_fn=None,
    vision_client_factory=None,
) -> dict:
    primary = _ocrspace_extract_text(image_bytes, request_fn=request_fn)
    if primary.get("status") == "ok" and _is_usable_text(str(primary.get("ocr_text", ""))):
        return primary

    fallback = _google_vision_extract_text(image_bytes, vision_client_factory=vision_client_factory)
    if fallback.get("status") == "ok" and _is_usable_text(str(fallback.get("ocr_text", ""))):
        fallback_notes = list(primary.get("ocr_notes", []))
        fallback_meta = dict(fallback.get("provider_meta", {}))
        fallback_meta["fallback_from"] = {
            "provider": primary.get("ocr_provider"),
            "engine": primary.get("ocr_engine"),
            "status": primary.get("status"),
            "notes": fallback_notes,
            "meta": primary.get("provider_meta", {}),
        }
        fallback["ocr_notes"] = ["used_fallback_from_ocr.space"]
        fallback["provider_meta"] = fallback_meta
        return fallback

    fallback_notes = [f"fallback_{note}" for note in list(fallback.get("ocr_notes", []))]
    return {
        "status": primary.get("status", "failed"),
        "ocr_text": "",
        "ocr_provider": primary.get("ocr_provider", "ocr.space"),
        "ocr_engine": primary.get("ocr_engine", "3"),
        "ocr_notes": list(primary.get("ocr_notes", [])) + fallback_notes + ["fallback_failed"],
        "provider_meta": {
            "provider": primary.get("ocr_provider", "ocr.space"),
            "primary": primary.get("provider_meta", {}),
            "fallback": fallback.get("provider_meta", {}),
            "fallback_provider": fallback.get("ocr_provider", "google_vision"),
            "fallback_status": fallback.get("status", "failed"),
            "fallback_notes": fallback.get("ocr_notes", []),
        },
    }
