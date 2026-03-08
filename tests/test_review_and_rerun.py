import unittest
from unittest.mock import patch

from app.skeleton_server import _parse_rerun_payload, _persist_capture_review
from pipeline.run_phase1 import build_exact_context_job


class ReviewAndRerunTests(unittest.TestCase):
    def test_review_persistence_requires_language_and_capture_context(self):
        with self.assertRaisesRegex(ValueError, "capture_context_id is required"):
            _persist_capture_review({"domain": "example.com", "language": "en", "status": "valid", "timestamp": "2026-01-01T00:00:00Z"})
        with self.assertRaisesRegex(ValueError, "language is required"):
            _persist_capture_review({"domain": "example.com", "capture_context_id": "abc", "status": "valid", "timestamp": "2026-01-01T00:00:00Z"})

    def test_review_persistence_validates_and_writes(self):
        payload = {
            "domain": "example.com",
            "capture_context_id": "ctx1",
            "language": "en",
            "status": "valid",
            "reviewer": "qa",
            "timestamp": "2026-01-01T00:00:00Z",
        }
        with patch("app.skeleton_server.GCSArtifactWriter.set_review_status", return_value="gs://review/x.json") as m:
            out = _persist_capture_review(payload)
        self.assertEqual(out["storage_uri"], "gs://review/x.json")
        m.assert_called_once()

    def test_rerun_payload_rejects_url_only(self):
        with self.assertRaisesRegex(ValueError, "missing required fields"):
            _parse_rerun_payload({"domain": "example.com", "run_id": "r1", "url": "https://example.com/"})

    def test_exact_context_job_resolves_single_job(self):
        job = build_exact_context_job(
            domain="example.com",
            url="https://example.com/profile",
            language="en",
            viewport_kind="desktop",
            state="profile_open",
            user_tier="guest",
        )
        self.assertEqual(job.context.url, "https://example.com/profile")
        self.assertEqual(job.context.state, "profile_open")
        self.assertEqual(job.context.viewport_kind, "desktop")
        self.assertEqual(job.context.user_tier, "guest")


if __name__ == "__main__":
    unittest.main()
