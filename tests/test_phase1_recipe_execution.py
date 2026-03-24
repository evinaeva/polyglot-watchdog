import json
import unittest
from pathlib import Path

from pipeline.interactive_capture import CapturePoint, Recipe, RecipeStep
from pipeline.run_phase1 import _execute_recipe_until_state


class _FakeLocator:
    def __init__(self, page, selector):
        self.page = page
        self.selector = selector

    async def click(self):
        self.page.calls.append(("click", self.selector))

    async def fill(self, value):
        self.page.calls.append(("fill", self.selector, value))

    async def press(self, key):
        self.page.calls.append(("press", self.selector, key))

    async def hover(self):
        self.page.calls.append(("hover", self.selector))

    async def scroll_into_view_if_needed(self):
        self.page.calls.append(("scroll_into_view", self.selector))


class _FakeMouse:
    def __init__(self, page):
        self.page = page

    async def wheel(self, x, y):
        self.page.calls.append(("wheel", x, y))


class _FakePage:
    def __init__(self):
        self.calls = []
        self.mouse = _FakeMouse(self)

    def locator(self, selector):
        return _FakeLocator(self, selector)

    async def goto(self, url, timeout=0):
        self.calls.append(("goto", url, timeout))

    async def wait_for_selector(self, selector, state="visible", timeout=0):
        self.calls.append(("wait_for_selector", selector, state, timeout))

    async def wait_for_url(self, pattern, timeout=0):
        self.calls.append(("wait_for_url", pattern, timeout))

    async def wait_for_function(self, expression, timeout=0):
        self.calls.append(("wait_for_function", expression, timeout))


class Phase1RecipeExecutionTests(unittest.IsolatedAsyncioTestCase):
    async def test_scripted_capture_executes_steps_until_matching_capture_marker(self):
        recipe = Recipe(
            recipe_id="profile",
            url_pattern="/profile",
            steps=(
                RecipeStep(action="click", selector="#photos"),
                RecipeStep(action="wait_for_selector", selector=".photos-grid"),
                RecipeStep(action="capture_state", selector="gallery_photos_open"),
                RecipeStep(action="click", selector="#comments"),
                RecipeStep(action="capture_state", selector="comments_panel_open"),
            ),
            capture_points=(
                CapturePoint(state="gallery_photos_open"),
                CapturePoint(state="comments_panel_open"),
            ),
        )
        page = _FakePage()

        await _execute_recipe_until_state(page, recipe, "gallery_photos_open")

        self.assertEqual(
            page.calls,
            [
                ("click", "#photos"),
                ("wait_for_selector", ".photos-grid", "visible", 10000),
            ],
        )

    async def test_scripted_capture_fails_when_multi_capture_recipe_has_no_markers(self):
        recipe = Recipe(
            recipe_id="profile",
            url_pattern="/profile",
            steps=(RecipeStep(action="click", selector="#photos"),),
            capture_points=(
                CapturePoint(state="gallery_photos_open"),
                CapturePoint(state="comments_panel_open"),
            ),
        )
        page = _FakePage()

        with self.assertRaisesRegex(RuntimeError, "requires capture_state step markers"):
            await _execute_recipe_until_state(page, recipe, "comments_panel_open")

    async def test_recipe_marker_matching_drift_regression(self):
        case = json.loads(Path("tests/fixtures/recipe_marker_drift_case.json").read_text(encoding="utf-8"))
        recipe = Recipe(
            recipe_id=case["recipe_id"],
            url_pattern=case["url_pattern"],
            steps=tuple(RecipeStep(action=step["action"], selector=step.get("selector")) for step in case["steps"]),
            capture_points=tuple(CapturePoint(state=point["state"]) for point in case["capture_points"]),
        )
        page = _FakePage()

        with self.assertRaisesRegex(RuntimeError, case["expected_error_substring"]):
            await _execute_recipe_until_state(page, recipe, case["target_state"])


if __name__ == "__main__":
    unittest.main()
