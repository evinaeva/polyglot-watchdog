import unittest

from pipeline.phase0_crawler import build_url_inventory, canonicalize_url
from pipeline.phase1_puller import compute_item_id
from pipeline.phase5_normalizer import normalize_text
from pipeline.schema_validator import validate


class ContractPipelineTests(unittest.TestCase):
    def test_phase0_canonicalization_and_sort(self):
        urls = [
            "http://example.com/b#frag",
            "https://example.com/a?page=2",
            "https://example.com/a?page=2",
            "https://example.com/a#x",
        ]
        inventory = build_url_inventory(urls, domain="example.com", url_rules=[])
        self.assertEqual(inventory, [
            "https://example.com/a",
            "https://example.com/a?page=2",
            "https://example.com/b",
        ])
        self.assertEqual(canonicalize_url("http://example.com/x#f"), "https://example.com/x")

    def test_phase1_item_id_deterministic_excludes_text(self):
        bbox = {"x": 1, "y": 2, "width": 3, "height": 4}
        a = compute_item_id("example.com", "https://example.com/a", "div > p", bbox, "p")
        b = compute_item_id("example.com", "https://example.com/a", "div > p", bbox, "p")
        self.assertEqual(a, b)

    def test_phase5_preserves_double_spaces(self):
        self.assertEqual(normalize_text("A  B\r\nC"), "A  B\nC")

    def test_issues_schema_shape(self):
        issues = [{
            "id": "1",
            "category": "MISSING_TRANSLATION",
            "confidence": 0.5,
            "message": "m",
            "evidence": {"url": "https://example.com", "bbox": {"x": 0, "y": 0, "width": 1, "height": 1}, "storage_uri": "gs://b/s.png"},
        }]
        validate("issues", issues)


if __name__ == "__main__":
    unittest.main()
