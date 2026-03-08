"""Interaction recipe persistence helpers."""

from __future__ import annotations

from typing import Any

from pipeline import storage
from pipeline.interactive_capture import CapturePoint, Recipe, RecipeStep, validate_state_name
from pipeline.schema_validator import validate


def _recipes_path_run_id() -> str:
    # Recipes are config artifacts under the manual namespace.
    return "manual"


def _normalize_recipe(recipe: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "recipe_id": str(recipe.get("recipe_id", "")).strip(),
        "url_pattern": str(recipe.get("url_pattern", "")).strip(),
        "steps": list(recipe.get("steps", [])),
        "capture_points": list(recipe.get("capture_points", [])),
    }
    validate("interaction_recipe", normalized)
    for point in normalized["capture_points"]:
        validate_state_name(str(point.get("state", "")))
    return normalized


def list_recipes(domain: str) -> list[dict[str, Any]]:
    try:
        payload = storage.read_json_artifact(domain, _recipes_path_run_id(), "recipes.json")
    except Exception:
        return []
    if not isinstance(payload, list):
        return []
    valid: list[dict[str, Any]] = []
    for rec in payload:
        if isinstance(rec, dict):
            valid.append(_normalize_recipe(rec))
    valid.sort(key=lambda r: r["recipe_id"])
    return valid


def write_recipes(domain: str, recipes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = [_normalize_recipe(r) for r in recipes]
    normalized.sort(key=lambda r: r["recipe_id"])
    storage.write_json_artifact(domain, _recipes_path_run_id(), "recipes.json", normalized)
    return normalized


def upsert_recipe(domain: str, recipe: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_recipe(recipe)
    recipes = [r for r in list_recipes(domain) if r["recipe_id"] != normalized["recipe_id"]]
    recipes.append(normalized)
    write_recipes(domain, recipes)
    return normalized


def delete_recipe(domain: str, recipe_id: str) -> list[dict[str, Any]]:
    filtered = [r for r in list_recipes(domain) if r["recipe_id"] != recipe_id]
    write_recipes(domain, filtered)
    return filtered


def load_recipes_for_planner(domain: str) -> dict[str, Recipe]:
    recipes: dict[str, Recipe] = {}
    for raw in list_recipes(domain):
        recipes[raw["recipe_id"]] = Recipe(
            recipe_id=raw["recipe_id"],
            url_pattern=raw["url_pattern"],
            steps=tuple(RecipeStep(**step) for step in raw["steps"]),
            capture_points=tuple(CapturePoint(**cp) for cp in raw["capture_points"]),
        )
    return recipes
