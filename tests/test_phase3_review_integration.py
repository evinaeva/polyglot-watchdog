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
        ), patch("pipeline.run_phase3.write_json_artifact"), patch("pipeline.run_phase3.write_text_artifact"):
            eligible = run("example.com", "run-1")

        self.assertEqual(eligible, [])


if __name__ == "__main__":
    unittest.main()
