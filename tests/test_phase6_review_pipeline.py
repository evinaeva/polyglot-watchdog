from unittest.mock import patch

import pytest

from pipeline.run_phase6 import run
from pipeline.phase6_review import prepare_review_inputs


def _base_artifacts(target_item_overrides=None):
    en_item = {
        "item_id": "item-1",
        "page_id": "en-page-1",
        "url": "https://example.com/p",
        "language": "en",
        "viewport_kind": "desktop",
        "state": "baseline",
        "user_tier": "guest",
        "element_type": "p",
        "css_selector": "main > p",
        "bbox": {"x": 1, "y": 2, "width": 3, "height": 4},
        "text": "Buy now",
        "visible": True,
        "tag": "p",
        "attributes": None,
    }
    target_item = {
        "item_id": "item-1",
        "page_id": "fr-page-1",
        "url": "https://example.com/fr/p",
        "language": "fr",
        "viewport_kind": "desktop",
        "state": "baseline",
        "user_tier": "guest",
        "element_type": "p",
        "css_selector": "main > p",
        "bbox": {"x": 1, "y": 2, "width": 3, "height": 4},
        "text": "Acheter",
        "visible": True,
        "tag": "p",
        "attributes": None,
    }
    if target_item_overrides:
        target_item.update(target_item_overrides)

    return [
        [en_item],
        [target_item],
        [{"item_id": "item-1", "page_id": "en-page-1", "bbox": {"x": 1, "y": 2, "width": 3, "height": 4}}],
        [{"item_id": "item-1", "page_id": "fr-page-1", "bbox": {"x": 1, "y": 2, "width": 3, "height": 4}}],
        [{"page_id": "en-page-1", "storage_uri": "gs://b/en.png"}],
        [{"page_id": "fr-page-1", "storage_uri": "gs://b/fr.png"}],
        FileNotFoundError("phase4_ocr missing"),
    ]


def test_review_class_mapping_and_rich_evidence_for_placeholder():
    artifacts = _base_artifacts({"text": "Acheter %s"})
    artifacts[0][0]["text"] = "Buy now <name>"

    with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts), patch(
        "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
    ), patch("pipeline.run_phase6.write_json_artifact"), patch("pipeline.run_phase6.write_phase_manifest"):
        issues = run("example.com", "run-en", "run-fr", review_mode="test-heuristic")

    assert len(issues) == 1
    issue = issues[0]
    assert issue["category"] == "FORMATTING_MISMATCH"
    assert issue["evidence"]["review_class"] == "PLACEHOLDER"
    assert issue["evidence"]["reason"]
    assert "signals" in issue["evidence"]
    assert issue["evidence"]["pairing_basis"] in {"logical_match_key_exact", "fallback_weighted"}
    assert issue["evidence"]["text_en"] == "Buy now <name>"
    assert issue["evidence"]["text_target"] == "Acheter %s"


def test_ocr_metadata_applies_only_to_image_items():
    artifacts = _base_artifacts({"tag": "img", "element_type": "img", "ocr_text": "X", "text": "Acheter"})

    with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts), patch(
        "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
    ), patch("pipeline.run_phase6.write_json_artifact"), patch("pipeline.run_phase6.write_phase_manifest"):
        issues = run("example.com", "run-en", "run-fr", review_mode="test-heuristic")

    assert len(issues) == 1
    issue = issues[0]
    assert issue["evidence"]["review_class"] == "OCR_NOISE"
    assert issue["category"] == "FORMATTING_MISMATCH"
    assert issue["evidence"]["ocr_text"] == "X"
    assert issue["evidence"]["ocr_engine"] == "OCR.Space:engine3"




def test_image_backed_review_prefers_good_ocr_text_over_unreliable_dom_text():
    artifacts = _base_artifacts(
        {
            "tag": "img",
            "element_type": "img",
            "text": "Texte DOM fiable mais non fautif",
            "ocr_text": "teh translation",
            "ocr_notes": [],
        }
    )

    with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts), patch(
        "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
    ), patch("pipeline.run_phase6.write_json_artifact"), patch("pipeline.run_phase6.write_phase_manifest"):
        issues = run("example.com", "run-en", "run-fr", review_mode="test-heuristic")

    spelling_issue = next(issue for issue in issues if issue["evidence"]["review_class"] == "SPELLING")
    assert spelling_issue["evidence"]["text_target"] == "teh translation"
    assert spelling_issue["evidence"]["ocr_text"] == "teh translation"
    assert spelling_issue["evidence"]["comparison_text_source"] == "ocr"


