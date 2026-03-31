"""Phase 6 provider interfaces for optional AI-assisted translation checks.

Default providers are deterministic and offline-safe.
"""

from __future__ import annotations

import json
import os
import re
import warnings
from math import ceil
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol
from urllib.error import URLError
from urllib.request import Request, urlopen


def _empty_llm_review_stats(
    *,
    review_mode: str,
    provider_type: str,
    configured_provider: str,
    configured_model: str,
    effective_model: str,
) -> dict[str, Any]:
    return {
        "review_mode": review_mode,
        "provider_type": provider_type,
        "configured_provider": configured_provider,
        "configured_model": configured_model,
        "effective_model": effective_model,
        "llm_requested": False,
        "llm_batches_attempted": 0,
        "llm_batches_succeeded": 0,
        "llm_batches_failed": 0,
        "fallback_batches": 0,
        "fallback_items": 0,
        "llm_items_requested": 0,
        "llm_items_completed": 0,
        "estimated_prompt_tokens": 0,
        "estimated_completion_tokens": 0,
        "estimated_total_tokens": 0,
        "actual_prompt_tokens": None,
        "actual_completion_tokens": None,
        "actual_total_tokens": None,
        "estimated_cost_usd": None,
        "actual_cost_usd": None,
        "currency": "USD",
        "responses_received": 0,
        "transport_failures": 0,
        "parse_failures": 0,
        "provider_failures": 0,
        "used_fallback": False,
        "fallback_reason_summary": [],
        "batches": [],
    }


@dataclass(frozen=True)
class SpellingGrammarSignals:
    spelling_score: float
    grammar_score: float
    notes: list[str]
    provider_meta: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MeaningSignals:
    meaning_mismatch_score: float
    notes: list[str]
    provider_meta: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class _PairReviewResult:
    spelling_score: float
    grammar_score: float
    meaning_mismatch_score: float
    notes: list[str]
    provider_meta: dict[str, Any] = field(default_factory=dict)


class Phase6ReviewProvider(Protocol):
    def review_spelling_grammar(
        self,
        text_en: str,
        text_target: str,
        language: str,
        *,
        kind_code: int = 1,
        context_code: int = 3,
        masked_flag: int = 0,
        low_pairing_confidence_flag: int = 0,
    ) -> SpellingGrammarSignals:
        ...

    def review_meaning(
        self,
        text_en: str,
        text_target: str,
        language: str,
        *,
        kind_code: int = 1,
        context_code: int = 3,
        masked_flag: int = 0,
        low_pairing_confidence_flag: int = 0,
    ) -> MeaningSignals:
        ...


