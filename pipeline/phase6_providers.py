"""Phase 6 provider interfaces for optional AI-assisted translation checks.

Default providers are deterministic and offline-safe.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SpellingGrammarSignals:
    spelling_score: float
    grammar_score: float
    notes: list[str]


@dataclass(frozen=True)
class MeaningSignals:
    meaning_mismatch_score: float
    notes: list[str]


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


def build_provider(mode: str = "offline") -> Phase6ReviewProvider:
    normalized = mode.strip().lower()
    if normalized in {"disabled", "off", "none"}:
        return DisabledReviewProvider()
    return DeterministicOfflineProvider()
