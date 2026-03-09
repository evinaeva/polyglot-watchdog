import unittest
from unittest.mock import patch

from pipeline.run_phase3 import run


class Phase3ReviewIntegrationTests(unittest.TestCase):
    def test_blocked_overlay_contexts_are_excluded_before_rules(self):
        collected_items = [
            {
                "item_id": "i-1",
                "page_id": "p-1",
                "url": "https://example.com/p",
                "language": "en",
                "element_type": "p",
                "text": "Hello",
            }
        ]
        page_screenshots = [
            {
                "page_id": "p-1",
                "url": "https://example.com/p",
                "viewport_kind": "desktop",
                "state": "baseline",
                "user_tier": "guest",
            }
        ]
        template_rules = []

        with patch(
            "pipeline.run_phase3.read_json_artifact",
            side_effect=[collected_items, page_screenshots, template_rules],
        ), patch(
            "pipeline.run_phase3._load_review_statuses",
            return_value=[{"capture_context_id": "ctx", "status": "blocked_by_overlay"}],
        ), patch("pipeline.run_phase3.build_eligible_dataset", return_value=[]), patch(
            "pipeline.run_phase3.validate"
        ), patch("pipeline.run_phase3.write_json_artifact"), patch("pipeline.run_phase3.write_text_artifact"), patch(
            "pipeline.run_phase3.write_phase_manifest"
        ) as manifest_mock:
            eligible = run("example.com", "run-1")

        self.assertEqual(eligible, [])
        manifest_mock.assert_called_once()

    def test_universal_sections_are_included_in_eligible_dataset(self):
        collected_items = [
            {"item_id": "i-1", "page_id": "p-1", "url": "https://example.com/p", "language": "en", "element_type": "p", "text": "Hello"}
        ]
        page_screenshots = [{"page_id": "p-1", "url": "https://example.com/p", "viewport_kind": "desktop", "state": "baseline", "user_tier": "guest"}]
        universal_sections = [{"section_id": "sec-1", "fingerprint": "fp1", "representative_url": "https://example.com/p", "representative_page_id": "p-1", "label": "universal_section", "member_urls_count": 2, "member_urls": ["https://example.com/p", "https://example.com/q"], "created_at": "2026-01-01T00:00:00Z"}]

        with patch("pipeline.run_phase3.read_json_artifact", side_effect=[collected_items, page_screenshots, universal_sections, []]), patch(
            "pipeline.run_phase3._load_review_statuses", return_value=[]
        ), patch("pipeline.run_phase3.validate"), patch("pipeline.run_phase3.write_json_artifact"), patch(
            "pipeline.run_phase3.write_text_artifact"
        ), patch("pipeline.run_phase3.write_phase_manifest"):
            eligible = run("example.com", "run-2")

        universal_rows = [row for row in eligible if str(row.get("item_id", "")).startswith("universal-")]
        self.assertEqual(len(universal_rows), 1)
        self.assertEqual(universal_rows[0]["url"], "https://example.com/p")


if __name__ == "__main__":
    unittest.main()
