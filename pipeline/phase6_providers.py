"""Phase 6 provider interfaces for optional AI-assisted translation checks.

Default providers are deterministic and offline-safe.
"""

from __future__ import annotations

import json
import os
from math import ceil
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol
from urllib.error import URLError
from urllib.request import Request, urlopen


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
    def review_spelling_grammar(self, text_en: str, text_target: str, language: str) -> SpellingGrammarSignals:
        ...

    def review_meaning(self, text_en: str, text_target: str, language: str) -> MeaningSignals:
        ...


class DeterministicOfflineProvider:
    """Heuristic-only provider with deterministic outputs and no network calls."""

    _SPELLING_MARKERS = ("teh", "recieve", "definately")

    def review_spelling_grammar(self, text_en: str, text_target: str, language: str) -> SpellingGrammarSignals:
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

        return SpellingGrammarSignals(spelling_score=spelling_score, grammar_score=grammar_score, notes=notes)

    def review_meaning(self, text_en: str, text_target: str, language: str) -> MeaningSignals:
        notes: list[str] = []
        score = 0.0

        if text_en and text_target and len(text_target) < max(3, len(text_en) // 4):
            score = 0.65
            notes.append("target_much_shorter_than_source")

        if text_en and text_target and text_en.lower() == text_target.lower():
            score = max(score, 0.8)
            notes.append("identical_text_signal")

        return MeaningSignals(meaning_mismatch_score=score, notes=notes)


class DisabledReviewProvider:
    """Provider that emits no AI-assisted signals."""

    def review_spelling_grammar(self, text_en: str, text_target: str, language: str) -> SpellingGrammarSignals:
        return SpellingGrammarSignals(spelling_score=0.0, grammar_score=0.0, notes=["provider_disabled"])

    def review_meaning(self, text_en: str, text_target: str, language: str) -> MeaningSignals:
        return MeaningSignals(meaning_mismatch_score=0.0, notes=["provider_disabled"])


class LLMReviewProvider:
    """JSON-only LLM review provider with deterministic offline fallback."""

    _DEFAULT_SYSTEM_PROMPT = (
        "You review localization text quality for EN to target translations. "
        "Assess spelling, grammar, and meaning mismatch risk."
    )
    _SYSTEM_PROMPT_CONTRACT_SUFFIX = (
        " Return ONLY JSON object with key results. results must be an array of objects with keys: "
        "item_id, spelling_score, grammar_score, meaning_mismatch_score, notes. "
        "Scores must be numeric from 0 to 1 where higher is higher risk. "
        "notes must be an array of concise strings."
    )

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
        self._pair_reviews: dict[tuple[str, str, str], _PairReviewResult] = {}

    def prefetch_reviews(self, pairs: list[tuple[str, str]], language: str) -> None:
        unresolved_items: list[dict[str, Any]] = []
        for idx, (text_en, text_target) in enumerate(pairs):
            cache_key = (text_en, text_target, language)
            if cache_key in self._pair_reviews:
                continue
            unresolved_items.append(
                {"item_id": f"item_{idx}", "text_en": text_en, "text_target": text_target, "cache_key": cache_key}
            )
        if not unresolved_items:
            return
        for batch in self._split_batches(language=language, items=unresolved_items):
            self._execute_batch(language=language, items=batch)

    def review_spelling_grammar(self, text_en: str, text_target: str, language: str) -> SpellingGrammarSignals:
        pair_review = self._get_pair_review(text_en=text_en, text_target=text_target, language=language)

        return SpellingGrammarSignals(
            spelling_score=pair_review.spelling_score,
            grammar_score=pair_review.grammar_score,
            notes=pair_review.notes,
            provider_meta=pair_review.provider_meta,
        )

    def review_meaning(self, text_en: str, text_target: str, language: str) -> MeaningSignals:
        pair_review = self._get_pair_review(text_en=text_en, text_target=text_target, language=language)

        return MeaningSignals(
            meaning_mismatch_score=pair_review.meaning_mismatch_score,
            notes=pair_review.notes,
            provider_meta=pair_review.provider_meta,
        )

    def _get_pair_review(self, text_en: str, text_target: str, language: str) -> _PairReviewResult:
        cache_key = (text_en, text_target, language)
        cached = self._pair_reviews.get(cache_key)
        if cached is not None:
            return cached

        self.prefetch_reviews([(text_en, text_target)], language)
        return self._pair_reviews.get(cache_key) or self._fallback_result(text_en, text_target, language)

    def _execute_batch(self, language: str, items: list[dict[str, Any]]) -> None:
        parsed_by_item_id = self._review_batch(language=language, items=items)
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

    def _review_batch(self, language: str, items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        if not self._api_key:
            return {}

        user_payload = {
            "language": language,
            "items": [
                {"item_id": item["item_id"], "text_en": item["text_en"], "text_target": item["text_target"]}
                for item in items
            ],
        }
        payload = {
            "model": self._model,
            "response_format": {"type": "json_object"},
            "temperature": 0,
            "messages": [
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
        }

        try:
            response = self._request_fn(self._endpoint, self._api_key, self._timeout_s, payload)
            content = response["choices"][0]["message"]["content"]
            parsed = json.loads(content)
        except (KeyError, IndexError, TypeError, ValueError, URLError):
            return {}
        return self._parse_batch_results(parsed, {item["item_id"] for item in items})

    def _parse_batch_results(self, parsed: Any, expected_item_ids: set[str]) -> dict[str, dict[str, Any]]:
        if not isinstance(parsed, dict):
            return {}
        results = parsed.get("results")
        if not isinstance(results, list):
            return {}
        valid: dict[str, dict[str, Any]] = {}
        for row in results:
            if not isinstance(row, dict):
                continue
            item_id = str(row.get("item_id", "")).strip()
            if not item_id or item_id not in expected_item_ids or item_id in valid:
                continue
            required_scores = ("spelling_score", "grammar_score", "meaning_mismatch_score")
            if not all(key in row for key in required_scores):
                continue
            if not all(self._is_numeric(row.get(key)) for key in required_scores):
                continue
            valid[item_id] = row
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
                "mode": "ai",
                "model": self._model,
                "fallback_used": False,
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
            provider_meta={"provider": "llm", "mode": "ai", "model": self._model, "fallback_used": True},
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
        serialized = json.dumps(
            {"language": language, "items": [{"item_id": item["item_id"], "text_en": item["text_en"], "text_target": item["text_target"]}]},
            ensure_ascii=False,
        )
        return self._estimate_tokens(serialized) + self._estimated_output_tokens_per_item + 24

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

    def _build_system_prompt(self, custom_prompt: str | None) -> str:
        base = (custom_prompt or "").strip() or self._DEFAULT_SYSTEM_PROMPT
        return f"{base}{self._SYSTEM_PROMPT_CONTRACT_SUFFIX}"

    @staticmethod
    def _default_request(endpoint: str, api_key: str, timeout_s: float, payload: dict[str, Any]) -> dict[str, Any]:
        req = Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
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
    def _merge_notes(*note_lists: list[str]) -> list[str]:
        merged: list[str] = []
        for notes in note_lists:
            for note in notes:
                cleaned = str(note).strip()
                if cleaned and cleaned not in merged:
                    merged.append(cleaned)
        return merged[:5] if merged else ["llm_response_no_notes"]


def build_provider(mode: str = "offline") -> Phase6ReviewProvider:
    normalized = mode.strip().lower()
    if normalized in {"disabled", "off", "none"}:
        return DisabledReviewProvider()
    if normalized in {"ai", "llm", "openai"}:
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
        )
    return DeterministicOfflineProvider()