class DeterministicOfflineProvider:
    """Heuristic-only provider with deterministic outputs and no network calls."""

    _SPELLING_MARKERS = ("teh", "recieve", "definately")
    _PROVIDER_META = {
        "provider": "deterministic-offline",
        "review_mode": "test-heuristic",
        "confidence_provenance": "heuristic",
        "origin": "deterministic_offline",
        "fallback_used": False,
    }

    def review_spelling_grammar(
        self, text_en: str, text_target: str, language: str, **_: Any
    ) -> SpellingGrammarSignals:
        target_lc = text_target.lower()
        notes: list[str] = []

        spelling_score = 0.0
        grammar_score = 0.0

        if any(marker in target_lc for marker in self._SPELLING_MARKERS):
            spelling_score = 0.86
            notes.append("spelling_marker_detected")

        if "??" in text_target or "!!" in text_target:
            grammar_score = 0.78
            notes.append("punctuation_instability")

        return SpellingGrammarSignals(
            spelling_score=spelling_score,
            grammar_score=grammar_score,
            notes=notes,
            provider_meta=dict(self._PROVIDER_META),
        )

    def review_meaning(self, text_en: str, text_target: str, language: str, **_: Any) -> MeaningSignals:
        notes: list[str] = []
        score = 0.0

        if text_en and text_target and len(text_target) < max(3, len(text_en) // 4):
            score = 0.65
            notes.append("target_much_shorter_than_source")

        if text_en and text_target and text_en.lower() == text_target.lower():
            score = max(score, 0.8)
            notes.append("identical_text_signal")

        return MeaningSignals(
            meaning_mismatch_score=score,
            notes=notes,
            provider_meta=dict(self._PROVIDER_META),
        )

    def get_llm_review_stats(self) -> dict[str, Any]:
        return _empty_llm_review_stats(
            review_mode="test-heuristic",
            provider_type="heuristic",
            configured_provider="test-heuristic",
            configured_model="",
            effective_model="",
        )


class DisabledReviewProvider:
    """Provider that emits no AI-assisted signals."""

    def review_spelling_grammar(
        self, text_en: str, text_target: str, language: str, **_: Any
    ) -> SpellingGrammarSignals:
        return SpellingGrammarSignals(spelling_score=0.0, grammar_score=0.0, notes=["provider_disabled"])

    def review_meaning(self, text_en: str, text_target: str, language: str, **_: Any) -> MeaningSignals:
        return MeaningSignals(meaning_mismatch_score=0.0, notes=["provider_disabled"])

    def get_llm_review_stats(self) -> dict[str, Any]:
        return _empty_llm_review_stats(
            review_mode="disabled",
            provider_type="disabled",
            configured_provider="disabled",
            configured_model="",
            effective_model="",
        )


class LLMReviewProvider:
    """JSON-only LLM review provider with deterministic offline fallback."""

    _DEFAULT_SYSTEM_PROMPT_BASE = "You are a concise localization QA reviewer."
    _SYSTEM_PROMPT_CONTRACT_SUFFIX = (
        "Localization QA for EN -> target. Domain: legal adult webcam site. Adult terminology alone is not an error. "
        "Judge linguistic quality and meaning only; no literal translation required; short UI labels may have multiple valid translations. "
        "Unchanged brand names, URLs, acronyms, and copyright strings can be valid. If m=1 (masked) be conservative. "
        "If p=1 (low pairing confidence) be conservative unless error is obvious. For k=3 or c=4, judge localized alt text only, not image content. "
        'Input JSON: {"l":"<target_language>","i":[[id,en,tg,k,c,m,p]]}. '
        "k codes: 0=a,1=p,2=h1,3=img,4=short_text. c codes: 0=nav,1=footer,2=title,3=body,4=img_alt,5=brand,6=lang_switcher,7=cta. "
        'Output JSON only: {"r":[[id,s,g,m,n]]}. '
        "s/g/m are integer 0..100 risk scores. Bands: 0..15 no meaningful issue, 20..45 weak suspicion/minor issue, 50..69 likely issue, 70..100 clear issue. "
        "n primary note code: 0 ok, 1 spell, 2 grammar, 3 meaning, 4 untranslated, 5 partial, 6 brand_ok, 7 same_ok, 8 masked_ok, 9 adult_ok, 10 uncertain."
    )
    _NOTE_CODE_TO_LABEL = {
        0: "ok",
        1: "spell",
        2: "grammar",
        3: "meaning",
        4: "untranslated",
        5: "partial",
        6: "brand_ok",
        7: "same_ok",
        8: "masked_ok",
        9: "adult_ok",
        10: "uncertain",
    }
    _MASK_HINT_RE = re.compile(r"(\*{2,}|%[^%]+%|\[[^\]]+\]|<[^>]+>)")

    def __init__(
        self,
        api_key: str | None,
        model: str = "openrouter/free",
        timeout_s: float = 8.0,
        endpoint: str = "https://openrouter.ai/api/v1/chat/completions",
        system_prompt: str | None = None,
        hard_context_tokens: int = 150000,
        token_reserve_ratio: float = 0.20,
        fixed_token_margin: int = 1024,
        estimated_output_tokens_per_item: int = 64,
        fallback_provider: Phase6ReviewProvider | None = None,
        request_fn: Callable[[str, str, float, dict[str, Any]], dict[str, Any]] | None = None,
        artifact_writer: Callable[[str, Any], None] | None = None,
    ) -> None:
        self._api_key = (api_key or "").strip()
        self._model = model
        self._timeout_s = timeout_s
        self._endpoint = endpoint
        self._system_prompt = self._build_system_prompt(system_prompt)
        self._hard_context_tokens = max(1024, int(hard_context_tokens))
        self._token_reserve_ratio = max(0.05, min(0.50, float(token_reserve_ratio)))
        self._fixed_token_margin = max(128, int(fixed_token_margin))
        self._estimated_output_tokens_per_item = max(16, int(estimated_output_tokens_per_item))
        self._fallback = fallback_provider or DeterministicOfflineProvider()
        self._request_fn = request_fn or self._default_request
        self._artifact_writer = artifact_writer
        self._pair_reviews: dict[tuple[str, str, str, int, int, int, int], _PairReviewResult] = {}
        self._batch_stats: list[dict[str, Any]] = []
        self._input_cost_per_1m = self._read_cost_env("PHASE6_REVIEW_INPUT_COST_PER_1M_TOKENS")
        self._output_cost_per_1m = self._read_cost_env("PHASE6_REVIEW_OUTPUT_COST_PER_1M_TOKENS")
        self._actual_prompt_token_sum = 0
        self._actual_completion_token_sum = 0
        self._actual_total_token_sum = 0
        self._has_actual_usage = False

    @staticmethod
    def _read_cost_env(env_key: str) -> float | None:
        raw = os.environ.get(env_key)
        if raw is None:
            return None
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None

    def prefetch_reviews(self, pairs: list[tuple[str, str] | dict[str, Any]], language: str) -> None:
        unresolved_items: list[dict[str, Any]] = []
        for idx, pair in enumerate(pairs):
            if isinstance(pair, dict):
                text_en = str(pair.get("text_en", ""))
                text_target = str(pair.get("text_target", ""))
                kind_code = int(pair.get("kind_code", 1))
                context_code = int(pair.get("context_code", 3))
                masked_flag = int(pair.get("masked_flag", 1 if self._MASK_HINT_RE.search(text_target) else 0))
                low_pairing_confidence_flag = int(pair.get("low_pairing_confidence_flag", 0))
            else:
                text_en, text_target = pair
                kind_code = 1
                context_code = 3
                masked_flag = 1 if self._MASK_HINT_RE.search(text_target) else 0
                low_pairing_confidence_flag = 0
            cache_key = self._pair_cache_key(
                language=language,
                text_en=text_en,
                text_target=text_target,
                kind_code=kind_code,
                context_code=context_code,
                masked_flag=masked_flag,
                low_pairing_confidence_flag=low_pairing_confidence_flag,
            )
            if cache_key in self._pair_reviews:
                continue
            unresolved_items.append(
                {
                    "item_id": f"item_{idx}",
                    "wire_id": idx,
                    "text_en": text_en,
                    "text_target": text_target,
                    "kind_code": max(0, min(4, kind_code)),
                    "context_code": max(0, min(7, context_code)),
                    "masked_flag": 1 if masked_flag else 0,
                    "low_pairing_confidence_flag": 1 if low_pairing_confidence_flag else 0,
                    "cache_key": cache_key,
                }
            )
        if not unresolved_items:
            return
        for batch in self._split_batches(language=language, items=unresolved_items):
            self._execute_batch(language=language, items=batch)

    def review_spelling_grammar(
        self,
        text_en: str,
        text_target: str,
        language: str,
        *,
        kind_code: int = 1,
        context_code: int = 3,
        masked_flag: int = 0,
        low_pairing_confidence_flag: int = 0,
    ) -> SpellingGrammarSignals:
        pair_review = self._get_pair_review(
            text_en=text_en,
            text_target=text_target,
            language=language,
            kind_code=kind_code,
            context_code=context_code,
            masked_flag=masked_flag,
            low_pairing_confidence_flag=low_pairing_confidence_flag,
        )

        return SpellingGrammarSignals(
            spelling_score=pair_review.spelling_score,
            grammar_score=pair_review.grammar_score,
            notes=pair_review.notes,
            provider_meta=pair_review.provider_meta,
        )

    def review_meaning(
        self,
        text_en: str,
        text_target: str,
        language: str,
        *,
        kind_code: int = 1,
        context_code: int = 3,
        masked_flag: int = 0,
        low_pairing_confidence_flag: int = 0,
    ) -> MeaningSignals:
        pair_review = self._get_pair_review(
            text_en=text_en,
            text_target=text_target,
            language=language,
            kind_code=kind_code,
            context_code=context_code,
            masked_flag=masked_flag,
            low_pairing_confidence_flag=low_pairing_confidence_flag,
        )

        return MeaningSignals(
            meaning_mismatch_score=pair_review.meaning_mismatch_score,
            notes=pair_review.notes,
            provider_meta=pair_review.provider_meta,
        )

    def _get_pair_review(
        self,
        text_en: str,
        text_target: str,
        language: str,
        *,
        kind_code: int,
        context_code: int,
        masked_flag: int,
        low_pairing_confidence_flag: int,
    ) -> _PairReviewResult:
        cache_key = self._pair_cache_key(
            language=language,
            text_en=text_en,
            text_target=text_target,
            kind_code=kind_code,
            context_code=context_code,
            masked_flag=masked_flag,
            low_pairing_confidence_flag=low_pairing_confidence_flag,
        )
        cached = self._pair_reviews.get(cache_key)
        if cached is not None:
            return cached

        self.prefetch_reviews(
            [{
                "text_en": text_en,
                "text_target": text_target,
                "kind_code": kind_code,
                "context_code": context_code,
                "masked_flag": masked_flag,
                "low_pairing_confidence_flag": low_pairing_confidence_flag,
            }],
            language,
        )
        return self._pair_reviews.get(cache_key) or self._fallback_result(text_en, text_target, language)

    def _execute_batch(self, language: str, items: list[dict[str, Any]]) -> None:
        parsed_by_item_id, batch_stats = self._review_batch(language=language, items=items, batch_index=len(self._batch_stats) + 1)
        for item in items:
            cache_key = item["cache_key"]
            text_en = item["text_en"]
            text_target = item["text_target"]
            item_id = item["item_id"]
            parsed = parsed_by_item_id.get(item_id)
            result = (
                self._llm_result(parsed)
                if parsed is not None
                else self._fallback_result(text_en=text_en, text_target=text_target, language=language)
            )
            self._pair_reviews[cache_key] = result
        completed = len(parsed_by_item_id)
        fallback_items = max(0, len(items) - completed)
        batch_stats["llm_items_completed"] = completed
        batch_stats["fallback_items"] = fallback_items
        batch_stats["fallback_used"] = fallback_items > 0
        if batch_stats["status"] not in {"not_attempted", "failed"}:
            batch_stats["status"] = "succeeded" if fallback_items == 0 else "fallback"
        if fallback_items > 0:
            batch_stats["failure_type"] = batch_stats["failure_type"] or "fallback"
            batch_stats["failure_message"] = batch_stats["failure_message"] or f"{fallback_items} item(s) used fallback"
        self._batch_stats.append(batch_stats)

    def _review_batch(self, language: str, items: list[dict[str, Any]], batch_index: int) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
        deduped_rows, _ = self._dedupe_rows(language=language, items=items)
        estimated_prompt_tokens = self._estimate_prompt_tokens() + sum(self._estimate_item_prompt_tokens(language, item) for item in deduped_rows)
        estimated_completion_tokens = len(deduped_rows) * self._estimated_output_tokens_per_item
        estimated_total_tokens = estimated_prompt_tokens + estimated_completion_tokens
        batch_stats = {
            "batch_index": batch_index,
            "items": len(items),
            "estimated_prompt_tokens": estimated_prompt_tokens,
            "estimated_completion_tokens": estimated_completion_tokens,
            "estimated_total_tokens": estimated_total_tokens,
            "actual_prompt_tokens": None,
            "actual_completion_tokens": None,
            "actual_total_tokens": None,
            "estimated_cost_usd": self._compute_cost(estimated_prompt_tokens, estimated_completion_tokens),
            "actual_cost_usd": None,
            "provider": "llm",
            "model": self._model,
            "status": "attempted",
            "fallback_used": False,
            "failure_type": None,
            "failure_message": None,
            "response_received": False,
        }
        if not self._api_key:
            batch_stats["status"] = "not_attempted"
            batch_stats["failure_type"] = "provider"
            batch_stats["failure_message"] = "missing_api_key"
            return {}, batch_stats

        user_payload = self._compact_request_payload(language=language, items=items)
        payload = {
            "model": self._model,
            "response_format": {"type": "json_object"},
            "temperature": 0,
            "messages": [
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False, separators=(",", ":"))},
            ],
        }
        if self._artifact_writer is not None and batch_index == 1:
            self._artifact_writer("check_languages_llm_request.json", payload)

        try:
            response = self._request_fn(self._endpoint, self._api_key, self._timeout_s, payload)
            batch_stats["response_received"] = True
            content = response["choices"][0]["message"]["content"]
            if self._artifact_writer is not None and batch_index == 1:
                self._artifact_writer("check_languages_llm_raw_response.json", {"content": content})
            usage = response.get("usage", {}) if isinstance(response, dict) else {}
            prompt_tokens = self._safe_int((usage or {}).get("prompt_tokens"))
            completion_tokens = self._safe_int((usage or {}).get("completion_tokens"))
            total_tokens = self._safe_int((usage or {}).get("total_tokens"))
            if prompt_tokens is not None and completion_tokens is not None:
                if total_tokens is None:
                    total_tokens = prompt_tokens + completion_tokens
                batch_stats["actual_prompt_tokens"] = prompt_tokens
                batch_stats["actual_completion_tokens"] = completion_tokens
                batch_stats["actual_total_tokens"] = total_tokens
                batch_stats["actual_cost_usd"] = self._compute_cost(prompt_tokens, completion_tokens)
                self._actual_prompt_token_sum += prompt_tokens
                self._actual_completion_token_sum += completion_tokens
                self._actual_total_token_sum += total_tokens
                self._has_actual_usage = True
            parsed = json.loads(content)
        except URLError as exc:
            batch_stats["status"] = "failed"
            batch_stats["failure_type"] = "transport"
            batch_stats["failure_message"] = str(exc)
            return {}, batch_stats
        except (TimeoutError, OSError) as exc:
            batch_stats["status"] = "failed"
            batch_stats["failure_type"] = "transport"
            batch_stats["failure_message"] = str(exc)
            return {}, batch_stats
        except ValueError as exc:
            batch_stats["status"] = "failed"
            batch_stats["failure_type"] = "parse"
            batch_stats["failure_message"] = str(exc)
            return {}, batch_stats
        except (KeyError, IndexError, TypeError) as exc:
            batch_stats["status"] = "failed"
            batch_stats["failure_type"] = "provider"
            batch_stats["failure_message"] = str(exc)
            return {}, batch_stats
        deduped_rows, fanout = self._dedupe_rows(language=language, items=items)
        valid_by_wire_id = self._parse_batch_results(parsed, {int(item["wire_id"]) for item in deduped_rows})
        valid: dict[str, dict[str, Any]] = {}
        for wire_id, row in valid_by_wire_id.items():
            for item_id in fanout.get(wire_id, []):
                valid[item_id] = row
        if not valid:
            batch_stats["status"] = "failed"
            batch_stats["failure_type"] = "parse"
            batch_stats["failure_message"] = "empty_or_invalid_results"
        return valid, batch_stats

    def _dedupe_rows(self, language: str, items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[int, list[str]]]:
        deduped: list[dict[str, Any]] = []
        fanout: dict[int, list[str]] = {}
        seen: dict[tuple[str, str, str, int, int, int, int], int] = {}
        for item in items:
            wire_id = int(item["wire_id"])
            key = self._pair_cache_key(
                language=language,
                text_en=item["text_en"],
                text_target=item["text_target"],
                kind_code=item.get("kind_code", 1),
                context_code=item.get("context_code", 3),
                masked_flag=item.get("masked_flag", 0),
                low_pairing_confidence_flag=item.get("low_pairing_confidence_flag", 0),
            )
            existing_wire_id = seen.get(key)
            if existing_wire_id is None:
                seen[key] = wire_id
                deduped.append(item)
                fanout[wire_id] = [str(item["item_id"])]
            else:
                fanout.setdefault(existing_wire_id, []).append(str(item["item_id"]))
        return deduped, fanout

    def _compact_request_payload(self, language: str, items: list[dict[str, Any]]) -> dict[str, Any]:
        deduped_rows, _ = self._dedupe_rows(language=language, items=items)
        return {
            "l": language,
            "i": [
                [
                    int(item["wire_id"]),
                    item["text_en"],
                    item["text_target"],
                    int(item.get("kind_code", 1)),
                    int(item.get("context_code", 3)),
                    1 if item.get("masked_flag") else 0,
                    1 if item.get("low_pairing_confidence_flag") else 0,
                ]
                for item in deduped_rows
            ],
        }

    @staticmethod
    def _normalized_text(value: Any) -> str:
        return " ".join(str(value or "").strip().split()).casefold()

    @classmethod
    def _pair_cache_key(
        cls,
        *,
        language: str,
        text_en: Any,
        text_target: Any,
        kind_code: Any,
        context_code: Any,
        masked_flag: Any,
        low_pairing_confidence_flag: Any,
    ) -> tuple[str, str, str, int, int, int, int]:
        return (
            str(language or "").strip().casefold(),
            cls._normalized_text(text_en),
            cls._normalized_text(text_target),
            max(0, min(4, int(kind_code or 0))),
            max(0, min(7, int(context_code or 0))),
            1 if masked_flag else 0,
            1 if low_pairing_confidence_flag else 0,
        )

    def _parse_batch_results(self, parsed: Any, expected_item_ids: set[int]) -> dict[int, dict[str, Any]]:
        if not isinstance(parsed, dict):
            return {}
        results = parsed.get("r")
        if not isinstance(results, list):
            return {}
        valid: dict[int, dict[str, Any]] = {}
        for row in results:
            if not isinstance(row, list) or len(row) != 5:
                continue
            item_id = self._safe_int(row[0])
            if item_id is None or item_id not in expected_item_ids or item_id in valid:
                continue
            score_vals = row[1:4]
            note_code = self._safe_int(row[4])
            if note_code is None:
                continue
            if not all(self._is_numeric(val) for val in score_vals):
                continue
            valid[item_id] = {
                "spelling_score": self._score_from_percent(score_vals[0]),
                "grammar_score": self._score_from_percent(score_vals[1]),
                "meaning_mismatch_score": self._score_from_percent(score_vals[2]),
                "notes": [self._note_label(note_code)],
            }
        return valid

    def _llm_result(self, parsed: dict[str, Any]) -> _PairReviewResult:
        spelling_score = self._clamp(parsed.get("spelling_score"))
        grammar_score = self._clamp(parsed.get("grammar_score"))
        meaning_score = self._clamp(parsed.get("meaning_mismatch_score"))
        return _PairReviewResult(
            spelling_score=spelling_score,
            grammar_score=grammar_score,
            meaning_mismatch_score=meaning_score,
            notes=self._sanitize_notes(parsed.get("notes")),
            provider_meta={
                "provider": "llm",
                "review_mode": "llm",
                "model": self._model,
                "fallback_used": False,
                "confidence_provenance": "llm",
                "provider_score_summary": {
                    "spelling_score": spelling_score,
                    "grammar_score": grammar_score,
                    "meaning_mismatch_score": meaning_score,
                },
            },
        )

    def _fallback_result(self, text_en: str, text_target: str, language: str) -> _PairReviewResult:
        fallback_spelling_grammar = self._fallback.review_spelling_grammar(text_en, text_target, language)
        fallback_meaning = self._fallback.review_meaning(text_en, text_target, language)
        fallback_notes = self._merge_notes(
            fallback_spelling_grammar.notes,
            fallback_meaning.notes,
            ["ai_fallback_used"],
        )
        return _PairReviewResult(
            spelling_score=fallback_spelling_grammar.spelling_score,
            grammar_score=fallback_spelling_grammar.grammar_score,
            meaning_mismatch_score=fallback_meaning.meaning_mismatch_score,
            notes=fallback_notes,
            provider_meta={
                "provider": "llm",
                "review_mode": "llm",
                "model": self._model,
                "fallback_used": True,
                "fallback_origin": "deterministic_offline",
                "fallback_review_mode": "test-heuristic",
                "confidence_provenance": "heuristic",
            },
        )

    def _split_batches(self, language: str, items: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
        safe_budget = self._safe_context_budget()
        batches: list[list[dict[str, Any]]] = []
        current: list[dict[str, Any]] = []
        current_estimate = self._estimate_prompt_tokens()
        for item in items:
            item_estimate = self._estimate_item_tokens(language, item)
            if current and (current_estimate + item_estimate) > safe_budget:
                batches.append(current)
                current = []
                current_estimate = self._estimate_prompt_tokens()
            current.append(item)
            current_estimate += item_estimate
        if current:
            batches.append(current)
        return batches

    def _safe_context_budget(self) -> int:
        reserve = max(int(self._hard_context_tokens * self._token_reserve_ratio), self._fixed_token_margin)
        safe = self._hard_context_tokens - reserve
        return max(1024, safe)

    def _estimate_prompt_tokens(self) -> int:
        return self._estimate_tokens(self._system_prompt) + 200

    def _estimate_item_tokens(self, language: str, item: dict[str, Any]) -> int:
        return self._estimate_item_prompt_tokens(language, item) + self._estimated_output_tokens_per_item

    def _estimate_item_prompt_tokens(self, language: str, item: dict[str, Any]) -> int:
        serialized = json.dumps({"l": language, "i": [[0, item["text_en"], item["text_target"], item.get("kind_code", 1), item.get("context_code", 3), item.get("masked_flag", 0), item.get("low_pairing_confidence_flag", 0)]]}, ensure_ascii=False, separators=(",", ":"))
        return self._estimate_tokens(serialized) + 24

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        return max(1, ceil(len(text) / 3))

    @staticmethod
    def _is_numeric(value: Any) -> bool:
        try:
            float(value)
            return True
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _safe_int(value: Any) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _compute_cost(self, prompt_tokens: int, completion_tokens: int) -> float | None:
        if self._input_cost_per_1m is None or self._output_cost_per_1m is None:
            return None
        value = (prompt_tokens / 1_000_000.0) * self._input_cost_per_1m + (completion_tokens / 1_000_000.0) * self._output_cost_per_1m
        return round(value, 8)

    def _build_system_prompt(self, custom_prompt: str | None) -> str:
        base = (custom_prompt or "").strip() or self._DEFAULT_SYSTEM_PROMPT_BASE
        base_clean = base.rstrip()
        return f"{base_clean} {self._SYSTEM_PROMPT_CONTRACT_SUFFIX}"

    @staticmethod
    def _default_request(endpoint: str, api_key: str, timeout_s: float, payload: dict[str, Any]) -> dict[str, Any]:
        req = Request(
            endpoint,
            data=json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            method="POST",
        )
        with urlopen(req, timeout=timeout_s) as resp:  # noqa: S310 - endpoint is fixed by configuration.
            body = resp.read().decode("utf-8")
        return json.loads(body)

    @staticmethod
    def _clamp(value: Any) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(1.0, round(numeric, 4)))

    @staticmethod
    def _sanitize_notes(notes: Any) -> list[str]:
        if not isinstance(notes, list):
            return ["llm_response_no_notes"]
        sanitized = [str(n).strip() for n in notes if str(n).strip()]
        return sanitized[:5] if sanitized else ["llm_response_no_notes"]

    @staticmethod
    def _score_from_percent(value: Any) -> float:
        try:
            numeric = int(round(float(value)))
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(1.0, numeric / 100.0))

    @classmethod
    def _note_label(cls, note_code: int) -> str:
        return cls._NOTE_CODE_TO_LABEL.get(note_code, "uncertain")

    @staticmethod
    def _merge_notes(*note_lists: list[str]) -> list[str]:
        merged: list[str] = []
        for notes in note_lists:
            for note in notes:
                cleaned = str(note).strip()
                if cleaned and cleaned not in merged:
                    merged.append(cleaned)
        return merged[:5] if merged else ["llm_response_no_notes"]

    def get_llm_review_stats(self) -> dict[str, Any]:
        stats = _empty_llm_review_stats(
            review_mode="llm",
            provider_type="llm",
            configured_provider="llm",
            configured_model=self._model,
            effective_model=self._model,
        )
        stats["batches"] = [dict(batch) for batch in self._batch_stats]
        stats["llm_batches_attempted"] = sum(1 for batch in self._batch_stats if batch["status"] != "not_attempted")
        stats["llm_requested"] = stats["llm_batches_attempted"] > 0
        stats["llm_batches_succeeded"] = sum(1 for batch in self._batch_stats if batch["status"] == "succeeded")
        stats["llm_batches_failed"] = sum(1 for batch in self._batch_stats if batch["status"] == "failed")
        stats["fallback_batches"] = sum(1 for batch in self._batch_stats if batch["fallback_used"])
        stats["llm_items_requested"] = sum(int(batch["items"]) for batch in self._batch_stats)
        stats["llm_items_completed"] = sum(int(batch.get("llm_items_completed", 0)) for batch in self._batch_stats)
        stats["fallback_items"] = sum(int(batch.get("fallback_items", 0)) for batch in self._batch_stats)
        stats["estimated_prompt_tokens"] = sum(int(batch["estimated_prompt_tokens"]) for batch in self._batch_stats)
        stats["estimated_completion_tokens"] = sum(int(batch["estimated_completion_tokens"]) for batch in self._batch_stats)
        stats["estimated_total_tokens"] = sum(int(batch["estimated_total_tokens"]) for batch in self._batch_stats)
        est_costs = [batch["estimated_cost_usd"] for batch in self._batch_stats if batch.get("estimated_cost_usd") is not None]
        stats["estimated_cost_usd"] = round(sum(est_costs), 8) if len(est_costs) == len(self._batch_stats) and est_costs else None
        if self._has_actual_usage:
            stats["actual_prompt_tokens"] = self._actual_prompt_token_sum
            stats["actual_completion_tokens"] = self._actual_completion_token_sum
            stats["actual_total_tokens"] = self._actual_total_token_sum
            stats["actual_cost_usd"] = self._compute_cost(self._actual_prompt_token_sum, self._actual_completion_token_sum)
        stats["responses_received"] = sum(1 for batch in self._batch_stats if batch["response_received"])
        stats["transport_failures"] = sum(1 for batch in self._batch_stats if batch["failure_type"] == "transport")
        stats["parse_failures"] = sum(1 for batch in self._batch_stats if batch["failure_type"] == "parse")
        stats["provider_failures"] = sum(1 for batch in self._batch_stats if batch["failure_type"] == "provider")
        stats["used_fallback"] = stats["fallback_batches"] > 0
        reason_counts: dict[str, int] = {}
        for batch in self._batch_stats:
            if not batch.get("fallback_used"):
                continue
            failure_type = str(batch.get("failure_type") or "fallback")
            failure_message = str(batch.get("failure_message") or "").strip()
            reason = failure_type if not failure_message else f"{failure_type}:{failure_message}"
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
        stats["fallback_reason_summary"] = [
            reason for reason, _ in sorted(reason_counts.items(), key=lambda row: (-row[1], row[0]))[:5]
        ]
        return stats


