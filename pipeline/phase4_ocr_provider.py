from __future__ import annotations

import base64
import os
import unicodedata
from typing import Optional

import httpx


OCR_SPACE_ENDPOINT_DEFAULT = "https://api.ocr.space/parse/image"
GOOGLE_VISION_ENDPOINT_DEFAULT = "https://vision.googleapis.com/v1/images:annotate"


def _sanitize_ocr_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text or "")
    return "\n".join(" ".join(line.split()) for line in text.splitlines()).strip()


def _is_usable_text(text: str) -> bool:
    return bool("".join((text or "").split()))


def _default_request(url: str, payload: dict, headers: dict, timeout_s: float) -> httpx.Response:
    return httpx.post(url, data=payload, headers=headers, timeout=timeout_s)


def _default_google_request(url: str, payload: dict, headers: dict, timeout_s: float) -> httpx.Response:
    return httpx.post(url, json=payload, headers=headers, timeout=timeout_s)


def _short_error_from_meta(provider_meta: dict | None) -> str:
    meta = provider_meta if isinstance(provider_meta, dict) else {}
    raw = str(meta.get("error") or meta.get("error_message") or "").strip()
    if not raw:
        return ""
    return raw[:120]


def ocrspace_extract_text(
    image_bytes: bytes,
    *,
    request_fn=None,
    vision_client_factory=None,
) -> dict:
    api_key = os.getenv("OCR_SPACE_API_KEY", "").strip()
    if not api_key:
        fallback = _googlevision_extract_text(image_bytes, vision_client_factory=vision_client_factory)
        if vision_client_factory is not None and fallback.get("status") == "ok":
            return {
                **fallback,
                "ocr_notes": ["used_fallback_from_ocr.space", "ocr_space_missing_api_key", *list(fallback.get("ocr_notes", []))],
            }
        if fallback.get("status") == "ok":
            return {
                "status": "ok",
                "ocr_text": str(fallback.get("ocr_text", "")),
                "ocr_provider": "ocr.space",
                "ocr_engine": "3",
                "ocr_notes": ["fallback_google_vision"],
                "provider_meta": {"provider": "ocr.space", "fallback": {"provider": fallback.get("ocr_provider", "google_vision")}},
            }
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
        result = {
            "status": "failed",
            "ocr_text": "",
            "ocr_provider": "ocr.space",
            "ocr_engine": "3",
            "ocr_notes": ["request_failed"],
            "provider_meta": {"provider": "ocr.space", "error": str(exc)},
        }
        return result

    if not isinstance(result, dict):
        fallback = _googlevision_extract_text(image_bytes, vision_client_factory=vision_client_factory)
        if vision_client_factory is not None and fallback.get("status") == "ok":
            return {
                **fallback,
                "ocr_notes": ["used_fallback_from_ocr.space", "malformed_response", *list(fallback.get("ocr_notes", []))],
            }
        if fallback.get("status") == "ok":
            return {
                "status": "ok",
                "ocr_text": str(fallback.get("ocr_text", "")),
                "ocr_provider": "ocr.space",
                "ocr_engine": "3",
                "ocr_notes": ["fallback_google_vision", "malformed_response"],
                "provider_meta": {"provider": "ocr.space", "fallback": {"provider": fallback.get("ocr_provider", "google_vision")}},
            }
        outcome = {
            "status": "failed",
            "ocr_text": "",
            "ocr_provider": "ocr.space",
            "ocr_engine": "3",
            "ocr_notes": ["malformed_response", "fallback_empty_text", "fallback_failed"],
            "provider_meta": {"provider": "ocr.space", "fallback": {"provider": fallback.get("ocr_provider", "google_vision")}},
        }
        return outcome

    if result.get("IsErroredOnProcessing"):
        outcome = {
            "status": "failed",
            "ocr_text": "",
            "ocr_provider": "ocr.space",
            "ocr_engine": "3",
            "ocr_notes": ["errored_on_processing"],
            "provider_meta": {"provider": "ocr.space", "error_message": result.get("ErrorMessage")},
        }
        return outcome

    parsed_results = result.get("ParsedResults")
    parsed_text = ""
    if isinstance(parsed_results, list) and parsed_results:
        first = parsed_results[0] if isinstance(parsed_results[0], dict) else {}
        parsed_text = _sanitize_ocr_text(str(first.get("ParsedText", "")))

    if not _is_usable_text(parsed_text):
        fallback = _googlevision_extract_text(image_bytes, vision_client_factory=vision_client_factory)
        if vision_client_factory is not None and fallback.get("status") == "ok":
            return {
                **fallback,
                "ocr_notes": ["used_fallback_from_ocr.space", "ocr_space_empty_text", *list(fallback.get("ocr_notes", []))],
            }
        if fallback.get("status") == "ok":
            return {
                "status": "ok",
                "ocr_text": str(fallback.get("ocr_text", "")),
                "ocr_provider": "ocr.space",
                "ocr_engine": "3",
                "ocr_notes": ["fallback_google_vision", "ocr_space_empty_text"],
                "provider_meta": {"provider": "ocr.space", "fallback": {"provider": fallback.get("ocr_provider", "google_vision")}},
            }
        return {
            "status": "failed",
            "ocr_text": "",
            "ocr_provider": "ocr.space",
            "ocr_engine": "3",
            "ocr_notes": ["empty_text", "fallback_empty_text", "fallback_failed"],
            "provider_meta": {"provider": "ocr.space", "fallback": {"provider": fallback.get("ocr_provider", "google_vision")}},
        }

    return {
        "status": "ok",
        "ocr_text": parsed_text,
        "ocr_provider": "ocr.space",
        "ocr_engine": "3",
        "ocr_notes": [],
        "provider_meta": {"provider": "ocr.space", "endpoint": endpoint},
    }


