import unittest
from unittest.mock import patch

from app.recipes import delete_recipe, list_recipes, load_recipes_for_planner, upsert_recipe


class RecipesCrudTests(unittest.TestCase):
    def test_upsert_and_list_are_deterministic(self):
        r2 = {
            "recipe_id": "b",
            "url_pattern": "/p",
            "steps": [{"action": "click", "selector": "#x", "wait_for": None}],
            "capture_points": [{"state": "gallery_open"}],
        }
        r1 = {
            "recipe_id": "a",
            "url_pattern": "/p",
            "steps": [{"action": "click", "selector": "#x", "wait_for": None}],
            "capture_points": [{"state": "baseline"}],
        }

        mem = []

        def fake_read(domain, run_id, filename):
            if not mem:
                raise RuntimeError("missing")
            return list(mem)

        def fake_write(domain, run_id, filename, data):
            mem.clear()
            mem.extend(data)
            return "gs://bucket/x"

        with patch("app.recipes.storage.read_json_artifact", side_effect=fake_read), patch(
            "app.recipes.storage.write_json_artifact", side_effect=fake_write
        ):
            upsert_recipe("example.com", r2)
            upsert_recipe("example.com", r1)
            recipes = list_recipes("example.com")

        self.assertEqual([r["recipe_id"] for r in recipes], ["a", "b"])

    def test_delete_recipe(self):
        existing = [
            {"recipe_id": "a", "url_pattern": "/a", "steps": [{"action": "click"}], "capture_points": [{"state": "baseline"}]},
            {"recipe_id": "b", "url_pattern": "/b", "steps": [{"action": "click"}], "capture_points": [{"state": "user"}]},
        ]

        with patch("app.recipes.storage.read_json_artifact", return_value=existing), patch(
            "app.recipes.storage.write_json_artifact", return_value="gs://bucket/x"
        ):
            remaining = delete_recipe("example.com", "a")

        self.assertEqual([r["recipe_id"] for r in remaining], ["b"])

    def test_load_recipes_for_planner(self):
        existing = [
            {"recipe_id": "profile", "url_pattern": "/profile", "steps": [{"action": "click"}], "capture_points": [{"state": "profile_open"}]},
        ]
        with patch("app.recipes.storage.read_json_artifact", return_value=existing):
            loaded = load_recipes_for_planner("example.com")
        self.assertIn("profile", loaded)
        self.assertEqual(loaded["profile"].capture_points[0].state, "profile_open")


if __name__ == "__main__":
    unittest.main()
