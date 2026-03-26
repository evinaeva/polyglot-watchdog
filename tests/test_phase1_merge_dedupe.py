from pipeline.run_phase1 import merge_and_dedupe_items


def test_merge_and_dedupe_items_baseline_wins_on_collision():
    baseline = [
        {"item_id": "abc", "url": "https://site/a", "state": "baseline", "text": "Login"},
    ]
    recipe = [
        {"item_id": "abc", "url": "https://site/a", "state": "modal_open", "text": "Login now"},
    ]

    merged = merge_and_dedupe_items(baseline, recipe)

    assert len(merged) == 1
    assert merged[0]["item_id"] == "abc"
    assert merged[0]["state"] == "baseline"
    assert merged[0]["text"] == "Login"


def test_merge_and_dedupe_items_keeps_recipe_only_item_ids():
    baseline = [
        {"item_id": "abc", "url": "https://site/a", "state": "baseline", "text": "Login"},
    ]
    recipe = [
        {"item_id": "xyz", "url": "https://site/a", "state": "modal_open", "text": "Subscribe"},
    ]

    merged = merge_and_dedupe_items(baseline, recipe)

    assert [row["item_id"] for row in merged] == ["abc", "xyz"]


def test_merge_and_dedupe_items_preserves_missing_item_id_rows():
    baseline = [{"item_id": "", "url": "https://site/a", "state": "baseline", "text": "A"}]
    recipe = [{"url": "https://site/a", "state": "modal_open", "text": "B"}]

    merged = merge_and_dedupe_items(baseline, recipe)

    no_id_rows = [row for row in merged if not str(row.get("item_id", "")).strip()]
    assert len(no_id_rows) == 2
    assert sorted([row["text"] for row in no_id_rows]) == ["A", "B"]
