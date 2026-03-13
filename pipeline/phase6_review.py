"""Phase 6 internal review pipeline.

This module keeps rich QA metadata in `issue["evidence"]` while preserving the
persisted top-level issue schema contract.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from pipeline.phase5_normalizer import normalize_text
from pipeline.phase6_providers import Phase6ReviewProvider

_PLACEHOLDER_RE = re.compile(r"(%[^%]+%|\[[^\]]+\]|<[^>]+>)")
_DYNAMIC_NUMBER_RE = re.compile(r"\d+")
_HEADER_ONLINE_CLASS_TOKENS = {"header_online", "bc_flex", "bc_flex_items_center"}
_IMAGE_TAGS = {"img", "image"}

REVIEW_TO_CATEGORY = {
    "SPELLING": "TRANSLATION_MISMATCH",
    "GRAMMAR": "TRANSLATION_MISMATCH",
    "MEANING": "TRANSLATION_MISMATCH",
    "PLACEHOLDER": "FORMATTING_MISMATCH",
    "OCR_NOISE": "FORMATTING_MISMATCH",
    "OTHER": "TRANSLATION_MISMATCH",
}


@dataclass(frozen=True)
class ReviewContext:
    en_item: dict
    target_item: dict | None
    evidence_base: dict
    language: str


def _issue_id(category: str, en_item_id: str, target_url: str, message: str) -> str:
    raw = f"{category}|{en_item_id}|{target_url}|{message}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _item_classes(item: dict) -> set[str]:
    attributes = item.get("attributes") if isinstance(item, dict) else None
    if not isinstance(attributes, dict):
        return set()
    class_value = str(attributes.get("class", "")).strip()
    if not class_value:
        return set()
    return {token for token in class_value.split() if token}


def _is_header_online_dynamic_counter(en_item: dict, target_item: dict) -> bool:
    classes = _item_classes(en_item) | _item_classes(target_item)
    return _HEADER_ONLINE_CLASS_TOKENS.issubset(classes)


def _normalize_dynamic_counter_text(en_item: dict, target_item: dict, text: str) -> str:
    if _is_header_online_dynamic_counter(en_item, target_item):
        return _DYNAMIC_NUMBER_RE.sub("<NUM>", text)
    return text


def _is_image_item(item: dict) -> bool:
    tag = str(item.get("tag", "")).strip().lower()
    element_type = str(item.get("element_type", "")).strip().lower()
    return tag in _IMAGE_TAGS or element_type in _IMAGE_TAGS


def _extract_ocr_text(item: dict) -> str:
    for key in ("ocr_text", "ocr", "text_ocr", "ocr_value"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _build_evidence(evidence_base: dict, en_text: str, target_text: str, review_class: str, reason: str, signals: dict, pairing_basis: str, ocr_text: str = "", ocr_engine: str = "", provider_notes: list[str] | None = None) -> dict:
    evidence = {
        **evidence_base,
        "text_en": en_text,
        "text_target": target_text,
        "review_class": review_class,
        "reason": reason,
        "signals": signals,
        "pairing_basis": pairing_basis,
    }
    if ocr_text:
        evidence["ocr_text"] = ocr_text
        evidence["ocr_engine"] = ocr_engine
    if provider_notes:
        evidence["provider_notes"] = provider_notes
    return evidence


def _assemble_issue(category: str, confidence: float, message: str, evidence: dict, en_item_id: str, target_url: str) -> dict:
    return {
        "id": _issue_id(category, en_item_id, target_url, message),
        "category": category,
        "confidence": confidence,
        "message": message,
        "evidence": evidence,
    }


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, round(v, 4)))


def _confidence(base: float, signals: dict[str, float]) -> float:
    return _clamp(base + sum(signals.values()))


def review_pair(context: ReviewContext, provider: Phase6ReviewProvider) -> list[dict]:
    en_item = context.en_item
    target_item = context.target_item

    is_dynamic_counter = _is_header_online_dynamic_counter(en_item, target_item or {})
    en_text = _normalize_dynamic_counter_text(en_item, target_item or {}, normalize_text(en_item.get("text", "")))

    if not target_item:
        signals = {"missing_target": 0.15}
        reason = "No paired target item for EN reference"
        evidence = _build_evidence(
            context.evidence_base,
            en_text=en_text,
            target_text="",
            review_class="OTHER",
            reason=reason,
            signals=signals,
            pairing_basis="item_id",
        )
        message = "Missing target element for EN reference item"
        return [
            _assemble_issue(
                category="MISSING_TRANSLATION",
                confidence=_confidence(0.8, signals),
                message=message,
                evidence=evidence,
                en_item_id=en_item.get("item_id", ""),
                target_url=en_item.get("url", ""),
            )
        ]

    target_text = _normalize_dynamic_counter_text(en_item, target_item, normalize_text(target_item.get("text", "")))
    en_placeholders = sorted(_PLACEHOLDER_RE.findall(en_text))
    target_placeholders = sorted(_PLACEHOLDER_RE.findall(target_text))

    issues: list[dict] = []
    item_id = str(en_item.get("item_id", ""))
    target_url = str(target_item.get("url", ""))

    is_image = _is_image_item(target_item) or _is_image_item(en_item)
    ocr_text = _extract_ocr_text(target_item) if is_image else ""
    ocr_engine = "OCR.Space:engine3" if ocr_text else ""

    if en_placeholders != target_placeholders:
        signals = {
            "placeholder_count_delta": float(abs(len(en_placeholders) - len(target_placeholders))) * 0.08,
            "placeholder_set_mismatch": 0.12,
        }
        reason = "Placeholder tokens differ between source and target"
        evidence = _build_evidence(
            context.evidence_base,
            en_text=en_text,
            target_text=target_text,
            review_class="PLACEHOLDER",
            reason=reason,
            signals=signals,
            pairing_basis="item_id",
            ocr_text=ocr_text,
            ocr_engine=ocr_engine,
        )
        msg = "Placeholder tokens differ between EN and target text"
        issues.append(
            _assemble_issue(
                category=REVIEW_TO_CATEGORY["PLACEHOLDER"],
                confidence=_confidence(0.7, signals),
                message=msg,
                evidence=evidence,
                en_item_id=item_id,
                target_url=target_url,
            )
        )

    if en_text and target_text and en_text == target_text and not en_placeholders and not is_dynamic_counter:
        signals = {"identical_text": 0.2, "untranslated_indicator": 0.1}
        reason = "Source and target text are identical after deterministic normalization"
        evidence = _build_evidence(
            context.evidence_base,
            en_text=en_text,
            target_text=target_text,
            review_class="MEANING",
            reason=reason,
            signals=signals,
            pairing_basis="item_id",
            ocr_text=ocr_text,
            ocr_engine=ocr_engine,
        )
        msg = "Target text appears untranslated (identical to EN)"
        issues.append(
            _assemble_issue(
                category=REVIEW_TO_CATEGORY["MEANING"],
                confidence=_confidence(0.4, signals),
                message=msg,
                evidence=evidence,
                en_item_id=item_id,
                target_url=target_url,
            )
        )

    spelling_grammar = provider.review_spelling_grammar(en_text, target_text, context.language)
    if spelling_grammar.spelling_score >= 0.8:
        signals = {"spelling_score": spelling_grammar.spelling_score}
        reason = "Deterministic provider suggests potential spelling issue"
        evidence = _build_evidence(
            context.evidence_base,
            en_text=en_text,
            target_text=target_text,
            review_class="SPELLING",
            reason=reason,
            signals=signals,
            provider_notes=spelling_grammar.notes,
            pairing_basis="item_id",
            ocr_text=ocr_text,
            ocr_engine=ocr_engine,
        )
        issues.append(
            _assemble_issue(
                category=REVIEW_TO_CATEGORY["SPELLING"],
                confidence=_confidence(0.35, signals),
                message="Potential spelling issue in target text",
                evidence=evidence,
                en_item_id=item_id,
                target_url=target_url,
            )
        )
    if spelling_grammar.grammar_score >= 0.75:
        signals = {"grammar_score": spelling_grammar.grammar_score}
        reason = "Deterministic provider suggests potential grammar issue"
        evidence = _build_evidence(
            context.evidence_base,
            en_text=en_text,
            target_text=target_text,
            review_class="GRAMMAR",
            reason=reason,
            signals=signals,
            provider_notes=spelling_grammar.notes,
            pairing_basis="item_id",
            ocr_text=ocr_text,
            ocr_engine=ocr_engine,
        )
        issues.append(
            _assemble_issue(
                category=REVIEW_TO_CATEGORY["GRAMMAR"],
                confidence=_confidence(0.35, signals),
                message="Potential grammar issue in target text",
                evidence=evidence,
                en_item_id=item_id,
                target_url=target_url,
            )
        )

    meaning = provider.review_meaning(en_text, target_text, context.language)
    if meaning.meaning_mismatch_score >= 0.7 and not (en_text == target_text):
        signals = {"meaning_mismatch_score": meaning.meaning_mismatch_score}
        reason = "Deterministic provider suggests potential meaning drift"
        evidence = _build_evidence(
            context.evidence_base,
            en_text=en_text,
            target_text=target_text,
            review_class="MEANING",
            reason=reason,
            signals=signals,
            provider_notes=meaning.notes,
            pairing_basis="item_id",
            ocr_text=ocr_text,
            ocr_engine=ocr_engine,
        )
        issues.append(
            _assemble_issue(
                category=REVIEW_TO_CATEGORY["MEANING"],
                confidence=_confidence(0.3, signals),
                message="Potential meaning mismatch between EN and target text",
                evidence=evidence,
                en_item_id=item_id,
                target_url=target_url,
            )
        )

    if is_image and ocr_text and len(ocr_text) <= 2:
        signals = {"ocr_text_too_short": 0.2, "ocr_ambiguity": 0.15}
        reason = "OCR result is too short for reliable comparison"
        evidence = _build_evidence(
            context.evidence_base,
            en_text=en_text,
            target_text=target_text,
            review_class="OCR_NOISE",
            reason=reason,
            signals=signals,
            pairing_basis="item_id",
            ocr_text=ocr_text,
            ocr_engine=ocr_engine,
        )
        issues.append(
            _assemble_issue(
                category=REVIEW_TO_CATEGORY["OCR_NOISE"],
                confidence=_confidence(0.45, signals),
                message="OCR output appears noisy for image-based item",
                evidence=evidence,
                en_item_id=item_id,
                target_url=target_url,
            )
        )

    return issues


def overlay_blocked_issue(capture_context_id: str, blocked: dict) -> dict:
    reason = "Capture review marked this page as blocked by overlay"
    evidence = {
        "url": blocked["url"],
        "bbox": {"x": 0, "y": 0, "width": 0, "height": 0},
        "storage_uri": blocked["storage_uri"],
        "review_class": "OTHER",
        "reason": reason,
        "signals": {"overlay_blocked": True},
        "pairing_basis": "capture_context",
    }
    message = "Capture blocked by overlay"
    return _assemble_issue(
        category="OVERLAY_BLOCKED_CAPTURE",
        confidence=1.0,
        message=message,
        evidence=evidence,
        en_item_id=capture_context_id,
        target_url=blocked["url"],
    )