def test_weak_ocr_falls_back_to_dom_for_canonical_comparison_text():
    artifacts = _base_artifacts(
        {
            "tag": "img",
            "element_type": "img",
            "text": "teh translation",
            "ocr_text": "!!! $$$$ ----",
            "ocr_notes": ["uncertain parse"],
        }
    )

    with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts), patch(
        "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
    ), patch("pipeline.run_phase6.write_json_artifact"), patch("pipeline.run_phase6.write_phase_manifest"):
        issues = run("example.com", "run-en", "run-fr", review_mode="test-heuristic")

    spelling_issue = next(issue for issue in issues if issue["evidence"]["review_class"] == "SPELLING")
    assert spelling_issue["evidence"]["text_target"] == "teh translation"
    assert spelling_issue["evidence"]["comparison_text_source"] == "dom"
    ocr_issue = next(issue for issue in issues if issue["evidence"]["review_class"] == "OCR_NOISE")
    assert ocr_issue["evidence"]["ocr_quality"]["trust_bucket"] == "weak"


def test_image_item_with_ocr_handoff_metadata_but_unusable_text_falls_back_to_dom():
    artifacts = _base_artifacts(
        {
            "tag": "img",
            "element_type": "img",
            "text": "teh translation",
            "ocr_text": "   ",
            "ocr_notes": ["empty result"],
            "ocr_engine": "OCR.Space:engine3",
        }
    )

    with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts), patch(
        "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
    ), patch("pipeline.run_phase6.write_json_artifact"), patch("pipeline.run_phase6.write_phase_manifest"):
        issues = run("example.com", "run-en", "run-fr", review_mode="test-heuristic")

    spelling_issue = next(issue for issue in issues if issue["evidence"]["review_class"] == "SPELLING")
    assert spelling_issue["evidence"]["text_target"] == "teh translation"
    assert spelling_issue["evidence"]["comparison_text_source"] == "dom"


def test_non_image_items_do_not_receive_ocr_signals():
    artifacts = _base_artifacts({"ocr_text": "X", "text": "Acheter"})

    with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts), patch(
        "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
    ), patch("pipeline.run_phase6.write_json_artifact"), patch("pipeline.run_phase6.write_phase_manifest"):
        issues = run("example.com", "run-en", "run-fr", review_mode="test-heuristic")

    assert issues == []


def test_provider_disabled_mode_is_deterministic_and_offline():
    artifacts = _base_artifacts({"text": "teh translation"})

    with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts), patch(
        "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
    ), patch("pipeline.run_phase6.write_json_artifact"), patch("pipeline.run_phase6.write_phase_manifest"), patch.dict(
        "os.environ", {"PHASE6_REVIEW_PROVIDER": "disabled"}, clear=False
    ):
        issues = run("example.com", "run-en", "run-fr", review_mode="disabled")

    assert issues == []


def test_confidence_and_ordering_are_deterministic():
    artifacts = _base_artifacts({"text": "Buy now"})

    with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts), patch(
        "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
    ), patch("pipeline.run_phase6.write_json_artifact"), patch("pipeline.run_phase6.write_phase_manifest"):
        first = run("example.com", "run-en", "run-fr", review_mode="test-heuristic")

    with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts), patch(
        "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
    ), patch("pipeline.run_phase6.write_json_artifact"), patch("pipeline.run_phase6.write_phase_manifest"):
        second = run("example.com", "run-en", "run-fr", review_mode="test-heuristic")

    assert len(first) == 1
    assert first == second
    assert first[0]["confidence"] == 0.7
    assert first[0]["evidence"]["signals"] == {"identical_text": 0.2, "untranslated_indicator": 0.1}


def test_missing_target_evidence_prefers_collected_page_id_for_storage_lookup():
    artifacts = _base_artifacts()
    # Remove target so EN item becomes missing-target case.
    artifacts[1] = []
    artifacts[2] = [{"item_id": "item-1", "page_id": "en-page-collected", "bbox": {"x": 1, "y": 2, "width": 3, "height": 4}}]
    artifacts[4] = [{"page_id": "en-page-collected", "storage_uri": "gs://b/en-collected.png"}]
    artifacts[0][0]["page_id"] = "en-page-ignored"

    with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts), patch(
        "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
    ), patch("pipeline.run_phase6.write_json_artifact"), patch("pipeline.run_phase6.write_phase_manifest"):
        issues = run("example.com", "run-en", "run-fr", review_mode="test-heuristic")

    assert len(issues) == 1
    issue = issues[0]
    assert issue["category"] == "MISSING_TRANSLATION"
    assert issue["evidence"]["page_id"] == "en-page-collected"
    assert issue["evidence"]["storage_uri"] == "gs://b/en-collected.png"