def google_vision_extract_text(
    image_bytes: bytes,
    *,
    request_fn=None,
) -> dict:
    api_key = os.getenv("GOOGLE_VISION_API_KEY", "").strip()
    if not api_key:
        return {
            "status": "skipped",
            "ocr_text": "",
            "ocr_provider": "google_vision",
            "ocr_engine": "text_detection",
            "ocr_notes": ["missing_api_key"],
            "provider_meta": {"provider": "google_vision"},
        }

    endpoint = os.getenv("GOOGLE_VISION_ENDPOINT", GOOGLE_VISION_ENDPOINT_DEFAULT).strip() or GOOGLE_VISION_ENDPOINT_DEFAULT
    timeout_s = float(os.getenv("GOOGLE_VISION_TIMEOUT_S", "20"))
    payload = {
        "requests": [
            {
                "image": {"content": base64.b64encode(image_bytes).decode("utf-8")},
                "features": [{"type": "TEXT_DETECTION"}],
            }
        ]
    }
    headers = {"Content-Type": "application/json"}

    request = request_fn or _default_google_request
    try:
        response = request(f"{endpoint}?key={api_key}", payload, headers, timeout_s)
        response.raise_for_status()
        result = response.json()
    except Exception as exc:
        return {
            "status": "failed",
            "ocr_text": "",
            "ocr_provider": "google_vision",
            "ocr_engine": "text_detection",
            "ocr_notes": ["request_failed"],
            "provider_meta": {"provider": "google_vision", "error": str(exc)},
        }

    if not isinstance(result, dict):
        return {
            "status": "failed",
            "ocr_text": "",
            "ocr_provider": "google_vision",
            "ocr_engine": "text_detection",
            "ocr_notes": ["malformed_response"],
            "provider_meta": {"provider": "google_vision"},
        }

    responses = result.get("responses")
    if not isinstance(responses, list) or not responses:
        return {
            "status": "failed",
            "ocr_text": "",
            "ocr_provider": "google_vision",
            "ocr_engine": "text_detection",
            "ocr_notes": ["empty_response"],
            "provider_meta": {"provider": "google_vision"},
        }
    first = responses[0] if isinstance(responses[0], dict) else {}
    if first.get("error"):
        return {
            "status": "failed",
            "ocr_text": "",
            "ocr_provider": "google_vision",
            "ocr_engine": "text_detection",
            "ocr_notes": ["errored_on_processing"],
            "provider_meta": {"provider": "google_vision", "error_message": first.get("error", {}).get("message")},
        }

    parsed_text = _sanitize_ocr_text(
        str(first.get("fullTextAnnotation", {}).get("text", "")).strip()
        or str((first.get("textAnnotations") or [{}])[0].get("description", "")).strip()
    )
    if not parsed_text:
        return {
            "status": "failed",
            "ocr_text": "",
            "ocr_provider": "google_vision",
            "ocr_engine": "text_detection",
            "ocr_notes": ["empty_text"],
            "provider_meta": {"provider": "google_vision"},
        }

    return {
        "status": "ok",
        "ocr_text": parsed_text,
        "ocr_provider": "google_vision",
        "ocr_engine": "text_detection",
        "ocr_notes": [],
        "provider_meta": {"provider": "google_vision", "endpoint": endpoint},
    }


