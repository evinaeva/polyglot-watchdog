import unittest

from pipeline.interactive_capture import (
    CaptureContext,
    CapturePoint,
    DeterminismError,
    DeterministicPlanner,
    GCSArtifactWriter,
    InMemoryStore,
    Recipe,
    RecipeStep,
    RunContext,
    build_capture_context_id,
    build_eligible_dataset,
    build_universal_sections_en_only,
    capture_state,
)


class InteractiveCaptureAcceptanceTests(unittest.TestCase):
    def _payload(self, text="Hello"):
        return (
            {"viewport": {"width": 1280, "height": 720}, "screenshot_bytes": b"PNG"},
            [
                {
                    "css_selector": "header > h1",
                    "element_type": "h1",
                    "bbox": {"x": 1, "y": 2, "width": 3, "height": 4},
                    "text": text,
                    "visible": True,
                }
            ],
        )

    def _run_context(self):
        return RunContext(run_id="run-20260101-01", run_started_at="2026-01-01T00:00:00Z")

    def test_baseline_contract_test(self):
        store = InMemoryStore()
        writer = GCSArtifactWriter(store, "watchdog-data", "watchdog-review")
        context = CaptureContext("example.com", "https://example.com/", "en", "desktop", "baseline", "guest")
        out = capture_state(context, self._payload(), writer, self._run_context())
        self.assertTrue(out["page"]["storage_uri"].endswith("/screenshot.png"))
        keys = [k for (bucket, k) in store.objects if bucket == "watchdog-data"]
        self.assertEqual(len([k for k in keys if "/screenshots/" in k]), 1)
        self.assertEqual(len([k for k in keys if "/pages/" in k]), 1)
        self.assertEqual(len([k for k in keys if "/elements/" in k]), 1)

    def test_multi_state_recipe_test(self):
        planner = DeterministicPlanner()
        seed_urls = {"domain": "example.com", "urls": [{"url": "https://example.com/profile", "recipe_ids": ["profile"]}]}
        recipes = {
            "profile": Recipe(
                recipe_id="profile",
                url_pattern="/profile",
                steps=(RecipeStep(action="click", selector="#photos"),),
                capture_points=(CapturePoint("gallery_photos_open"), CapturePoint("gallery_videos_open"), CapturePoint("comments_panel_open")),
            )
        }
        jobs = planner.expand_jobs(seed_urls, recipes, ["en"], ["desktop"], ["guest"])
        states = [j.context.state for j in jobs]
        self.assertEqual(states.count("baseline"), 1)
        self.assertEqual(len([s for s in states if s != "baseline"]), 3)

    def test_determinism_test_byte_identical(self):
        store = InMemoryStore()
        writer = GCSArtifactWriter(store, "watchdog-data", "watchdog-review")
        context = CaptureContext("example.com", "https://example.com/", "en", "desktop", "baseline", "guest")
        run_context = self._run_context()

        out1 = capture_state(context, self._payload(), writer, run_context)
        out2 = capture_state(context, self._payload(), writer, run_context)
        self.assertEqual([e["item_id"] for e in out1["elements"]], [e["item_id"] for e in out2["elements"]])
        self.assertEqual(out1["uris"], out2["uris"])

        page_key = out1["uris"]["page_uri"].replace("gs://watchdog-data/", "")
        page_bytes_1 = store.objects[("watchdog-data", page_key)]
        page_bytes_2 = store.objects[("watchdog-data", page_key)]
        self.assertEqual(page_bytes_1, page_bytes_2)
        self.assertIn(b"\"captured_at\":\"2026-01-01T00:00:00Z\"", page_bytes_1)


    def test_capture_context_id_excludes_language(self):
        base = CaptureContext("example.com", "https://example.com/", "en", "desktop", "baseline", "guest")
        fr = CaptureContext("example.com", "https://example.com/", "fr", "desktop", "baseline", "guest")
        self.assertEqual(build_capture_context_id(base), build_capture_context_id(fr))

    def test_page_storage_uri_not_placeholder(self):
        store = InMemoryStore()
        writer = GCSArtifactWriter(store, "watchdog-data", "watchdog-review")
        context = CaptureContext("example.com", "https://example.com/", "en", "desktop", "baseline", "guest")
        result = capture_state(context, self._payload(), writer, self._run_context())

        page_key = result["uris"]["page_uri"].replace("gs://watchdog-data/", "")
        page_json = store.read_json("watchdog-data", page_key)
        self.assertEqual(page_json["storage_uri"], result["uris"]["screenshot_uri"])
        self.assertNotEqual(page_json["storage_uri"], "pending://screenshot")

    def test_overlay_review_excludes_eligible_dataset(self):
        store = InMemoryStore()
        writer = GCSArtifactWriter(store, "watchdog-data", "watchdog-review")
        context = CaptureContext("example.com", "https://example.com/", "fr", "desktop", "baseline", "guest")
        result = capture_state(context, self._payload(), writer, self._run_context())

        capture_context_id = build_capture_context_id(context)
        review_statuses = [{"capture_context_id": capture_context_id, "status": "blocked_by_overlay"}]
        page_map = {capture_context_id: result["page"]}
        eligible = build_eligible_dataset(result["elements"], review_statuses, page_map)
        self.assertEqual(eligible, [])

    def test_universal_sections_test(self):
        run_context = self._run_context()
        pages = [
            {"page_id": "p1", "url": "https://example.com/a", "state": "baseline"},
            {"page_id": "p2", "url": "https://example.com/b", "state": "baseline"},
        ]
        items = [
            {"page_id": "p1", "language": "en", "state": "baseline", "css_selector": "header > h1", "element_type": "h1", "text": "Site"},
            {"page_id": "p2", "language": "en", "state": "baseline", "css_selector": "header > h1", "element_type": "h1", "text": "Site"},
        ]
        sections = build_universal_sections_en_only(pages, items, run_context)
        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0]["representative_url"], "https://example.com/a")
        self.assertEqual(sections[0]["created_at"], run_context.run_started_at)

    def test_cross_language_recipe_reproduction_test(self):
        planner = DeterministicPlanner()
        seed_urls = {"domain": "example.com", "urls": [{"url": "https://example.com/profile", "recipe_ids": ["profile"]}]}
        recipes = {
            "profile": Recipe(
                recipe_id="profile",
                url_pattern="/profile",
                steps=(RecipeStep(action="navigate"),),
                capture_points=(CapturePoint("gallery_photos_open"),),
            )
        }
        jobs = planner.expand_jobs(seed_urls, recipes, ["en", "fr"], ["desktop"], ["guest"])
        states_by_lang = {}
        for job in jobs:
            states_by_lang.setdefault(job.context.language, set()).add(job.context.state)
        self.assertEqual(states_by_lang["en"], states_by_lang["fr"])

    def test_fail_fast_missing_selector(self):
        store = InMemoryStore()
        writer = GCSArtifactWriter(store, "watchdog-data", "watchdog-review")
        context = CaptureContext("example.com", "https://example.com/", "en", "desktop", "baseline", "guest")
        payload = (
            {"viewport": {"width": 1, "height": 1}, "screenshot_bytes": b"PNG"},
            [{"element_type": "p", "bbox": {"x": 0, "y": 0, "width": 1, "height": 1}, "text": "x"}],
        )
        with self.assertRaises(DeterminismError):
            capture_state(context, payload, writer, self._run_context())

    def test_unordered_elements_are_stabilized_not_failed(self):
        store = InMemoryStore()
        writer = GCSArtifactWriter(store, "watchdog-data", "watchdog-review")
        context = CaptureContext("example.com", "https://example.com/", "en", "desktop", "baseline", "guest")
        payload = (
            {"viewport": {"width": 1, "height": 1}, "screenshot_bytes": b"PNG"},
            [
                {"css_selector": "b", "element_type": "p", "bbox": {"x": 0, "y": 0, "width": 1, "height": 1}, "text": "x"},
                {"css_selector": "a", "element_type": "p", "bbox": {"x": 0, "y": 0, "width": 1, "height": 1}, "text": "y"},
            ],
        )
        result = capture_state(context, payload, writer, self._run_context())
        ids = [element["item_id"] for element in result["elements"]]
        self.assertEqual(ids, sorted(ids))


if __name__ == "__main__":
    unittest.main()
