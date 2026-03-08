import unittest

from pipeline.interactive_capture import CaptureContext, DeterminismError, GCSArtifactWriter, InMemoryStore, RunContext, capture_state
from pipeline.phase1_puller import wait_for_capture_readiness


class _TimeoutPage:
    async def wait_for_load_state(self, state, timeout):
        raise TimeoutError(f"timeout at {state}")

    async def wait_for_selector(self, selector, state, timeout):
        return None

    async def wait_for_timeout(self, ms):
        return None


class Phase1FailFastTests(unittest.IsolatedAsyncioTestCase):
    async def test_wait_policy_timeout_fails_hard(self):
        page = _TimeoutPage()
        with self.assertRaises(TimeoutError):
            await wait_for_capture_readiness(page, "baseline")

    def test_missing_bbox_fails_and_writes_nothing(self):
        store = InMemoryStore()
        writer = GCSArtifactWriter(store, "watchdog-data", "watchdog-review")
        context = CaptureContext("example.com", "https://example.com/", "en", "desktop", "baseline", "guest")
        payload = (
            {"viewport": {"width": 10, "height": 10}, "screenshot_bytes": b"PNG"},
            [{"css_selector": "main > p", "element_type": "p", "text": "x", "visible": True}],
        )
        with self.assertRaises(DeterminismError):
            capture_state(context, payload, writer, RunContext("r1", "2026-01-01T00:00:00Z"))
        self.assertEqual(store.objects, {})


if __name__ == "__main__":
    unittest.main()
