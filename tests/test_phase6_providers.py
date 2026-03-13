import json

from pipeline.phase6_providers import (
    DeterministicOfflineProvider,
    DisabledReviewProvider,
    LLMReviewProvider,
    build_provider,
)


def test_build_provider_selection_modes(monkeypatch):
    assert isinstance(build_provider("offline"), DeterministicOfflineProvider)
    assert isinstance(build_provider("disabled"), DisabledReviewProvider)

    monkeypatch.setenv("PHASE6_REVIEW_API_KEY", "test-key")
    provider = build_provider("ai")
    assert isinstance(provider, LLMReviewProvider)


def test_llm_provider_missing_api_key_uses_deterministic_fallback():
    provider = LLMReviewProvider(api_key="")

    sg = provider.review_spelling_grammar("Buy now", "teh translation", "fr")
    assert sg.spelling_score == 0.86
    assert sg.grammar_score == 0.0
    assert "ai_fallback_used" in sg.notes
    assert sg.provider_meta["fallback_used"] is True

    meaning = provider.review_meaning("Buy now", "Buy now", "fr")
    assert meaning.meaning_mismatch_score == 0.8
    assert "ai_fallback_used" in meaning.notes
    assert meaning.provider_meta["fallback_used"] is True


def test_llm_provider_malformed_response_degrades_safely_and_reuses_fallback_once():
    attempts = 0

    def bad_request(endpoint, api_key, timeout_s, payload):
        nonlocal attempts
        attempts += 1
        return {"choices": [{"message": {"content": "not-json"}}]}

    provider = LLMReviewProvider(api_key="k", request_fn=bad_request)
    sg = provider.review_spelling_grammar("Buy now", "teh translation", "fr")
    meaning = provider.review_meaning("Buy now", "teh translation", "fr")

    assert attempts == 1
    assert sg.spelling_score == 0.86
    assert meaning.meaning_mismatch_score == 0.0
    assert "ai_fallback_used" in sg.notes
    assert sg.notes == meaning.notes
    assert sg.provider_meta == meaning.provider_meta
    assert sg.provider_meta["fallback_used"] is True


def test_llm_provider_parses_and_clamps_json_response():
    def good_request(endpoint, api_key, timeout_s, payload):
        response_payload = {
            "spelling_score": 1.4,
            "grammar_score": 0.42,
            "meaning_mismatch_score": -2,
            "notes": ["likely typo", "low context confidence"],
        }
        return {"choices": [{"message": {"content": json.dumps(response_payload)}}]}

    provider = LLMReviewProvider(api_key="k", request_fn=good_request)
    sg = provider.review_spelling_grammar("Buy now", "Acheter", "fr")
    meaning = provider.review_meaning("Buy now", "Acheter", "fr")

    assert sg.spelling_score == 1.0
    assert sg.grammar_score == 0.42
    assert sg.notes == ["likely typo", "low context confidence"]
    assert sg.provider_meta["fallback_used"] is False
    assert sg.provider_meta["provider_score_summary"] == {
        "spelling_score": 1.0,
        "grammar_score": 0.42,
        "meaning_mismatch_score": 0.0,
    }

    assert meaning.meaning_mismatch_score == 0.0
    assert meaning.provider_meta["provider_score_summary"] == {
        "spelling_score": 1.0,
        "grammar_score": 0.42,
        "meaning_mismatch_score": 0.0,
    }


def test_llm_provider_reuses_single_ai_request_for_same_pair():
    attempts = 0

    def good_request(endpoint, api_key, timeout_s, payload):
        nonlocal attempts
        attempts += 1
        response_payload = {
            "spelling_score": 0.2,
            "grammar_score": 0.4,
            "meaning_mismatch_score": 0.6,
            "notes": ["single-call"],
        }
        return {"choices": [{"message": {"content": json.dumps(response_payload)}}]}

    provider = LLMReviewProvider(api_key="k", request_fn=good_request)

    provider.review_spelling_grammar("Hello", "Bonjour", "fr")
    provider.review_meaning("Hello", "Bonjour", "fr")

    assert attempts == 1


def test_llm_provider_cache_separates_different_pairs():
    attempts = 0

    def good_request(endpoint, api_key, timeout_s, payload):
        nonlocal attempts
        attempts += 1
        response_payload = {
            "spelling_score": 0.2,
            "grammar_score": 0.4,
            "meaning_mismatch_score": 0.6,
            "notes": [payload["messages"][1]["content"]],
        }
        return {"choices": [{"message": {"content": json.dumps(response_payload)}}]}

    provider = LLMReviewProvider(api_key="k", request_fn=good_request)

    first = provider.review_spelling_grammar("Hello", "Bonjour", "fr")
    second = provider.review_meaning("Hello", "Hola", "es")

    assert attempts == 2
    assert first.notes != second.notes