def build_provider(mode: str, **provider_kwargs: Any) -> Phase6ReviewProvider:
    normalized = mode.strip().lower()
    if normalized == "offline":
        warnings.warn(
            "phase6 review mode 'offline' is deprecated; use 'test-heuristic'",
            DeprecationWarning,
            stacklevel=2,
        )
        normalized = "test-heuristic"
    elif normalized == "ai":
        warnings.warn(
            "phase6 review mode 'ai' is deprecated; use 'llm'",
            DeprecationWarning,
            stacklevel=2,
        )
        normalized = "llm"

    if normalized in {"test-heuristic", "heuristic", "deterministic"}:
        return DeterministicOfflineProvider()
    if normalized in {"disabled", "off", "none"}:
        return DisabledReviewProvider()
    if normalized in {"llm", "openai"}:
        def _read_float(env_key: str, default: float) -> float:
            raw = os.environ.get(env_key, str(default))
            try:
                return float(raw)
            except (TypeError, ValueError):
                return default

        def _read_int(env_key: str, default: int) -> int:
            raw = os.environ.get(env_key, str(default))
            try:
                return int(raw)
            except (TypeError, ValueError):
                return default

        raw_timeout = os.environ.get("PHASE6_REVIEW_TIMEOUT_S", "8")
        try:
            timeout_s = float(raw_timeout)
        except (TypeError, ValueError):
            timeout_s = 8.0
        return LLMReviewProvider(
            api_key=os.environ.get("PHASE6_REVIEW_API_KEY"),
            model=os.environ.get("PHASE6_REVIEW_MODEL", "openrouter/free"),
            timeout_s=timeout_s,
            endpoint=os.environ.get("PHASE6_REVIEW_ENDPOINT", "https://openrouter.ai/api/v1/chat/completions"),
            system_prompt=os.environ.get("PHASE6_REVIEW_SYSTEM_PROMPT"),
            hard_context_tokens=_read_int("PHASE6_REVIEW_HARD_CONTEXT_TOKENS", 150000),
            token_reserve_ratio=_read_float("PHASE6_REVIEW_TOKEN_RESERVE_RATIO", 0.20),
            fixed_token_margin=_read_int("PHASE6_REVIEW_FIXED_TOKEN_MARGIN", 1024),
            estimated_output_tokens_per_item=_read_int("PHASE6_REVIEW_ESTIMATED_OUTPUT_TOKENS_PER_ITEM", 64),
            **provider_kwargs,
        )
    raise ValueError(
        f"Unsupported phase6 review mode: {mode!r}. Supported modes: test-heuristic, disabled, llm"
    )