def test_prepare_review_inputs_matches_dom_text_pair():
    artifacts = _base_artifacts({"text": "Acheter maintenant"})
    prepared = prepare_review_inputs(artifacts[0][0], artifacts[1][0])

    assert prepared.en_text == "Buy now"
    assert prepared.target_text == "Acheter maintenant"
    assert prepared.comparison_text_source == "dom"


def test_prepare_review_inputs_prefers_ocr_for_image_items_when_quality_good():
    artifacts = _base_artifacts(
        {
            "tag": "img",
            "element_type": "img",
            "text": "Texte DOM",
            "ocr_text": "Acheter maintenant",
            "ocr_notes": [],
        }
    )
    prepared = prepare_review_inputs(artifacts[0][0], artifacts[1][0])

    assert prepared.target_text == "Acheter maintenant"
    assert prepared.comparison_text_source == "ocr"


def test_prepare_review_inputs_applies_dynamic_counter_normalization():
    artifacts = _base_artifacts(
        {
            "text": "12 en ligne",
            "attributes": {"class": "header_online bc_flex bc_flex_items_center"},
        }
    )
    artifacts[0][0]["text"] = "11 online"
    artifacts[0][0]["attributes"] = {"class": "header_online bc_flex bc_flex_items_center"}
    prepared = prepare_review_inputs(artifacts[0][0], artifacts[1][0])

    assert prepared.en_text == "<NUM> online"
    assert prepared.target_text == "<NUM> en ligne"


class _PrefetchAwareProvider:
    def __init__(self):
        self.prefetched = set()
        self.misses = []

    def prefetch_reviews(self, pairs, language):
        self.prefetched.update((text_en, text_target, language) for text_en, text_target in pairs)

    def review_spelling_grammar(self, text_en, text_target, language, **kwargs):
        from pipeline.phase6_providers import SpellingGrammarSignals

        key = (text_en, text_target, language)
        if key not in self.prefetched:
            self.misses.append(key)
        return SpellingGrammarSignals(spelling_score=0.0, grammar_score=0.0, notes=[])

    def review_meaning(self, text_en, text_target, language, **kwargs):
        from pipeline.phase6_providers import MeaningSignals

        key = (text_en, text_target, language)
        if key not in self.prefetched:
            self.misses.append(key)
        return MeaningSignals(meaning_mismatch_score=0.0, notes=[])


def test_run_prefetch_warms_exact_finalized_pair_keys_for_reviews():
    artifacts = _base_artifacts(
        {
            "tag": "img",
            "element_type": "img",
            "text": "Texte DOM",
            "ocr_text": "OCR final text",
            "ocr_notes": [],
        }
    )
    provider = _PrefetchAwareProvider()

    with patch("pipeline.run_phase6.build_provider", return_value=provider), patch(
        "pipeline.run_phase6.read_json_artifact", side_effect=artifacts
    ), patch("pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]), patch(
        "pipeline.run_phase6.write_json_artifact"
    ), patch("pipeline.run_phase6.write_phase_manifest"):
        run("example.com", "run-en", "run-fr", review_mode="test-heuristic")

    assert provider.misses == []


def test_provider_notes_are_not_mixed_into_signals():
    artifacts = _base_artifacts({"text": "teh translation"})

    with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts), patch(
        "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
    ), patch("pipeline.run_phase6.write_json_artifact"), patch("pipeline.run_phase6.write_phase_manifest"):
        issues = run("example.com", "run-en", "run-fr", review_mode="test-heuristic")

    assert len(issues) >= 1
    spelling_issue = next(issue for issue in issues if issue["message"] == "Potential spelling issue in target text")
    assert "notes" not in spelling_issue["evidence"]["signals"]
    assert spelling_issue["evidence"]["provider_notes"] == ["spelling_marker_detected"]
    assert spelling_issue["evidence"]["provider_meta"]["review_mode"] == "test-heuristic"
    assert spelling_issue["evidence"]["provider_meta"]["confidence_provenance"] == "heuristic"
    assert spelling_issue["evidence"]["provider_meta"]["origin"] == "deterministic_offline"
    assert spelling_issue["evidence"]["review_mode"] == "test-heuristic"
    assert spelling_issue["evidence"]["confidence_provenance"] == "heuristic"


