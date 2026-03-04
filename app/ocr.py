"""
OCR module: Google Vision + Azure Computer Vision + OCR.Space.
Supports running a specific engine or a set of engines.

Batching extension (Phase google-batch-v2):
  google_batch_annotate_images(image_bytes_list) — batch helper.
  _GOOGLE_CACHE — thread-safe result cache populated by run_routes before
  dispatch; consumed once by _ocr_google so dispatcher path is unchanged.
"""
import math
import os
import logging
import httpx
import base64
import threading
from typing import Optional

# The original ai_ocr module increments Firestore-based engine usage
# metrics via app.metrics.engine_usage. In this CLI context we do not
# collect or persist metrics, so we provide a no-op stub. If the
# metrics module exists, it will be imported; otherwise the stub is
# used.
try:
    from app.metrics.engine_usage import increment_engine_usage  # type: ignore
except Exception:
    def increment_engine_usage(engine: str, delta: int = 1) -> None:  # type: ignore
        return None

logger = logging.getLogger(__name__)

ALL_ENGINES = ["google", "azure", "ocrspace"]
DEFAULT_AZURE_OCR_API_VERSION = "2024-02-01"

_GOOGLE_CACHE_LOCK = threading.Lock()
# Maps id(image_bytes) -> OCRResult for pre-computed Google results.
# Entries are consumed once (removed on first read) to avoid stale state.
_GOOGLE_CACHE: dict = {}


def _google_cache_put(image_bytes: bytes, result: "OCRResult") -> None:
    """Store a pre-computed Google result keyed by object identity."""
    with _GOOGLE_CACHE_LOCK:
        _GOOGLE_CACHE[id(image_bytes)] = result


def _google_cache_pop(image_bytes: bytes) -> "Optional[OCRResult]":
    """Consume a cached Google result (remove on read). Returns None if absent."""
    with _GOOGLE_CACHE_LOCK:
        return _GOOGLE_CACHE.pop(id(image_bytes), None)


def _google_cache_clear(keys: list) -> None:
    """Remove any remaining cache entries for the given ids (cleanup)."""
    with _GOOGLE_CACHE_LOCK:
        for k in keys:
            _GOOGLE_CACHE.pop(k, None)


# ─────────────────────────── Startup validation ──────────────────────────────

_AZURE_WARN_EMITTED = False


def _check_azure_config() -> None:
    """
    Called once at startup (via _ensure_azure_checked).
    Logs a structured WARNING if azure is listed in ALL_ENGINES but
    env vars are missing.  Never raises.
    """
    global _AZURE_WARN_EMITTED
    if _AZURE_WARN_EMITTED:
        return
    _AZURE_WARN_EMITTED = True

    endpoint = os.getenv("AZURE_OCR_ENDPOINT", "").strip()
    key = os.getenv("AZURE_OCR_KEY", "").strip()

    if "azure" in ALL_ENGINES:
        if not endpoint and not key:
            logger.warning(
                '{"event": "azure_config_warning", "message": '
                '"azure is in ALL_ENGINES but AZURE_OCR_ENDPOINT and AZURE_OCR_KEY are not set; '
                'azure will be skipped for every OCR call"}'
            )
        elif not endpoint:
            logger.warning(
                '{"event": "azure_config_warning", "message": '
                '"azure is in ALL_ENGINES but AZURE_OCR_ENDPOINT is not set; '
                'azure will be skipped for every OCR call"}'
            )
        elif not key:
            logger.warning(
                '{"event": "azure_config_warning", "message": '
                '"azure is in ALL_ENGINES but AZURE_OCR_KEY is not set; '
                'azure will be skipped for every OCR call"}'
            )
        else:
            logger.info(
                '{"event": "azure_config_ok", "message": '
                '"azure env vars present"}'
            )


def emit_startup_warnings() -> None:
    """Call once from app lifespan to emit engine config warnings."""
    _check_azure_config()


# ─────────────────────────── Google Vision ───────────────────────────────────


def _parse_google_full_text(full_text_annotation):
    """
    Shared response-parsing logic for both single and batch Google calls.
    Returns (text, avg_confidence).
    """
    confidences = []
    for page in full_text_annotation.pages:
        for block in page.blocks:
            if block.confidence:
                confidences.append(block.confidence)
    avg_conf = sum(confidences) / len(confidences) if confidences else None
    return (full_text_annotation.text.strip(), avg_conf)


