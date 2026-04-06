from __future__ import annotations

from app.recipes import delete_recipe, list_recipes, upsert_recipe
from app.seed_urls import normalize_seed_url, read_seed_urls
from app.server_utils import _utc_now_rfc3339
from pipeline.storage import write_json_artifact


def write_seed_rows_preserve_order(domain: str, rows: list[dict]) -> dict:
    updated_at = _utc_now_rfc3339()
    contract_payload = {
        "domain": domain,
        "updated_at": updated_at,
        "urls": [
            {
                **{k: v for k, v in row.items() if k != "recipe_ids"},
                "url": row["url"],
                "recipe_ids": list(row.get("recipe_ids", [])),
            }
            for row in rows
            if isinstance(row, dict) and str(row.get("url", "")).strip()
        ],
    }
    write_json_artifact(domain, "manual", "seed_urls.json", contract_payload)
    return contract_payload


def get_recipes(domain: str) -> dict:
    return {"recipes": list_recipes(domain)}


def upsert_recipe_for_domain(domain: str, recipe: dict) -> dict:
    saved = upsert_recipe(domain, recipe)
    return {"recipe": saved, "recipes": list_recipes(domain)}


def delete_recipe_for_domain(domain: str, recipe_id: str) -> dict:
    recipes = delete_recipe(domain, recipe_id)
    seed_payload = read_seed_urls(domain)
    rows = [row for row in seed_payload.get("urls", []) if isinstance(row, dict)]
    merged_rows: list[dict] = []
    changed = False
    for row in rows:
        next_row = dict(row)
        current_ids = row.get("recipe_ids", [])
        normalized_ids = list(current_ids) if isinstance(current_ids, list) else []
        filtered_ids = [rid for rid in normalized_ids if str(rid).strip() and str(rid).strip() != recipe_id]
        if filtered_ids != normalized_ids:
            changed = True
        next_row["recipe_ids"] = filtered_ids
        merged_rows.append(next_row)
    saved = write_seed_rows_preserve_order(domain, merged_rows) if changed else seed_payload
    return {"status": "ok", "error": "", "recipe_id": recipe_id, "recipes": recipes, "seed_urls": saved}


def attach_recipe_to_seed_url(domain: str, recipe_id: str, raw_url: str) -> tuple[list[dict], bool]:
    normalized_url = normalize_seed_url(raw_url)
    if not normalized_url:
        raise ValueError("url is required when attach_to_url=true")
    seed_payload = read_seed_urls(domain)
    rows = [row for row in seed_payload.get("urls", []) if isinstance(row, dict)]
    match = next((row for row in rows if str(row.get("url", "")) == normalized_url), None)
    if match is None:
        raise ValueError("url not found in seed_urls")
    current_ids = match.get("recipe_ids", [])
    normalized_ids = list(current_ids) if isinstance(current_ids, list) else []
    recipe_ids = sorted({str(item).strip() for item in normalized_ids if str(item).strip()} | {recipe_id})
    updated_rows = [dict(row) for row in rows]
    attach_changed = False
    for row in updated_rows:
        if str(row.get("url", "")) == normalized_url:
            existing_ids = row.get("recipe_ids", [])
            normalized_existing = list(existing_ids) if isinstance(existing_ids, list) else []
            canonical_existing = sorted({str(item).strip() for item in normalized_existing if str(item).strip()})
            if recipe_ids != canonical_existing:
                attach_changed = True
            row["recipe_ids"] = recipe_ids
    return updated_rows, attach_changed