def test_fallback_weighted_pairing_reduces_false_missing_translation_on_item_id_drift():
    artifacts = _base_artifacts({"item_id": "item-fr-drifted", "text": "Buy now"})

    with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts), patch(
        "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
    ), patch("pipeline.run_phase6.write_json_artifact"), patch("pipeline.run_phase6.write_phase_manifest"):
        issues = run("example.com", "run-en", "run-fr", review_mode="test-heuristic")

    categories = [issue["category"] for issue in issues]
    assert "MISSING_TRANSLATION" not in categories
    assert len(issues) == 1
    meaning_issue = next(issue for issue in issues if issue["evidence"]["review_class"] == "MEANING")
    assert meaning_issue["evidence"]["pairing_basis"] == "fallback_weighted"
    assert meaning_issue["evidence"]["matched_target_item_id"] == "item-fr-drifted"
    assert "pairing_score_breakdown" in meaning_issue["evidence"]


def test_ai_mode_missing_key_falls_back_without_changing_category(monkeypatch):
    artifacts = _base_artifacts({"text": "teh translation"})

    monkeypatch.setenv("PHASE6_REVIEW_PROVIDER", "ai")
    monkeypatch.delenv("PHASE6_REVIEW_API_KEY", raising=False)

    with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts), patch(
        "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
    ), patch("pipeline.run_phase6.write_json_artifact"), patch("pipeline.run_phase6.write_phase_manifest"):
        issues = run("example.com", "run-en", "run-fr")

    spelling_issue = next(issue for issue in issues if issue["evidence"]["review_class"] == "SPELLING")
    assert spelling_issue["category"] == "TRANSLATION_MISMATCH"
    assert spelling_issue["evidence"]["provider_meta"]["provider"] == "llm"
    assert spelling_issue["evidence"]["provider_meta"]["review_mode"] == "llm"
    assert spelling_issue["evidence"]["provider_meta"]["fallback_used"] is True
    assert "fallback" in " ".join(spelling_issue["evidence"]["provider_notes"]).lower()


def test_llm_mode_missing_key_falls_back_without_changing_category(monkeypatch):
    # Backward-compatible alias for branches that renamed the provider-mode test.
    test_ai_mode_missing_key_falls_back_without_changing_category(monkeypatch)


def test_llm_mode_enriches_evidence_metadata_when_response_valid(monkeypatch):
    artifacts = _base_artifacts({"text": "Acheter"})

    def fake_request(endpoint, api_key, timeout_s, payload):
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"r":[[0,82,10,20,1]]}'
                    }
                }
            ]
        }

    monkeypatch.setenv("PHASE6_REVIEW_API_KEY", "test-key")

    with patch("pipeline.phase6_providers.LLMReviewProvider._default_request", side_effect=fake_request), patch(
        "pipeline.run_phase6.read_json_artifact", side_effect=artifacts
    ), patch("pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]), patch(
        "pipeline.run_phase6.write_json_artifact"
    ), patch("pipeline.run_phase6.write_phase_manifest"):
        issues = run("example.com", "run-en", "run-fr", review_mode="llm")

    spelling_issue = next(issue for issue in issues if issue["evidence"]["review_class"] == "SPELLING")
    assert spelling_issue["category"] == "TRANSLATION_MISMATCH"
    assert spelling_issue["evidence"]["provider_meta"]["model"] == "openrouter/free"
    assert spelling_issue["evidence"]["provider_meta"]["review_mode"] == "llm"
    assert spelling_issue["evidence"]["provider_meta"]["confidence_provenance"] == "llm"
    assert spelling_issue["evidence"]["provider_meta"]["fallback_used"] is False
    assert spelling_issue["evidence"]["review_mode"] == "llm"
    assert spelling_issue["evidence"]["confidence_provenance"] == "llm"
    assert spelling_issue["evidence"]["provider_meta"]["provider_score_summary"] == {
        "spelling_score": 0.82,
        "grammar_score": 0.1,
        "meaning_mismatch_score": 0.2,
    }
    assert spelling_issue["evidence"]["provider_notes"] == ["spell"]


