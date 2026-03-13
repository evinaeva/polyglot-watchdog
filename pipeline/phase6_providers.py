"""Phase 6 provider interfaces for optional AI-assisted translation checks.

Default providers are deterministic and offline-safe.
"""

from __future__ import annotations

import json
import os
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

    def __init__(
        self,
        api_key: str | None,
        model: str = "gpt-4o-mini",
        timeout_s: float = 8.0,
        endpoint: str = "https://api.openai.com/v1/chat/completions",
        fallback_provider: Phase6ReviewProvider | None = None,
        request_fn: Callable[[str, str, float, dict[str, Any]], dict[str, Any]] | None = None,
    ) -> None:
        self._api_key = (api_key or "").strip()
        self._model = model
        self._timeout_s = timeout_s
        self._endpoint = endpoint
        self._fallback = fallback_provider or DeterministicOfflineProvider()
        self._request_fn = request_fn or self._default_request

    def review_spelling_grammar(self, text_en: str, text_target: str, language: str) -> SpellingGrammarSignals:
        parsed = self._review(text_en=text_en, text_target=text_target, language=language)
        if parsed is None:
            fallback = self._fallback.review_spelling_grammar(text_en, text_target, language)
            return SpellingGrammarSignals(
                spelling_score=fallback.spelling_score,
                grammar_score=fallback.grammar_score,
                notes=[*fallback.notes, "ai_fallback_used"],
                provider_meta={"provider": "llm", "mode": "ai", "model": self._model, "fallback_used": True},
            )

        return SpellingGrammarSignals(
            spelling_score=self._clamp(parsed.get("spelling_score")),
            grammar_score=self._clamp(parsed.get("grammar_score")),
            notes=self._sanitize_notes(parsed.get("notes")),
            provider_meta={
                "provider": "llm",
                "mode": "ai",
                "model": self._model,
                "fallback_used": False,
                "provider_score_summary": {
                    "spelling_score": self._clamp(parsed.get("spelling_score")),
                    "grammar_score": self._clamp(parsed.get("grammar_score")),
                },
            },
        )

    def review_meaning(self, text_en: str, text_target: str, language: str) -> MeaningSignals:
        parsed = self._review(text_en=text_en, text_target=text_target, language=language)
        if parsed is None:
            fallback = self._fallback.review_meaning(text_en, text_target, language)
            return MeaningSignals(
                meaning_mismatch_score=fallback.meaning_mismatch_score,
                notes=[*fallback.notes, "ai_fallback_used"],
                provider_meta={"provider": "llm", "mode": "ai", "model": self._model, "fallback_used": True},
            )

        return MeaningSignals(
            meaning_mismatch_score=self._clamp(parsed.get("meaning_mismatch_score")),
            notes=self._sanitize_notes(parsed.get("notes")),
            provider_meta={
                "provider": "llm",
                "mode": "ai",
                "model": self._model,
                "fallback_used": False,
                "provider_score_summary": {"meaning_mismatch_score": self._clamp(parsed.get("meaning_mismatch_score"))},
            },
        )

    def _review(self, text_en: str, text_target: str, language: str) -> dict[str, Any] | None:
        if not self._api_key:
            return None

        payload = {
            "model": self._model,
            "response_format": {"type": "json_object"},
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You review localization text quality. Return only strict JSON with keys "
                        "spelling_score, grammar_score, meaning_mismatch_score, notes. "
                        "Scores must be numeric between 0 and 1, where higher means higher risk. "
                        "notes must be an array of concise uncertainty-aware rationale strings."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "text_en": text_en,
                            "text_target": text_target,
                            "language": language,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        }

        try:
            response = self._request_fn(self._endpoint, self._api_key, self._timeout_s, payload)
            content = response["choices"][0]["message"]["content"]
            parsed = json.loads(content)
        except (KeyError, IndexError, TypeError, ValueError, URLError):
            return None

        if not isinstance(parsed, dict):
            return None
        return parsed

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


def build_provider(mode: str = "offline") -> Phase6ReviewProvider:
    normalized = mode.strip().lower()
    if normalized in {"disabled", "off", "none"}:
        return DisabledReviewProvider()
    if normalized in {"ai", "llm", "openai"}:
        raw_timeout = os.environ.get("PHASE6_REVIEW_TIMEOUT_S", "8")
        try:
            timeout_s = float(raw_timeout)
        except (TypeError, ValueError):
            timeout_s = 8.0
        return LLMReviewProvider(
            api_key=os.environ.get("PHASE6_REVIEW_API_KEY"),
            model=os.environ.get("PHASE6_REVIEW_MODEL", "gpt-4o-mini"),
            timeout_s=timeout_s,
            endpoint=os.environ.get("PHASE6_REVIEW_ENDPOINT", "https://api.openai.com/v1/chat/completions"),
        )
    return DeterministicOfflineProvider()
