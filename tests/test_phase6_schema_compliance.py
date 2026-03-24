import unittest
from unittest.mock import patch

from pipeline.run_phase6 import run
from pipeline.schema_validator import SchemaValidationError


class Phase6SchemaComplianceTests(unittest.TestCase):
    def _artifacts(self):
        en_eligible = [
            {
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
        ]
        target_eligible = []
        en_collected = [
            {
                "item_id": "item-1",
                "page_id": "en-page-1",
                "bbox": {"x": 1, "y": 2, "width": 3, "height": 4},
            }
        ]
        target_collected = []
        en_screens = [{"page_id": "en-page-1", "storage_uri": "gs://b/en.png"}]
        target_screens = []
        return [en_eligible, target_eligible, en_collected, target_collected, en_screens, target_screens]

    def test_phase6_uses_schema_approved_categories(self):
        artifacts = self._artifacts()

        with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts + [FileNotFoundError("missing")]), patch(
            "pipeline.run_phase6.write_json_artifact"
        ) as write_mock, patch("pipeline.run_phase6.write_phase_manifest") as manifest_mock:
            issues = run("example.com", "run-en", "run-fr")

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["category"], "MISSING_TRANSLATION")
        self.assertEqual(issues[0]["evidence"]["review_class"], "OTHER")
        self.assertIn("signals", issues[0]["evidence"])
        write_mock.assert_called_once()
        manifest_mock.assert_called_once()

    def test_phase6_does_not_persist_when_schema_invalid(self):
        artifacts = self._artifacts()

        with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts + [FileNotFoundError("missing")]), patch(
            "pipeline.run_phase6.validate", side_effect=SchemaValidationError("STOP: invalid")
        ), patch("pipeline.run_phase6.write_json_artifact") as write_mock, self.assertRaises(SystemExit):
            run("example.com", "run-en", "run-fr")

        write_mock.assert_not_called()

    def test_phase6_emits_overlay_blocked_capture_issue_when_review_marks_blocked(self):
        en_eligible, target_eligible, en_collected, target_collected, en_screens, target_screens = self._artifacts()
        target_eligible = [
            {
                "item_id": "item-1",
                "page_id": "fr-page-1",
                "url": "https://fr.example.com/p",
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
        ]
        target_collected = [{"item_id": "item-1", "page_id": "fr-page-1", "bbox": {"x": 1, "y": 2, "width": 3, "height": 4}}]
        target_screens = [{"page_id": "fr-page-1", "url": "https://fr.example.com/p", "viewport_kind": "desktop", "state": "baseline", "user_tier": "guest", "storage_uri": "gs://b/fr.png"}]

        artifacts = [en_eligible, target_eligible, en_collected, target_collected, en_screens, target_screens]
        with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts + [FileNotFoundError("missing")]), patch(
            "pipeline.run_phase6._load_blocked_overlay_pages",
            return_value=[{"capture_context_id": "ctx-1", "url": "https://fr.example.com/p", "storage_uri": "gs://b/fr.png"}],
        ), patch("pipeline.run_phase6.write_json_artifact"), patch("pipeline.run_phase6.write_phase_manifest"):
            issues = run("example.com", "run-en", "run-fr")

        categories = {issue["category"] for issue in issues}
        self.assertIn("OVERLAY_BLOCKED_CAPTURE", categories)
        overlay_issue = next(issue for issue in issues if issue["category"] == "OVERLAY_BLOCKED_CAPTURE")
        self.assertEqual(overlay_issue["evidence"]["review_class"], "OTHER")

    def test_phase6_preserves_contract_category_when_review_class_is_detailed(self):
        en_eligible, target_eligible, en_collected, target_collected, en_screens, target_screens = self._artifacts()
        target_eligible = [
            {
                "item_id": "item-1",
                "page_id": "fr-page-1",
                "url": "https://fr.example.com/p",
                "language": "fr",
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
        ]
        target_collected = [{"item_id": "item-1", "page_id": "fr-page-1", "bbox": {"x": 1, "y": 2, "width": 3, "height": 4}}]
        target_screens = [{"page_id": "fr-page-1", "url": "https://fr.example.com/p", "viewport_kind": "desktop", "state": "baseline", "user_tier": "guest", "storage_uri": "gs://b/fr.png"}]

        artifacts = [en_eligible, target_eligible, en_collected, target_collected, en_screens, target_screens]
        with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts + [FileNotFoundError("missing")]), patch(
            "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
        ), patch("pipeline.run_phase6.write_json_artifact"), patch("pipeline.run_phase6.write_phase_manifest"):
            issues = run("example.com", "run-en", "run-fr")

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["category"], "TRANSLATION_MISMATCH")
        self.assertEqual(issues[0]["evidence"]["review_class"], "MEANING")

    def test_phase6_skips_untranslated_issue_for_header_online_dynamic_numbers(self):
        en_eligible = [
            {
                "item_id": "item-dyn",
                "page_id": "en-page-dyn",
                "url": "https://example.com/p",
                "language": "en",
                "viewport_kind": "desktop",
                "state": "baseline",
                "user_tier": "guest",
                "element_type": "div",
                "css_selector": ".header_online.bc_flex.bc_flex_items_center",
                "bbox": {"x": 1, "y": 2, "width": 3, "height": 4},
                "text": "Online 123",
                "visible": True,
                "tag": "div",
                "attributes": {"class": "header_online bc_flex bc_flex_items_center"},
            }
        ]
        target_eligible = [
            {
                "item_id": "item-dyn",
                "page_id": "fr-page-dyn",
                "url": "https://example.com/fr/p",
                "language": "fr",
                "viewport_kind": "desktop",
                "state": "baseline",
                "user_tier": "guest",
                "element_type": "div",
                "css_selector": ".header_online.bc_flex.bc_flex_items_center",
                "bbox": {"x": 1, "y": 2, "width": 3, "height": 4},
                "text": "Online 456",
                "visible": True,
                "tag": "div",
                "attributes": {"class": "header_online bc_flex bc_flex_items_center"},
            }
        ]
        en_collected = [{"item_id": "item-dyn", "page_id": "en-page-dyn", "bbox": {"x": 1, "y": 2, "width": 3, "height": 4}}]
        target_collected = [{"item_id": "item-dyn", "page_id": "fr-page-dyn", "bbox": {"x": 1, "y": 2, "width": 3, "height": 4}}]
        en_screens = [{"page_id": "en-page-dyn", "storage_uri": "gs://b/en-dyn.png"}]
        target_screens = [{"page_id": "fr-page-dyn", "storage_uri": "gs://b/fr-dyn.png"}]

        artifacts = [en_eligible, target_eligible, en_collected, target_collected, en_screens, target_screens]
        with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts + [FileNotFoundError("missing")]), patch(
            "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
        ), patch("pipeline.run_phase6.write_json_artifact"
        ), patch("pipeline.run_phase6.write_phase_manifest"):
            issues = run("example.com", "run-en", "run-fr")

        assert [issue["category"] for issue in issues] == []

    def test_phase6_skips_untranslated_issue_when_dynamic_classes_are_split_across_en_and_target(self):
        en_eligible = [
            {
                "item_id": "item-dyn-split",
                "page_id": "en-page-dyn",
                "url": "https://example.com/p",
                "language": "en",
                "viewport_kind": "desktop",
                "state": "baseline",
                "user_tier": "guest",
                "element_type": "div",
                "css_selector": ".header_online.bc_flex",
                "bbox": {"x": 1, "y": 2, "width": 3, "height": 4},
                "text": "Online 123",
                "visible": True,
                "tag": "div",
                "attributes": {"class": "header_online bc_flex"},
            }
        ]
        target_eligible = [
            {
                "item_id": "item-dyn-split",
                "page_id": "fr-page-dyn",
                "url": "https://example.com/fr/p",
                "language": "fr",
                "viewport_kind": "desktop",
                "state": "baseline",
                "user_tier": "guest",
                "element_type": "div",
                "css_selector": ".bc_flex_items_center",
                "bbox": {"x": 1, "y": 2, "width": 3, "height": 4},
                "text": "Online 456",
                "visible": True,
                "tag": "div",
                "attributes": {"class": "bc_flex_items_center"},
            }
        ]
        en_collected = [{"item_id": "item-dyn-split", "page_id": "en-page-dyn", "bbox": {"x": 1, "y": 2, "width": 3, "height": 4}}]
        target_collected = [{"item_id": "item-dyn-split", "page_id": "fr-page-dyn", "bbox": {"x": 1, "y": 2, "width": 3, "height": 4}}]
        en_screens = [{"page_id": "en-page-dyn", "storage_uri": "gs://b/en-dyn.png"}]
        target_screens = [{"page_id": "fr-page-dyn", "storage_uri": "gs://b/fr-dyn.png"}]

        artifacts = [en_eligible, target_eligible, en_collected, target_collected, en_screens, target_screens]
        with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts + [FileNotFoundError("missing")]), patch(
            "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
        ), patch("pipeline.run_phase6.write_json_artifact"
        ), patch("pipeline.run_phase6.write_phase_manifest"):
            issues = run("example.com", "run-en", "run-fr")

        assert [issue["category"] for issue in issues] == []

    def test_phase6_schema_accepts_comparison_text_source_in_evidence(self):
        en_eligible, target_eligible, en_collected, target_collected, en_screens, target_screens = self._artifacts()
        target_eligible = [
            {
                "item_id": "item-1",
                "page_id": "fr-page-1",
                "url": "https://fr.example.com/p",
                "language": "fr",
                "viewport_kind": "desktop",
                "state": "baseline",
                "user_tier": "guest",
                "element_type": "img",
                "css_selector": "main > img",
                "bbox": {"x": 1, "y": 2, "width": 3, "height": 4},
                "text": "Texte DOM non fiable",
                "visible": True,
                "tag": "img",
                "attributes": None,
                "ocr_text": "teh translation",
                "ocr_notes": [],
            }
        ]
        target_collected = [{"item_id": "item-1", "page_id": "fr-page-1", "bbox": {"x": 1, "y": 2, "width": 3, "height": 4}}]
        target_screens = [{"page_id": "fr-page-1", "url": "https://fr.example.com/p", "viewport_kind": "desktop", "state": "baseline", "user_tier": "guest", "storage_uri": "gs://b/fr.png"}]

        artifacts = [en_eligible, target_eligible, en_collected, target_collected, en_screens, target_screens]
        with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts + [FileNotFoundError("missing")]), patch(
            "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
        ), patch("pipeline.run_phase6.write_json_artifact"), patch("pipeline.run_phase6.write_phase_manifest"):
            issues = run("example.com", "run-en", "run-fr")

        spelling_issue = next(issue for issue in issues if issue["evidence"]["review_class"] == "SPELLING")
        self.assertEqual(spelling_issue["evidence"]["comparison_text_source"], "ocr")

    def test_phase6_weighted_fallback_avoids_false_missing_translation_when_item_id_drifted(self):
        en_eligible, _, en_collected, _, en_screens, _ = self._artifacts()
        target_eligible = [
            {
                "item_id": "target-drift-1",
                "page_id": "fr-page-1",
                "url": "https://fr.example.com/p",
                "language": "fr",
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
        ]
        target_collected = [{"item_id": "target-drift-1", "page_id": "fr-page-1", "bbox": {"x": 1, "y": 2, "width": 3, "height": 4}}]
        target_screens = [{"page_id": "fr-page-1", "url": "https://fr.example.com/p", "viewport_kind": "desktop", "state": "baseline", "user_tier": "guest", "storage_uri": "gs://b/fr.png"}]
        artifacts = [en_eligible, target_eligible, en_collected, target_collected, en_screens, target_screens]

        with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts + [FileNotFoundError("missing")]), patch(
            "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
        ), patch("pipeline.run_phase6.write_json_artifact"), patch("pipeline.run_phase6.write_phase_manifest"):
            issues = run("example.com", "run-en", "run-fr")

        self.assertNotIn("MISSING_TRANSLATION", [issue["category"] for issue in issues])
        meaning_issue = next(issue for issue in issues if issue["evidence"]["review_class"] == "MEANING")
        self.assertEqual(meaning_issue["evidence"]["pairing_basis"], "fallback_weighted")
        self.assertEqual(meaning_issue["evidence"]["matched_target_item_id"], "target-drift-1")

    def test_phase6_ambiguous_fallback_keeps_missing_translation_and_records_provenance(self):
        en_eligible, _, en_collected, _, en_screens, _ = self._artifacts()
        target_eligible = [
            {
                "item_id": "target-a",
                "page_id": "fr-page-1",
                "url": "https://fr.example.com/p",
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
            },
            {
                "item_id": "target-b",
                "page_id": "fr-page-2",
                "url": "https://fr.example.com/p2",
                "language": "fr",
                "viewport_kind": "desktop",
                "state": "baseline",
                "user_tier": "guest",
                "element_type": "p",
                "css_selector": "main > p",
                "bbox": {"x": 5, "y": 6, "width": 7, "height": 8},
                "text": "Acheter",
                "visible": True,
                "tag": "p",
                "attributes": None,
            },
        ]
        target_collected = [
            {"item_id": "target-a", "page_id": "fr-page-1", "bbox": {"x": 1, "y": 2, "width": 3, "height": 4}},
            {"item_id": "target-b", "page_id": "fr-page-2", "bbox": {"x": 5, "y": 6, "width": 7, "height": 8}},
        ]
        target_screens = [
            {"page_id": "fr-page-1", "url": "https://fr.example.com/p", "viewport_kind": "desktop", "state": "baseline", "user_tier": "guest", "storage_uri": "gs://b/fr1.png"},
            {"page_id": "fr-page-2", "url": "https://fr.example.com/p2", "viewport_kind": "desktop", "state": "baseline", "user_tier": "guest", "storage_uri": "gs://b/fr2.png"},
        ]
        artifacts = [en_eligible, target_eligible, en_collected, target_collected, en_screens, target_screens]

        with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts + [FileNotFoundError("missing")]), patch(
            "pipeline.run_phase6._load_blocked_overlay_pages", return_value=[]
        ), patch("pipeline.run_phase6.write_json_artifact"), patch("pipeline.run_phase6.write_phase_manifest"):
            issues = run("example.com", "run-en", "run-fr")

        self.assertIn("MISSING_TRANSLATION", [issue["category"] for issue in issues])
        missing_issue = next(issue for issue in issues if issue["category"] == "MISSING_TRANSLATION")
        self.assertEqual(missing_issue["evidence"]["pairing_basis"], "fallback_ambiguous")
        self.assertIn("pairing_score_breakdown", missing_issue["evidence"])


if __name__ == "__main__":
    unittest.main()
