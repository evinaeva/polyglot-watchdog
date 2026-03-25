import json
from urllib.error import URLError

import pytest

from pipeline.phase6_providers import (
    DeterministicOfflineProvider,
    DisabledReviewProvider,
    LLMReviewProvider,
    build_provider,
)


def test_build_provider_selection_modes(monkeypatch):
    assert isinstance(build_provider("test-heuristic"), DeterministicOfflineProvider)
    assert isinstance(build_provider("disabled"), DisabledReviewProvider)

    monkeypatch.setenv("PHASE6_REVIEW_API_KEY", "test-key")
    provider = build_provider("llm")
    assert isinstance(provider, LLMReviewProvider)
    assert provider._model == "openrouter/free"
    assert provider._endpoint == "https://openrouter.ai/api/v1/chat/completions"


def test_build_provider_deprecated_aliases_emit_warnings(monkeypatch):
    with pytest.deprecated_call(match="offline"):
        heuristic = build_provider("offline")
    assert isinstance(heuristic, DeterministicOfflineProvider)

    monkeypatch.setenv("PHASE6_REVIEW_API_KEY", "test-key")
    with pytest.deprecated_call(match="ai"):
        llm = build_provider("ai")
    assert isinstance(llm, LLMReviewProvider)


def test_build_provider_rejects_unknown_mode():
    with pytest.raises(ValueError, match="Unsupported phase6 review mode"):
        build_provider("something-else")


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
            "results": [
                {
                    "item_id": "item_0",
                    "spelling_score": 1.4,
                    "grammar_score": 0.42,
                    "meaning_mismatch_score": -2,
                    "notes": ["likely typo", "low context confidence"],
                }
            ]
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
            "results": [
                {
                    "item_id": "item_0",
                    "spelling_score": 0.2,
                    "grammar_score": 0.4,
                    "meaning_mismatch_score": 0.6,
                    "notes": ["single-call"],
                }
            ]
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
        user = json.loads(payload["messages"][1]["content"])
        result_rows = []
        for item in user["items"]:
            result_rows.append(
                {
                    "item_id": item["item_id"],
                    "spelling_score": 0.2,
                    "grammar_score": 0.4,
                    "meaning_mismatch_score": 0.6,
                    "notes": [item["text_target"]],
                }
            )
        response_payload = {
            "results": result_rows,
        }
        return {"choices": [{"message": {"content": json.dumps(response_payload)}}]}

    provider = LLMReviewProvider(api_key="k", request_fn=good_request)

    first = provider.review_spelling_grammar("Hello", "Bonjour", "fr")
    second = provider.review_meaning("Hello", "Hola", "es")

    assert attempts == 2
    assert first.notes != second.notes


def test_llm_provider_batch_prefetch_single_request_multiple_pairs():
    attempts = 0

    def good_request(endpoint, api_key, timeout_s, payload):
        nonlocal attempts
        attempts += 1
        user = json.loads(payload["messages"][1]["content"])
        assert "language" in user
        assert len(user["items"]) == 2
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "results": [
                                    {
                                        "item_id": item["item_id"],
                                        "spelling_score": 0.1,
                                        "grammar_score": 0.2,
                                        "meaning_mismatch_score": 0.3,
                                        "notes": ["batched"],
                                    }
                                    for item in user["items"]
                                ]
                            }
                        )
                    }
                }
            ]
        }

    provider = LLMReviewProvider(api_key="k", request_fn=good_request)
    provider.prefetch_reviews([("Hello", "Bonjour"), ("Buy now", "Acheter maintenant")], "fr")
    first = provider.review_spelling_grammar("Hello", "Bonjour", "fr")
    second = provider.review_meaning("Buy now", "Acheter maintenant", "fr")

    assert attempts == 1
    assert first.spelling_score == 0.1
    assert second.meaning_mismatch_score == 0.3


def test_test_heuristic_provider_has_required_provenance_fields():
    provider = build_provider("test-heuristic")

    sg = provider.review_spelling_grammar("Hello", "teh", "fr")
    meaning = provider.review_meaning("Hello", "Hello", "fr")

    expected = {
        "provider": "deterministic-offline",
        "review_mode": "test-heuristic",
        "confidence_provenance": "heuristic",
        "origin": "deterministic_offline",
        "fallback_used": False,
    }
    assert sg.provider_meta == expected
    assert meaning.provider_meta == expected


