import unittest
from unittest.mock import patch

from app.skeleton_server import _parse_rerun_payload, _persist_capture_review
from pipeline.interactive_capture import CapturePoint, InMemoryStore, Recipe, RecipeStep, GCSArtifactWriter
from pipeline.run_phase1 import build_exact_context_job, run_exact_context


class ReviewAndRerunTests(unittest.TestCase):
    def test_review_persistence_requires_language_and_capture_context(self):
        with self.assertRaisesRegex(ValueError, "capture_context_id is required"):
            _persist_capture_review({"domain": "example.com", "language": "en", "status": "valid", "timestamp": "2026-01-01T00:00:00Z"})
        with self.assertRaisesRegex(ValueError, "language is required"):
            _persist_capture_review({"domain": "example.com", "capture_context_id": "abc", "status": "valid", "timestamp": "2026-01-01T00:00:00Z"})

    def test_review_status_prefix_and_key_are_canonical(self):
        writer = GCSArtifactWriter(InMemoryStore(), "data-bucket", "review-bucket")
        self.assertEqual(writer.review_status_prefix("example.com"), "example.com/capture_status/")
        self.assertEqual(
            writer.review_status_key("example.com", "ctx-1", "en"),
            "example.com/capture_status/ctx-1__en.json",
        )

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



    def test_rerun_payload_requires_capture_context_id(self):
        with self.assertRaisesRegex(ValueError, "capture_context_id"):
            _parse_rerun_payload(
                {
                    "domain": "example.com",
                    "run_id": "r1",
                    "url": "https://example.com/",
                    "viewport_kind": "desktop",
                    "state": "guest",
                    "language": "en",
                    "recipe_id": "profile",
                    "capture_point_id": "cp-1",
                }
            )

    def test_rerun_payload_accepts_capture_context_id(self):
        payload = _parse_rerun_payload(
            {
                "domain": "example.com",
                "run_id": "r1",
                "url": "https://example.com/",
                "viewport_kind": "desktop",
                "state": "guest",
                "language": "en",
                "capture_context_id": "ctx-1",
                "recipe_id": "profile",
                "capture_point_id": "cp-1",
            }
        )
        self.assertEqual(payload["capture_context_id"], "ctx-1")
        self.assertEqual(payload["recipe_id"], "profile")
        self.assertEqual(payload["capture_point_id"], "cp-1")

    def test_rerun_payload_accepts_baseline_without_recipe_identifiers(self):
        payload = _parse_rerun_payload(
            {
                "domain": "example.com",
                "run_id": "r1",
                "url": "https://example.com/",
                "viewport_kind": "desktop",
                "state": "baseline",
                "language": "en",
                "capture_context_id": "ctx-1",
            }
        )
        self.assertIsNone(payload["recipe_id"])
        self.assertIsNone(payload["capture_point_id"])

    def test_rerun_payload_rejects_partial_recipe_identifiers(self):
        with self.assertRaisesRegex(ValueError, "requires both recipe_id and capture_point_id"):
            _parse_rerun_payload(
                {
                    "domain": "example.com",
                    "run_id": "r1",
                    "url": "https://example.com/",
                    "viewport_kind": "desktop",
                    "state": "profile_open",
                    "language": "en",
                    "capture_context_id": "ctx-1",
                    "recipe_id": "profile",
                }
            )

    def test_exact_context_job_resolves_single_job(self):
        recipes = {
            "profile": Recipe(
                recipe_id="profile",
                url_pattern="/profile",
                steps=(RecipeStep(action="click", selector="#profile"),),
                capture_points=(CapturePoint(state="profile_open", capture_point_id="cp-profile-open"),),
            )
        }
        with patch("pipeline.run_phase1.load_recipes_for_planner", return_value=recipes):
            job = build_exact_context_job(
                domain="example.com",
                url="https://example.com/profile",
                language="en",
                viewport_kind="desktop",
                state="profile_open",
                user_tier="guest",
                recipe_id="profile",
                capture_point_id="cp-profile-open",
            )
        self.assertEqual(job.context.url, "https://example.com/profile")
        self.assertEqual(job.context.state, "profile_open")
        self.assertEqual(job.context.viewport_kind, "desktop")
        self.assertEqual(job.context.user_tier, "guest")
        self.assertEqual(job.capture_point_id, "cp-profile-open")

    def test_exact_context_state_only_ambiguous_fails(self):
        recipes = {
            "p1": Recipe(
                recipe_id="p1",
                url_pattern="/profile",
                steps=(RecipeStep(action="click", selector="#profile"),),
                capture_points=(CapturePoint(state="profile_open", capture_point_id="cp-1"),),
            ),
            "p2": Recipe(
                recipe_id="p2",
                url_pattern="/profile",
                steps=(RecipeStep(action="click", selector="#profile"),),
                capture_points=(CapturePoint(state="profile_open", capture_point_id="cp-2"),),
            ),
        }
        with patch("pipeline.run_phase1.load_recipes_for_planner", return_value=recipes):
            with self.assertRaisesRegex(RuntimeError, "Ambiguous state"):
                build_exact_context_job(
                    domain="example.com",
                    url="https://example.com/profile",
                    language="en",
                    viewport_kind="desktop",
                    state="profile_open",
                    user_tier="guest",
                )

    def test_exact_context_mismatch_between_state_and_capture_point_fails(self):
        recipes = {
            "profile": Recipe(
                recipe_id="profile",
                url_pattern="/profile",
                steps=(RecipeStep(action="click", selector="#profile"),),
                capture_points=(CapturePoint(state="profile_open", capture_point_id="cp-profile-open"),),
            )
        }
        with patch("pipeline.run_phase1.load_recipes_for_planner", return_value=recipes):
            with self.assertRaisesRegex(RuntimeError, "State mismatch"):
                build_exact_context_job(
                    domain="example.com",
                    url="https://example.com/profile",
                    language="en",
                    viewport_kind="desktop",
                    state="other_state",
                    user_tier="guest",
                    recipe_id="profile",
                    capture_point_id="cp-profile-open",
                )

    def test_exact_context_rerun_includes_provenance_link(self):
        recipes = {
            "profile": Recipe(
                recipe_id="profile",
                url_pattern="/profile",
                steps=(RecipeStep(action="click", selector="#profile"),),
                capture_points=(CapturePoint(state="profile_open", capture_point_id="cp-profile-open"),),
            )
        }
        with patch("pipeline.run_phase1.load_recipes_for_planner", return_value=recipes), \
             patch("pipeline.run_phase1.main") as main_mock, \
             patch("pipeline.run_phase1.asyncio.run", side_effect=lambda coro: None):
            run_exact_context(
                domain="example.com",
                run_id="run-rerun",
                url="https://example.com/profile",
                viewport_kind="desktop",
                state="profile_open",
                user_tier="guest",
                language="en",
                original_context_id="ctx-orig",
                recipe_id="profile",
                capture_point_id="cp-profile-open",
            )

        self.assertTrue(main_mock.called)
        _, kwargs = main_mock.call_args
        self.assertEqual(kwargs["rerun_provenance"]["original_capture_context_id"], "ctx-orig")
        self.assertEqual(kwargs["rerun_provenance"]["state"], "profile_open")
        self.assertEqual(kwargs["rerun_provenance"]["capture_point_id"], "cp-profile-open")


if __name__ == "__main__":
    unittest.main()
