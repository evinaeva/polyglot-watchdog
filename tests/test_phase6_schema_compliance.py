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

        with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts), patch(
            "pipeline.run_phase6.write_json_artifact"
        ) as write_mock:
            issues = run("example.com", "run-en", "run-fr")

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["category"], "MISSING_TRANSLATION")
        write_mock.assert_called_once()

    def test_phase6_does_not_persist_when_schema_invalid(self):
        artifacts = self._artifacts()

        with patch("pipeline.run_phase6.read_json_artifact", side_effect=artifacts), patch(
            "pipeline.run_phase6.validate", side_effect=SchemaValidationError("STOP: invalid")
        ), patch("pipeline.run_phase6.write_json_artifact") as write_mock, self.assertRaises(SystemExit):
            run("example.com", "run-en", "run-fr")

        write_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
