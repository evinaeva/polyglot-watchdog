"""Phase 6 internal review pipeline.

Phase 6 intentionally uses two classification layers:

* `issue["category"]` is the stable persisted contract field used by downstream
  consumers and validated by `issues.schema.json`.
* `issue["evidence"]["review_class"]` is richer internal QA metadata used to
  explain why an issue was emitted.

Multiple review classes can map into one persisted category. Keep this mapping
coarse and backward-compatible unless the external `issues.json` contract is
explicitly revised.
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
_REPEATED_CHAR_RE = re.compile(r"(.)\1{3,}")
_NOISY_NOTE_HINTS = ("ambig", "uncertain", "low_conf", "failed", "no_text", "empty")

# Internal Phase 6 QA classes collapse into coarse persisted issue categories.
# Do not expose these review classes as replacements for top-level `category`.
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


@dataclass(frozen=True)
class PreparedReviewInputs:
    en_text: str
    target_text: str
    is_dynamic_counter: bool
    ocr_text: str
    ocr_engine: str
    ocr_quality: dict | None
    comparison_text_source: str


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


def _assess_ocr_quality(en_text: str, ocr_text: str, ocr_notes: list[str] | None) -> dict:
    text = (ocr_text or "").strip()
    normalized = re.sub(r"\s+", " ", text)
    notes = [str(note).strip().lower() for note in (ocr_notes or []) if str(note).strip()]

    signals: dict[str, float] = {}
    flags: list[str] = []
    penalty = 0.0

    if not normalized:
        flags.append("ocr_missing_text")
        signals["ocr_missing_text"] = 1.0
        penalty += 0.65
    else:
        alnum_count = sum(1 for ch in normalized if ch.isalnum())
        non_space_count = sum(1 for ch in normalized if not ch.isspace())
        symbol_ratio = (non_space_count - alnum_count) / max(non_space_count, 1)
        alnum_ratio = alnum_count / max(non_space_count, 1)
        ocr_len = len(normalized)
        en_len = len(en_text.strip())
        length_ratio = ocr_len / max(en_len, 1)
        tokens = [token for token in normalized.split(" ") if token]
        short_token_ratio = (sum(1 for token in tokens if len(token) <= 1) / len(tokens)) if tokens else 1.0

        signals["ocr_symbol_ratio"] = round(symbol_ratio, 4)
        signals["ocr_alnum_ratio"] = round(alnum_ratio, 4)
        signals["ocr_length_ratio_vs_en"] = round(length_ratio, 4)

        if ocr_len <= 2:
            flags.append("ocr_too_short_absolute")
            penalty += 0.5
        if length_ratio < 0.15:
            flags.append("ocr_too_short_vs_source")
            penalty += 0.25
        if symbol_ratio > 0.45:
            flags.append("ocr_symbol_heavy")
            penalty += 0.2
        if alnum_ratio < 0.35:
            flags.append("ocr_low_alnum")
            penalty += 0.2
        if short_token_ratio > 0.6:
            flags.append("ocr_fragmented_tokens")
            penalty += 0.15
        if _REPEATED_CHAR_RE.search(normalized.lower()):
            flags.append("ocr_repeated_chars")
            penalty += 0.15

    if notes and any(any(hint in note for hint in _NOISY_NOTE_HINTS) for note in notes):
        flags.append("ocr_provider_uncertainty")
        signals["ocr_provider_uncertainty"] = 1.0
        penalty += 0.2

    trust_score = _clamp(1.0 - penalty)
    if trust_score <= 0.35:
        trust_bucket = "weak"
        confidence_adjustment = -0.25
    elif trust_score < 0.65:
        trust_bucket = "borderline"
        confidence_adjustment = -0.1
    else:
        trust_bucket = "good"
        confidence_adjustment = 0.0

    return {
        "trust_score": trust_score,
        "trust_bucket": trust_bucket,
        "confidence_adjustment": confidence_adjustment,
        "suppress_meaning_claims": trust_bucket == "weak",
        "flags": flags,
        "signals": signals,
    }


def _build_evidence(evidence_base: dict, en_text: str, target_text: str, review_class: str, reason: str, signals: dict, pairing_basis: str, ocr_text: str = "", ocr_engine: str = "", provider_notes: list[str] | None = None, provider_meta: dict | None = None) -> dict:
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
    if provider_meta:
        evidence["provider_meta"] = provider_meta
        review_mode = str(provider_meta.get("review_mode", "")).strip()
        if review_mode:
            evidence["review_mode"] = review_mode
        confidence_provenance = str(provider_meta.get("confidence_provenance", "")).strip()
        if confidence_provenance:
            evidence["confidence_provenance"] = confidence_provenance
    return evidence


def _select_target_comparison_text(
    en_item: dict,
    target_item: dict,
    dom_target_text: str,
    ocr_text: str,
    ocr_quality: dict | None,
) -> tuple[str, str]:
    normalized_ocr_text = _normalize_dynamic_counter_text(en_item, target_item, normalize_text(ocr_text))
    if ocr_quality and ocr_quality.get("trust_bucket") == "good" and normalized_ocr_text:
        return normalized_ocr_text, "ocr"
    return dom_target_text, "dom"


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


def prepare_review_inputs(en_item: dict, target_item: dict | None) -> PreparedReviewInputs:
    is_dynamic_counter = _is_header_online_dynamic_counter(en_item, target_item or {})
    en_text = _normalize_dynamic_counter_text(en_item, target_item or {}, normalize_text(en_item.get("text", "")))
    if not target_item:
        return PreparedReviewInputs(
            en_text=en_text,
            target_text="",
            is_dynamic_counter=is_dynamic_counter,
            ocr_text="",
            ocr_engine="",
            ocr_quality=None,
            comparison_text_source="dom",
        )

    dom_target_text = _normalize_dynamic_counter_text(en_item, target_item, normalize_text(target_item.get("text", "")))
    is_image = _is_image_item(target_item) or _is_image_item(en_item)
    ocr_text = _extract_ocr_text(target_item) if is_image else ""
    ocr_engine = str(target_item.get("ocr_engine", "")).strip() if is_image else ""
    if is_image and ocr_text and not ocr_engine:
        ocr_engine = "OCR.Space:engine3"
    ocr_notes = list(target_item.get("ocr_notes", [])) if is_image and isinstance(target_item.get("ocr_notes"), list) else []
    has_ocr_handoff = is_image and any(key in target_item for key in ("ocr_text", "ocr_notes", "ocr_engine"))
    ocr_quality = _assess_ocr_quality(en_text, ocr_text, ocr_notes) if has_ocr_handoff else None
    target_text, comparison_text_source = _select_target_comparison_text(
        en_item=en_item,
        target_item=target_item,
        dom_target_text=dom_target_text,
        ocr_text=ocr_text,
        ocr_quality=ocr_quality if is_image else None,
    )
    return PreparedReviewInputs(
        en_text=en_text,
        target_text=target_text,
        is_dynamic_counter=is_dynamic_counter,
        ocr_text=ocr_text,
        ocr_engine=ocr_engine,
        ocr_quality=ocr_quality,
        comparison_text_source=comparison_text_source,
    )


def review_pair(context: ReviewContext, provider: Phase6ReviewProvider) -> list[dict]:
    en_item = context.en_item
    target_item = context.target_item

    prepared = prepare_review_inputs(en_item, target_item)
    is_dynamic_counter = prepared.is_dynamic_counter
    en_text = prepared.en_text
    pairing_basis = str(context.evidence_base.get("pairing_basis", "item_id"))

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
            pairing_basis=pairing_basis,
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

    issues: list[dict] = []
    item_id = str(en_item.get("item_id", ""))
    target_url = str(target_item.get("url", ""))

    # OCR evidence is limited to approved image-backed items only. For these
    # items, Phase 6 prefers OCR as canonical comparison input only when OCR
    # quality is usable; otherwise it falls back to normalized DOM text.
    ocr_text = prepared.ocr_text
    ocr_engine = prepared.ocr_engine
    ocr_quality = prepared.ocr_quality
    target_text = prepared.target_text
    comparison_text_source = prepared.comparison_text_source

    en_placeholders = sorted(_PLACEHOLDER_RE.findall(en_text))
    target_placeholders = sorted(_PLACEHOLDER_RE.findall(target_text))

    def with_ocr_signals(base_signals: dict[str, float], include_quality_metrics: bool = False) -> dict[str, float]:
        if not ocr_quality:
            return dict(base_signals)
        merged = dict(base_signals)
        merged["ocr_confidence_adjustment"] = ocr_quality["confidence_adjustment"]
        if include_quality_metrics:
            for key, value in ocr_quality["signals"].items():
                merged[key] = value
        return merged

    if en_placeholders != target_placeholders:
        signals = with_ocr_signals({
            "placeholder_count_delta": float(abs(len(en_placeholders) - len(target_placeholders))) * 0.08,
            "placeholder_set_mismatch": 0.12,
        })
        reason = "Placeholder tokens differ between source and target"
        evidence = _build_evidence(
            context.evidence_base,
            en_text=en_text,
            target_text=target_text,
            review_class="PLACEHOLDER",
            reason=reason,
            signals=signals,
            pairing_basis=pairing_basis,
            ocr_text=ocr_text,
            ocr_engine=ocr_engine,
        )
        evidence["comparison_text_source"] = comparison_text_source
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
        signals = with_ocr_signals({"identical_text": 0.2, "untranslated_indicator": 0.1})
        reason = "Source and target text are identical after deterministic normalization"
        evidence = _build_evidence(
            context.evidence_base,
            en_text=en_text,
            target_text=target_text,
            review_class="MEANING",
            reason=reason,
            signals=signals,
            pairing_basis=pairing_basis,
            ocr_text=ocr_text,
            ocr_engine=ocr_engine,
        )
        evidence["comparison_text_source"] = comparison_text_source
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

    llm_kind_code = int(context.evidence_base.get("llm_kind_code", 1) or 1)
    llm_context_code = int(context.evidence_base.get("llm_context_code", 3) or 3)
    llm_masked_flag = int(context.evidence_base.get("llm_masked_flag", 0) or 0)
    llm_low_pairing_confidence_flag = int(context.evidence_base.get("llm_low_pairing_confidence_flag", 0) or 0)
    spelling_grammar = provider.review_spelling_grammar(
        en_text,
        target_text,
        context.language,
        kind_code=llm_kind_code,
        context_code=llm_context_code,
        masked_flag=llm_masked_flag,
        low_pairing_confidence_flag=llm_low_pairing_confidence_flag,
    )
    if spelling_grammar.spelling_score >= 0.8:
        signals = with_ocr_signals({"spelling_score": spelling_grammar.spelling_score})
        reason = "Provider suggests potential spelling issue"
        evidence = _build_evidence(
            context.evidence_base,
            en_text=en_text,
            target_text=target_text,
            review_class="SPELLING",
            reason=reason,
            signals=signals,
            provider_notes=spelling_grammar.notes,
            provider_meta=spelling_grammar.provider_meta,
            pairing_basis=pairing_basis,
            ocr_text=ocr_text,
            ocr_engine=ocr_engine,
        )
        evidence["comparison_text_source"] = comparison_text_source
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
        signals = with_ocr_signals({"grammar_score": spelling_grammar.grammar_score})
        reason = "Provider suggests potential grammar issue"
        evidence = _build_evidence(
            context.evidence_base,
            en_text=en_text,
            target_text=target_text,
            review_class="GRAMMAR",
            reason=reason,
            signals=signals,
            provider_notes=spelling_grammar.notes,
            provider_meta=spelling_grammar.provider_meta,
            pairing_basis=pairing_basis,
            ocr_text=ocr_text,
            ocr_engine=ocr_engine,
        )
        evidence["comparison_text_source"] = comparison_text_source
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

    meaning = provider.review_meaning(
        en_text,
        target_text,
        context.language,
        kind_code=llm_kind_code,
        context_code=llm_context_code,
        masked_flag=llm_masked_flag,
        low_pairing_confidence_flag=llm_low_pairing_confidence_flag,
    )
    if meaning.meaning_mismatch_score >= 0.7 and not (en_text == target_text) and not (ocr_quality and ocr_quality["suppress_meaning_claims"]):
        signals = with_ocr_signals({"meaning_mismatch_score": meaning.meaning_mismatch_score})
        reason = "Provider suggests potential meaning drift"
        evidence = _build_evidence(
            context.evidence_base,
            en_text=en_text,
            target_text=target_text,
            review_class="MEANING",
            reason=reason,
            signals=signals,
            provider_notes=meaning.notes,
            provider_meta=meaning.provider_meta,
            pairing_basis=pairing_basis,
            ocr_text=ocr_text,
            ocr_engine=ocr_engine,
        )
        evidence["comparison_text_source"] = comparison_text_source
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

    if ocr_quality and (ocr_quality["trust_bucket"] in {"weak", "borderline"}):
        signals = with_ocr_signals({"ocr_ambiguity": 0.15 if ocr_quality["trust_bucket"] == "weak" else 0.08}, include_quality_metrics=True)
        if ocr_quality["flags"]:
            signals["ocr_noise_flags"] = float(len(ocr_quality["flags"])) * 0.04
        reason = f"OCR quality is {ocr_quality['trust_bucket']} for reliable translation comparison"
        evidence = _build_evidence(
            context.evidence_base,
            en_text=en_text,
            target_text=target_text,
            review_class="OCR_NOISE",
            reason=reason,
            signals=signals,
            pairing_basis=pairing_basis,
            ocr_text=ocr_text,
            ocr_engine=ocr_engine,
            provider_notes=[f"ocr_quality_flags:{','.join(ocr_quality['flags'])}"] if ocr_quality["flags"] else None,
        )
        evidence["comparison_text_source"] = comparison_text_source
        evidence["ocr_quality"] = {
            "trust_bucket": ocr_quality["trust_bucket"],
            "trust_score": ocr_quality["trust_score"],
            "flags": ocr_quality["flags"],
        }
        issues.append(
            _assemble_issue(
                category=REVIEW_TO_CATEGORY["OCR_NOISE"],
                confidence=_confidence(0.4, signals),
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
