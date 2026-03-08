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


class _FailingBrowser:
    async def new_context(self, **kwargs):
        class _Ctx:
            async def new_page(self):
                return object()
        return _Ctx()

    async def close(self):
        return None


class _PlaywrightCM:
    async def __aenter__(self):
        class _P:
            class chromium:
                @staticmethod
                async def launch():
                    return _FailingBrowser()
        return _P()

    async def __aexit__(self, exc_type, exc, tb):
        return False


class Phase1RunFailFastTests(unittest.TestCase):
    def test_phase1_main_fails_fast_on_pull_error(self):
        from pipeline import run_phase1
        from pipeline.interactive_capture import CaptureContext, CaptureJob
        from unittest.mock import AsyncMock, patch

        job = CaptureJob(
            context=CaptureContext(
                domain="example.com",
                url="https://example.com/",
                language="en",
                viewport_kind="desktop",
                state="baseline",
                user_tier="guest",
            ),
            mode="baseline",
        )

        import types, sys
        fake_playwright = types.SimpleNamespace(async_playwright=lambda: _PlaywrightCM())
        with patch.dict(sys.modules, {"playwright.async_api": fake_playwright}), \
             patch("pipeline.run_phase1.pull_page", new=AsyncMock(side_effect=RuntimeError("boom"))), \
             patch("pipeline.run_phase1.write_json_artifact") as write_mock:
            with self.assertRaises(SystemExit):
                import asyncio
                asyncio.run(run_phase1.main("example.com", "run-1", "en", "desktop", "baseline", "guest", jobs_override=[job]))

        write_mock.assert_not_called()