class _HighMeaningProvider:
    def review_spelling_grammar(self, text_en, text_target, language, **kwargs):
        from pipeline.phase6_providers import SpellingGrammarSignals

        return SpellingGrammarSignals(spelling_score=0.0, grammar_score=0.0, notes=[])

    def review_meaning(self, text_en, text_target, language, **kwargs):
        from pipeline.phase6_providers import MeaningSignals

        return MeaningSignals(meaning_mismatch_score=0.92, notes=["forced_mismatch"])


def test_good_ocr_allows_normal_meaning_review_for_image_items():
    artifacts = _base_artifacts(
        {
            "tag": "img",
            "element_type": "img",
            "ocr_text": "Acheter maintenant",
            "ocr_notes": [],
            "text": "Buy now",
        }
    )

    with patch("pipeline.run_phase6.build_provider", return_value=_HighMeaningProvider()), patch(
        "pipeline.run_phase6.read_json_artifact", side_effect=artifacts
    ), patch("pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]), patch(
        "pipeline.run_phase6.write_json_artifact"
    ), patch("pipeline.run_phase6.write_phase_manifest"):
        issues = run("example.com", "run-en", "run-fr", review_mode="test-heuristic")

    meaning_issue = next(issue for issue in issues if issue["evidence"]["review_class"] == "MEANING")
    assert meaning_issue["category"] == "TRANSLATION_MISMATCH"
    assert "ocr_confidence_adjustment" in meaning_issue["evidence"]["signals"]
    assert meaning_issue["evidence"]["signals"]["ocr_confidence_adjustment"] == 0.0
    assert meaning_issue["evidence"]["text_target"] == "Acheter maintenant"
    assert meaning_issue["evidence"]["comparison_text_source"] == "ocr"


def test_weak_ocr_suppresses_strong_meaning_claims_and_adds_quality_evidence():
    artifacts = _base_artifacts(
        {
            "tag": "img",
            "element_type": "img",
            "ocr_text": "!!! $$$$ ----",
            "ocr_notes": ["uncertain parse"],
            "text": "Acheter",
        }
    )

    with patch("pipeline.run_phase6.build_provider", return_value=_HighMeaningProvider()), patch(
        "pipeline.run_phase6.read_json_artifact", side_effect=artifacts
    ), patch("pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]), patch(
        "pipeline.run_phase6.write_json_artifact"
    ), patch("pipeline.run_phase6.write_phase_manifest"):
        issues = run("example.com", "run-en", "run-fr", review_mode="test-heuristic")

    assert not any(issue for issue in issues if issue["evidence"]["review_class"] == "MEANING")
    ocr_issue = next(issue for issue in issues if issue["evidence"]["review_class"] == "OCR_NOISE")
    assert ocr_issue["category"] == "FORMATTING_MISMATCH"
    assert ocr_issue["evidence"]["ocr_quality"]["trust_bucket"] == "weak"
    assert ocr_issue["evidence"]["ocr_quality"]["flags"]
    assert "ocr_symbol_ratio" in ocr_issue["evidence"]["signals"]


def test_nearly_empty_ocr_text_is_treated_as_weak_quality_noise():
    artifacts = _base_artifacts({"tag": "img", "element_type": "img", "ocr_text": " ", "text": "Acheter"})

    with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts), patch(
        "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
    ), patch("pipeline.run_phase6.write_json_artifact"), patch("pipeline.run_phase6.write_phase_manifest"):
        issues = run("example.com", "run-en", "run-fr", review_mode="test-heuristic")

    ocr_issue = next(issue for issue in issues if issue["evidence"]["review_class"] == "OCR_NOISE")
    assert ocr_issue["evidence"]["ocr_quality"]["trust_bucket"] == "weak"
    assert "ocr_missing_text" in ocr_issue["evidence"]["ocr_quality"]["flags"]


def test_run_fails_fast_when_explicit_review_mode_required_and_omitted():
    artifacts = _base_artifacts()

    with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts), patch(
        "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
    ), patch("pipeline.run_phase6.write_json_artifact"), patch("pipeline.run_phase6.write_phase_manifest"), patch.dict(
        "os.environ", {}, clear=True
    ), pytest.raises(ValueError, match="must be set explicitly"):
        run("example.com", "run-en", "run-fr", require_explicit_mode=True)