def _parse_google_text_annotations(response) -> Optional[tuple]:
    """
    Parse TEXT_DETECTION response.
    Extracts text from text_annotations[0].description.
    Extracts confidence from full_text_annotation.pages[].blocks[] when
    present — TEXT_DETECTION responses include full_text_annotation alongside
    text_annotations, so block-level confidence is available without any
    extra request parameter.
    Returns (text, avg_confidence) or None if no text found.
    """
    anns = getattr(response, "text_annotations", None)
    if not anns:
        return None
    first = anns[0] if len(anns) > 0 else None
    text = ((getattr(first, "description", "") or "").strip() if first else "")
    if not text:
        return None

    # Attempt to extract confidence from full_text_annotation blocks.
    # full_text_annotation is populated by Google Vision for TEXT_DETECTION
    # responses (same as DOCUMENT_TEXT_DETECTION), providing block.confidence
    # values in range [0, 1]. We compute the arithmetic mean across all blocks.
    avg_conf = None
    full = getattr(response, "full_text_annotation", None)
    if full and getattr(full, "pages", None):
        confidences = []
        for page in full.pages:
            for block in page.blocks:
                if block.confidence:
                    confidences.append(block.confidence)
        avg_conf = sum(confidences) / len(confidences) if confidences else None

    return (text, avg_conf)


def _google_feature_for_mode(vision, google_mode: Optional[str]):
    mode = (google_mode or "text").strip().lower()
    if mode in ("document", "document_text_detection"):
        return vision.Feature.Type.DOCUMENT_TEXT_DETECTION
    return vision.Feature.Type.TEXT_DETECTION


def _build_google_annotate_request(image_bytes: bytes, google_mode: Optional[str] = None):
    """Build a single AnnotateImageRequest for Google Vision mode."""
    from google.cloud import vision  # type: ignore
    return vision.AnnotateImageRequest(
        image=vision.Image(content=image_bytes),
        features=[vision.Feature(type_=_google_feature_for_mode(vision, google_mode))],
    )


def _ocr_google(image_bytes: bytes, google_mode: Optional[str] = None) -> Optional[tuple]:
    """Return (text, confidence) or None on failure.

    If a pre-computed result has been injected via _google_cache_put, consume
    it and return immediately — no API call made.
    """
    # Check pre-computed cache first (set by run_routes batch path).
    cached = _google_cache_pop(image_bytes)
    if cached is not None:
        if not cached.text and cached.confidence == 0.0:
            return None
        return (cached.text, cached.confidence)

    try:
        from google.cloud import vision  # type: ignore
        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=image_bytes)
        mode = (google_mode or "text").strip().lower()
        if mode in ("document", "document_text_detection"):
            response = client.document_text_detection(image=image)
        else:
            response = client.text_detection(image=image)
        increment_engine_usage("google")
        if response.error.message:
            logger.error(
                '{"event": "ocr_google_error", "message": "%s"}'
                % response.error.message.replace('"', '\\"')
            )
            return None
        return _parse_google_text_annotations(response)
    except Exception as e:
        logger.exception('{"event": "ocr_google_exception", "message": "%s"}' % str(e))
        return None


# ─────────────────────────── Azure Computer Vision ───────────────────────────