def test_llm_stats_success_with_usage_payload():
    def good_request(endpoint, api_key, timeout_s, payload):
        return {
            "usage": {"prompt_tokens": 120, "completion_tokens": 30, "total_tokens": 150},
            "choices": [{
                "message": {
                    "content": json.dumps(
                        {"results": [{"item_id": "item_0", "spelling_score": 0.1, "grammar_score": 0.2, "meaning_mismatch_score": 0.3, "notes": []}]}
                    )
                }
            }],
        }

    provider = LLMReviewProvider(api_key="k", request_fn=good_request)
    provider.prefetch_reviews([("Hello", "Bonjour")], "fr")
    stats = provider.get_llm_review_stats()
    assert stats["llm_requested"] is True
    assert stats["llm_batches_succeeded"] == 1
    assert stats["actual_prompt_tokens"] == 120
    assert stats["actual_completion_tokens"] == 30
    assert stats["actual_total_tokens"] == 150
    assert stats["responses_received"] == 1
    assert stats["parse_failures"] == 0


def test_llm_stats_success_without_usage_payload():
    def good_request(endpoint, api_key, timeout_s, payload):
        return {
            "choices": [{
                "message": {
                    "content": json.dumps(
                        {"results": [{"item_id": "item_0", "spelling_score": 0.1, "grammar_score": 0.2, "meaning_mismatch_score": 0.3, "notes": []}]}
                    )
                }
            }],
        }

    provider = LLMReviewProvider(api_key="k", request_fn=good_request)
    provider.prefetch_reviews([("Hello", "Bonjour")], "fr")
    stats = provider.get_llm_review_stats()
    assert stats["actual_prompt_tokens"] is None
    assert stats["actual_completion_tokens"] is None
    assert stats["actual_total_tokens"] is None


def test_llm_stats_transport_failure_records_fallback():
    def fail_request(endpoint, api_key, timeout_s, payload):
        raise URLError("network down")

    provider = LLMReviewProvider(api_key="k", request_fn=fail_request)
    provider.prefetch_reviews([("Hello", "Bonjour")], "fr")
    stats = provider.get_llm_review_stats()
    assert stats["transport_failures"] == 1
    assert stats["llm_batches_failed"] == 1
    assert stats["fallback_batches"] == 1
    assert stats["used_fallback"] is True
    assert stats["batches"][0]["status"] == "failed"


def test_llm_stats_parse_failure_records_fallback():
    def bad_payload_request(endpoint, api_key, timeout_s, payload):
        return {"choices": [{"message": {"content": "not-json"}}]}

    provider = LLMReviewProvider(api_key="k", request_fn=bad_payload_request)
    provider.prefetch_reviews([("Hello", "Bonjour")], "fr")
    stats = provider.get_llm_review_stats()
    assert stats["parse_failures"] == 1
    assert stats["llm_batches_failed"] == 1
    assert stats["fallback_batches"] == 1
    assert stats["used_fallback"] is True


def test_llm_stats_mixed_multi_batch_execution():
    attempts = 0

    def mixed_request(endpoint, api_key, timeout_s, payload):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return {
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
                "choices": [{"message": {"content": json.dumps({"results": [{"item_id": "item_0", "spelling_score": 0.1, "grammar_score": 0.1, "meaning_mismatch_score": 0.1, "notes": []}]})}}],
            }
        raise URLError("timeout")

    provider = LLMReviewProvider(api_key="k", hard_context_tokens=1024, fixed_token_margin=128, request_fn=mixed_request)
    provider.prefetch_reviews([("a" * 2000, "b" * 2000), ("short", "court")], "fr")
    stats = provider.get_llm_review_stats()
    assert stats["llm_batches_attempted"] == 2
    assert stats["llm_batches_succeeded"] == 1
    assert stats["llm_batches_failed"] == 1
    assert stats["transport_failures"] == 1
    assert stats["fallback_batches"] == 1


def test_failed_batch_status_is_not_overwritten_by_fallback_status():
    def fail_request(endpoint, api_key, timeout_s, payload):
        raise URLError("gateway timeout")

    provider = LLMReviewProvider(api_key="k", request_fn=fail_request)
    provider.prefetch_reviews([("Hello", "Bonjour")], "fr")
    stats = provider.get_llm_review_stats()

    assert stats["llm_batches_attempted"] == 1
    assert stats["llm_batches_failed"] == 1
    assert stats["fallback_batches"] == 1
    assert stats["batches"][0]["status"] == "failed"
    assert stats["batches"][0]["fallback_used"] is True