def test_phase6_writes_coverage_gaps_artifact_for_unreviewed_image_items():
    artifacts = _base_artifacts({"tag": "img", "element_type": "img", "text": "Acheter"})
    captured = {}

    def _capture_write(domain, run_id, filename, payload):
        captured[filename] = payload
        return "gs://bucket/" + filename

    with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts), patch(
        "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
    ), patch("pipeline.run_phase6.write_json_artifact", side_effect=_capture_write), patch("pipeline.run_phase6.write_phase_manifest"):
        run("example.com", "run-en", "run-fr", review_mode="test-heuristic")

    assert "coverage_gaps.json" in captured
    gaps = captured["coverage_gaps.json"]
    assert len(gaps) == 1
    assert gaps[0]["image_text_review_status"] == "image_text_not_reviewed"


def test_phase6_coverage_gap_marks_blocked_image_items_separately():
    artifacts = _base_artifacts({"tag": "img", "element_type": "img", "text": "Acheter"})
    captured = {}

    def _capture_write(domain, run_id, filename, payload):
        captured[filename] = payload
        return "gs://bucket/" + filename

    blocked = [{"capture_context_id": "ctx-1", "url": "https://example.com/fr/p", "storage_uri": "gs://b/fr.png"}]
    with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts), patch(
        "pipeline.run_phase6._load_blocked_overlay_pages", return_value=blocked
    ), patch("pipeline.run_phase6.write_json_artifact", side_effect=_capture_write), patch("pipeline.run_phase6.write_phase_manifest"):
        run("example.com", "run-en", "run-fr", review_mode="test-heuristic")

    gaps = captured["coverage_gaps.json"]
    assert gaps[0]["image_text_review_status"] == "image_text_review_blocked"


def test_run_phase6_persists_llm_review_stats_artifact():
    artifacts = _base_artifacts({"text": "Acheter"})
    captured = {}

    class _Provider:
        def review_spelling_grammar(self, text_en, text_target, language, **kwargs):
            from pipeline.phase6_providers import SpellingGrammarSignals
            return SpellingGrammarSignals(spelling_score=0.0, grammar_score=0.0, notes=[])

        def review_meaning(self, text_en, text_target, language, **kwargs):
            from pipeline.phase6_providers import MeaningSignals
            return MeaningSignals(meaning_mismatch_score=0.0, notes=[])

        def get_llm_review_stats(self):
            return {
                "review_mode": "llm",
                "provider_type": "llm",
                "configured_provider": "llm",
                "configured_model": "m",
                "effective_model": "m",
                "llm_requested": True,
                "llm_batches_attempted": 1,
                "llm_batches_succeeded": 1,
                "llm_batches_failed": 0,
                "fallback_batches": 0,
                "fallback_items": 0,
                "llm_items_requested": 1,
                "llm_items_completed": 1,
                "estimated_prompt_tokens": 1,
                "estimated_completion_tokens": 1,
                "estimated_total_tokens": 2,
                "actual_prompt_tokens": 1,
                "actual_completion_tokens": 1,
                "actual_total_tokens": 2,
                "estimated_cost_usd": None,
                "actual_cost_usd": None,
                "currency": "USD",
                "responses_received": 1,
                "transport_failures": 0,
                "parse_failures": 0,
                "provider_failures": 0,
                "used_fallback": False,
                "fallback_reason_summary": [],
                "batches": [],
            }

    def _capture_write(domain, run_id, filename, payload):
        captured[filename] = payload
        return "gs://bucket/" + filename

    with patch("pipeline.run_phase6.build_provider", return_value=_Provider()), patch(
        "pipeline.run_phase6.read_json_artifact", side_effect=artifacts
    ), patch("pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]), patch(
        "pipeline.run_phase6.write_json_artifact", side_effect=_capture_write
    ), patch("pipeline.run_phase6.write_phase_manifest"):
        run("example.com", "run-en", "run-fr", review_mode="llm")

    assert "llm_review_stats.json" in captured
    assert captured["llm_review_stats.json"]["llm_requested"] is True


def test_heuristic_mode_writes_llm_stats_with_llm_requested_false():
    artifacts = _base_artifacts({"text": "Acheter"})
    captured = {}

    def _capture_write(domain, run_id, filename, payload):
        captured[filename] = payload
        return "gs://bucket/" + filename

    with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts), patch(
        "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
    ), patch("pipeline.run_phase6.write_json_artifact", side_effect=_capture_write), patch("pipeline.run_phase6.write_phase_manifest"):
        run("example.com", "run-en", "run-fr", review_mode="test-heuristic")

    assert captured["llm_review_stats.json"]["review_mode"] == "test-heuristic"
    assert captured["llm_review_stats.json"]["llm_requested"] is False


