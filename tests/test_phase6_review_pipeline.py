from unittest.mock import patch

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
        issues = run("example.com", "run-en", "run-fr")

    assert len(issues) == 1
    issue = issues[0]
    assert issue["category"] == "FORMATTING_MISMATCH"
    assert issue["evidence"]["review_class"] == "PLACEHOLDER"
    assert issue["evidence"]["reason"]
    assert "signals" in issue["evidence"]
    assert issue["evidence"]["pairing_basis"] == "item_id"
    assert issue["evidence"]["text_en"] == "Buy now <name>"
    assert issue["evidence"]["text_target"] == "Acheter %s"


def test_ocr_metadata_applies_only_to_image_items():
    artifacts = _base_artifacts({"tag": "img", "element_type": "img", "ocr_text": "X", "text": "Acheter"})

    with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts), patch(
        "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
    ), patch("pipeline.run_phase6.write_json_artifact"), patch("pipeline.run_phase6.write_phase_manifest"):
        issues = run("example.com", "run-en", "run-fr")

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
        issues = run("example.com", "run-en", "run-fr")

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
        issues = run("example.com", "run-en", "run-fr")

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
        issues = run("example.com", "run-en", "run-fr")

    spelling_issue = next(issue for issue in issues if issue["evidence"]["review_class"] == "SPELLING")
    assert spelling_issue["evidence"]["text_target"] == "teh translation"
    assert spelling_issue["evidence"]["comparison_text_source"] == "dom"


def test_non_image_items_do_not_receive_ocr_signals():
    artifacts = _base_artifacts({"ocr_text": "X", "text": "Acheter"})

    with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts), patch(
        "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
    ), patch("pipeline.run_phase6.write_json_artifact"), patch("pipeline.run_phase6.write_phase_manifest"):
        issues = run("example.com", "run-en", "run-fr")

    assert issues == []


def test_provider_disabled_mode_is_deterministic_and_offline():
    artifacts = _base_artifacts({"text": "teh translation"})

    with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts), patch(
        "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
    ), patch("pipeline.run_phase6.write_json_artifact"), patch("pipeline.run_phase6.write_phase_manifest"), patch.dict(
        "os.environ", {"PHASE6_REVIEW_PROVIDER": "disabled"}, clear=False
    ):
        issues = run("example.com", "run-en", "run-fr")

    assert issues == []


def test_confidence_and_ordering_are_deterministic():
    artifacts = _base_artifacts({"text": "Buy now"})

    with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts), patch(
        "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
    ), patch("pipeline.run_phase6.write_json_artifact"), patch("pipeline.run_phase6.write_phase_manifest"):
        first = run("example.com", "run-en", "run-fr")

    with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts), patch(
        "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
    ), patch("pipeline.run_phase6.write_json_artifact"), patch("pipeline.run_phase6.write_phase_manifest"):
        second = run("example.com", "run-en", "run-fr")

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
        issues = run("example.com", "run-en", "run-fr")

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

    def review_spelling_grammar(self, text_en, text_target, language):
        from pipeline.phase6_providers import SpellingGrammarSignals

        key = (text_en, text_target, language)
        if key not in self.prefetched:
            self.misses.append(key)
        return SpellingGrammarSignals(spelling_score=0.0, grammar_score=0.0, notes=[])

    def review_meaning(self, text_en, text_target, language):
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
        run("example.com", "run-en", "run-fr")

    assert provider.misses == []


def test_provider_notes_are_not_mixed_into_signals():
    artifacts = _base_artifacts({"text": "teh translation"})

    with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts), patch(
        "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
    ), patch("pipeline.run_phase6.write_json_artifact"), patch("pipeline.run_phase6.write_phase_manifest"):
        issues = run("example.com", "run-en", "run-fr")

    assert len(issues) >= 1
    spelling_issue = next(issue for issue in issues if issue["message"] == "Potential spelling issue in target text")
    assert "notes" not in spelling_issue["evidence"]["signals"]
    assert spelling_issue["evidence"]["provider_notes"] == ["spelling_marker_detected"]


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
    assert spelling_issue["evidence"]["provider_meta"]["mode"] == "ai"
    assert spelling_issue["evidence"]["provider_meta"]["fallback_used"] is True
    assert "ai_fallback_used" in spelling_issue["evidence"]["provider_notes"]


def test_ai_mode_enriches_evidence_metadata_when_response_valid(monkeypatch):
    artifacts = _base_artifacts({"text": "Acheter"})

    def fake_request(endpoint, api_key, timeout_s, payload):
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"results": [{"item_id": "item_0", "spelling_score": 0.82, "grammar_score": 0.1, "meaning_mismatch_score": 0.2, "notes": ["possible typo", "uncertain due to short text"]}]}'
                    }
                }
            ]
        }

    monkeypatch.setenv("PHASE6_REVIEW_PROVIDER", "ai")
    monkeypatch.setenv("PHASE6_REVIEW_API_KEY", "test-key")

    with patch("pipeline.phase6_providers.LLMReviewProvider._default_request", side_effect=fake_request), patch(
        "pipeline.run_phase6.read_json_artifact", side_effect=artifacts
    ), patch("pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]), patch(
        "pipeline.run_phase6.write_json_artifact"
    ), patch("pipeline.run_phase6.write_phase_manifest"):
        issues = run("example.com", "run-en", "run-fr")

    spelling_issue = next(issue for issue in issues if issue["evidence"]["review_class"] == "SPELLING")
    assert spelling_issue["category"] == "TRANSLATION_MISMATCH"
    assert spelling_issue["evidence"]["provider_meta"]["model"] == "openrouter/free"
    assert spelling_issue["evidence"]["provider_meta"]["fallback_used"] is False
    assert spelling_issue["evidence"]["provider_meta"]["provider_score_summary"] == {
        "spelling_score": 0.82,
        "grammar_score": 0.1,
        "meaning_mismatch_score": 0.2,
    }
    assert spelling_issue["evidence"]["provider_notes"] == ["possible typo", "uncertain due to short text"]


class _HighMeaningProvider:
    def review_spelling_grammar(self, text_en, text_target, language):
        from pipeline.phase6_providers import SpellingGrammarSignals

        return SpellingGrammarSignals(spelling_score=0.0, grammar_score=0.0, notes=[])

    def review_meaning(self, text_en, text_target, language):
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
        issues = run("example.com", "run-en", "run-fr")

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
        issues = run("example.com", "run-en", "run-fr")

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
        issues = run("example.com", "run-en", "run-fr")

    ocr_issue = next(issue for issue in issues if issue["evidence"]["review_class"] == "OCR_NOISE")
    assert ocr_issue["evidence"]["ocr_quality"]["trust_bucket"] == "weak"
    assert "ocr_missing_text" in ocr_issue["evidence"]["ocr_quality"]["flags"]