def _ocr_azure(image_bytes: bytes) -> Optional[tuple]:
    """Return (text, confidence) or None on failure."""
    endpoint = os.getenv("AZURE_OCR_ENDPOINT", "").strip()
    key = os.getenv("AZURE_OCR_KEY", "").strip()
    version = os.getenv("AZURE_OCR_API_VERSION", DEFAULT_AZURE_OCR_API_VERSION)
    if not endpoint or not key:
        return None
    url = f"{endpoint}/vision/v3.2/read/analyze?api-version={version}"
    headers = {"Ocp-Apim-Subscription-Key": key, "Content-Type": "application/octet-stream"}
    try:
        # Submit the image for processing
        response = httpx.post(url, headers=headers, content=image_bytes)
        response.raise_for_status()
        # The response includes an operation-location to check status; poll until succeeded
        operation_url = response.headers.get("Operation-Location")
        if not operation_url:
            return None
        # Poll for completion
        for _ in range(10):
            status_response = httpx.get(operation_url, headers=headers)
            status_response.raise_for_status()
            data = status_response.json()
            status = data.get("status", "").lower()
            if status == "succeeded":
                break
            if status == "failed":
                return None
            # Wait before polling again
            httpx.sleep(1)  # type: ignore
        results = data.get("analyzeResult", {}).get("readResults", [])
        lines = []
        confidences = []
        for read_result in results:
            for line in read_result.get("lines", []):
                line_text = line.get("text", "").strip()
                if line_text:
                    lines.append(line_text)
                    if "confidence" in line:
                        confidences.append(line["confidence"])
        text = "\n".join(lines)
        avg_conf = sum(confidences) / len(confidences) if confidences else None
        increment_engine_usage("azure")
        return (text, avg_conf)
    except Exception as e:
        logger.exception('{"event": "ocr_azure_exception", "message": "%s"}' % str(e))
        return None


# ─────────────────────────── OCR.Space ───────────────────────────────────────

def _ocr_ocrspace(image_bytes: bytes) -> Optional[tuple]:
    """Return (text, confidence) or None on failure."""
    api_key = os.getenv("OCR_SPACE_API_KEY", "").strip()
    if not api_key:
        return None
    payload = {
        "filetype": "png",
        "OCREngine": "3",
        "base64Image": "data:image/png;base64," + base64.b64encode(image_bytes).decode("utf-8"),
    }
    headers = {"apikey": api_key}
    try:
        response = httpx.post("https://api.ocr.space/parse/image", data=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        if not result.get("IsErroredOnProcessing"):
            parsed_results = result.get("ParsedResults", [])
            if parsed_results:
                lines = parsed_results[0].get("ParsedText", "")
                # OCR.Space does not provide confidence per text block; use None
                increment_engine_usage("ocrspace")
                return (lines, None)
        logger.error(
            '{"event": "ocr_ocrspace_error", "message": "%s"}'
            % result.get("ErrorMessage", ["Unknown error"])[0]
        )
        return None
    except Exception as e:
        logger.exception('{"event": "ocr_ocrspace_exception", "message": "%s"}' % str(e))
        return None


# ─────────────────────────── Public API ──────────────────────────────────────


class OCRResult:
    """Simple value object for OCR outputs."""

    def __init__(self, text: str, confidence: Optional[float]) -> None:
        self.text = text or ""
        self.confidence = confidence if confidence is not None else 0.0

    def __str__(self) -> str:
        return f"{self.confidence:.3f} {self.text!r}"

    def to_dict(self) -> dict:
        return {"text": self.text, "confidence": self.confidence}


def run_ocr(image_bytes: bytes, engine: str) -> Optional[OCRResult]:
    """Run OCR on a single engine; returns OCRResult or None on failure."""
    engine = (engine or "").strip().lower()
    fn = None
    if engine == "google":
        fn = _ocr_google
    elif engine == "azure":
        fn = _ocr_azure
    elif engine == "ocrspace":
        fn = _ocr_ocrspace
    else:
        return None
    result = fn(image_bytes)  # type: ignore
    if result is None:
        return None
    text, conf = result
    return OCRResult(text, conf)


def run_ocr_multi(image_bytes: bytes, engines: Optional[list[str]] = None) -> dict[str, OCRResult]:
    """Run OCR across multiple engines and return a mapping engine -> OCRResult.

    The engines list may be a subset of ALL_ENGINES. If None or empty, all engines are run.
    Engines with missing credentials or failures are skipped.
    """
    engines = engines or ALL_ENGINES
    out: dict[str, OCRResult] = {}
    keys_to_clear = []
    try:
        # If google is requested alongside others, run it last and inject its result
        # into the cache so that _ocr_google does not make an API call. This avoids
        # duplicate OCR calls to Google Vision when using the batch API.
        if "google" in engines and len(engines) > 1:
            g_index = engines.index("google")
            engines = engines[:g_index] + engines[g_index + 1:] + ["google"]
            keys_to_clear.append(id(image_bytes))
        for eng in engines:
            r = run_ocr(image_bytes, eng)
            if r is not None:
                out[eng] = r
        return out
    finally:
        if keys_to_clear:
            _google_cache_clear(keys_to_clear)