def test_phase6_wires_llm_request_artifact_writer_and_manifest_uri():
    artifacts = _base_artifacts({"text": "Acheter"})
    captured = {}
    manifest = {}

    class _Provider:
        def __init__(self, artifact_writer):
            self._artifact_writer = artifact_writer

        def prefetch_reviews(self, rows, language):
            self._artifact_writer(
                "check_languages_llm_request.json",
                {"model": "m", "messages": [{"role": "system"}, {"role": "user"}]},
            )

        def review_spelling_grammar(self, text_en, text_target, language, **kwargs):
            from pipeline.phase6_providers import SpellingGrammarSignals

            return SpellingGrammarSignals(spelling_score=0.0, grammar_score=0.0, notes=[])

        def review_meaning(self, text_en, text_target, language, **kwargs):
            from pipeline.phase6_providers import MeaningSignals

            return MeaningSignals(meaning_mismatch_score=0.0, notes=[])

        def get_llm_review_stats(self):
            return {"review_mode": "llm", "llm_requested": True}

    def _fake_build_provider(mode, **provider_kwargs):
        return _Provider(provider_kwargs["artifact_writer"])

    def _capture_write(domain, run_id, filename, payload):
        captured[filename] = payload
        return "gs://bucket/" + filename

    def _capture_manifest(domain, run_id, phase, payload):
        manifest["payload"] = payload

    with patch("pipeline.run_phase6.build_provider", side_effect=_fake_build_provider), patch(
        "pipeline.run_phase6.read_json_artifact", side_effect=artifacts
    ), patch("pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]), patch(
        "pipeline.run_phase6.write_json_artifact", side_effect=_capture_write
    ), patch("pipeline.run_phase6.write_phase_manifest", side_effect=_capture_manifest):
        run("example.com", "run-en", "run-fr", review_mode="llm")

    assert "check_languages_llm_request.json" in captured
    assert any(uri.endswith("/example.com/run-fr/check_languages_llm_request.json") for uri in manifest["payload"]["artifact_uris"])


def test_phase6_manifest_omits_llm_request_artifact_for_non_llm_mode():
    artifacts = _base_artifacts({"text": "Acheter"})
    manifest = {}

    def _capture_manifest(domain, run_id, phase, payload):
        manifest["payload"] = payload

    with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts), patch(
        "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
    ), patch("pipeline.run_phase6.write_json_artifact"), patch(
        "pipeline.run_phase6.write_phase_manifest", side_effect=_capture_manifest
    ):
        run("example.com", "run-en", "run-fr", review_mode="test-heuristic")

    assert not any(uri.endswith("/example.com/run-fr/check_languages_llm_request.json") for uri in manifest["payload"]["artifact_uris"])


def test_phase6_manifest_omits_llm_request_artifact_when_not_written():
    artifacts = _base_artifacts({"text": "Acheter"})
    manifest = {}

    class _Provider:
        def prefetch_reviews(self, rows, language):
            return None

        def review_spelling_grammar(self, text_en, text_target, language, **kwargs):
            from pipeline.phase6_providers import SpellingGrammarSignals

            return SpellingGrammarSignals(spelling_score=0.0, grammar_score=0.0, notes=[])

        def review_meaning(self, text_en, text_target, language, **kwargs):
            from pipeline.phase6_providers import MeaningSignals

            return MeaningSignals(meaning_mismatch_score=0.0, notes=[])

        def get_llm_review_stats(self):
            return {"review_mode": "llm", "llm_requested": True}

    def _capture_manifest(domain, run_id, phase, payload):
        manifest["payload"] = payload

    with patch("pipeline.run_phase6.build_provider", return_value=_Provider()), patch(
        "pipeline.run_phase6.read_json_artifact", side_effect=artifacts
    ), patch("pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]), patch(
        "pipeline.run_phase6.write_json_artifact"
    ), patch("pipeline.run_phase6.write_phase_manifest", side_effect=_capture_manifest):
        run("example.com", "run-en", "run-fr", review_mode="llm")

    assert not any(uri.endswith("/example.com/run-fr/check_languages_llm_request.json") for uri in manifest["payload"]["artifact_uris"])