def _googlevision_extract_text(
    image_bytes: bytes,
    *,
    request_fn=None,
    vision_client_factory=None,
) -> dict:
    if vision_client_factory is not None:
        try:
            client = vision_client_factory()
            response = client.text_detection(image=image_bytes)
            error_message = str(getattr(getattr(response, "error", None), "message", "")).strip()
            if error_message:
                return {
                    "status": "failed",
                    "ocr_text": "",
                    "ocr_provider": "google_vision",
                    "ocr_engine": "text_detection",
                    "ocr_notes": ["request_failed"],
                    "provider_meta": {"provider": "google_vision", "error_message": error_message},
                }
            annotations = list(getattr(response, "text_annotations", []) or [])
            text = _sanitize_ocr_text(str(getattr(annotations[0], "description", ""))) if annotations else ""
            if not _is_usable_text(text):
                return {
                    "status": "failed",
                    "ocr_text": "",
                    "ocr_provider": "google_vision",
                    "ocr_engine": "text_detection",
                    "ocr_notes": ["empty_text"],
                    "provider_meta": {"provider": "google_vision"},
                }
            return {
                "status": "ok",
                "ocr_text": text,
                "ocr_provider": "google_vision",
                "ocr_engine": "text_detection",
                "ocr_notes": [],
                "provider_meta": {"provider": "google_vision"},
            }
        except Exception as exc:
            return {
                "status": "failed",
                "ocr_text": "",
                "ocr_provider": "google_vision",
                "ocr_engine": "text_detection",
                "ocr_notes": ["request_failed"],
                "provider_meta": {"provider": "google_vision", "error": str(exc)},
            }
    return google_vision_extract_text(image_bytes, request_fn=request_fn)


def extract_text_with_ocrspace_fallback(image_bytes: bytes) -> dict:
    primary = ocrspace_extract_text(image_bytes)
    if primary.get("status") == "ok":
        primary_notes = [str(note).strip() for note in primary.get("ocr_notes", []) if str(note).strip()]
        if "fallback_google_vision" in primary_notes:
            return {
                **primary,
                "ocr_provider": "google_vision",
                "ocr_engine": "text_detection",
                "ocr_notes": ["fallback_from_ocr_space", "ocr_space_missing_api_key", *primary_notes],
                "provider_meta": {
                    "primary_attempt_provider": "ocr.space",
                    "fallback_provider": "google_vision",
                    "fallback_attempted": True,
                    "attempted_providers": ["ocr.space", "google_vision"],
                    "reason_for_fallback": "ocr_space_missing_api_key",
                    "ocr_space_status": "skipped",
                    "google_vision_status": "ok",
                    "ocr_space_notes": ["missing_api_key"],
                    "ocr_space_error_summary": "",
                },
            }
        return primary

    primary_notes = [str(note).strip() for note in primary.get("ocr_notes", []) if str(note).strip()]
    primary_error = _short_error_from_meta(primary.get("provider_meta"))
    primary_reason = primary_notes[0] if primary_notes else primary.get("status", "failed")
    reason_token = f"ocr_space_{primary_reason}"
    fallback = _googlevision_extract_text(image_bytes)
    fallback_error = _short_error_from_meta(fallback.get("provider_meta"))

    if fallback.get("status") == "ok":
        fallback_notes = [str(note).strip() for note in fallback.get("ocr_notes", []) if str(note).strip()]
        return {
            **fallback,
            "ocr_notes": ["fallback_from_ocr_space", reason_token, *fallback_notes],
            "provider_meta": {
                "primary_attempt_provider": "ocr.space",
                "fallback_provider": "google_vision",
                "fallback_attempted": True,
                "attempted_providers": ["ocr.space", "google_vision"],
                "reason_for_fallback": reason_token,
                "ocr_space_status": primary.get("status"),
                "google_vision_status": fallback.get("status"),
                "ocr_space_notes": primary_notes[:2],
                "ocr_space_error_summary": primary_error,
            },
        }

    fallback_notes = [str(note).strip() for note in fallback.get("ocr_notes", []) if str(note).strip()]
    merged_notes = [*primary_notes, "fallback_from_ocr_space", reason_token]
    if fallback_notes:
        merged_notes.append(f"google_vision_{fallback_notes[0]}")
    final_status = "skipped" if primary.get("status") == "skipped" and fallback.get("status") == "skipped" else "failed"
    return {
        "status": final_status,
        "ocr_text": "",
        "ocr_provider": str(fallback.get("ocr_provider") or "google_vision"),
        "ocr_engine": str(fallback.get("ocr_engine") or "text_detection"),
        "ocr_notes": merged_notes,
        "provider_meta": {
            "primary_attempt_provider": "ocr.space",
            "fallback_provider": "google_vision",
            "fallback_attempted": True,
            "attempted_providers": ["ocr.space", "google_vision"],
            "reason_for_fallback": reason_token,
            "ocr_space_status": primary.get("status"),
            "google_vision_status": fallback.get("status"),
            "ocr_space_notes": primary_notes[:2],
            "google_vision_notes": fallback_notes[:2],
            "ocr_space_error_summary": primary_error,
            "google_vision_error_summary": fallback_error,
        },
    }
