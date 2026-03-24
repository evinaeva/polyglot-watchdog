from pipeline.phase2_annotator import filter_items_by_rules


def test_phase3_filter_preserves_logical_matching_fields_into_eligible_dataset():
    collected = [{
        "item_id": "i1",
        "page_id": "p1",
        "url": "https://example.com/p",
        "language": "en",
        "element_type": "p",
        "text": "Hello",
        "page_canonical_key": "a" * 40,
        "logical_match_key": "b" * 40,
        "path_signature": "main>p",
        "container_signature": "main",
        "normalized_ordinal": 1,
        "semantic_hint": "role=button",
        "tag": "p",
        "attributes": {"role": "button"},
        "state": "baseline",
        "user_tier": "guest",
        "viewport_kind": "desktop",
    }]
    out = filter_items_by_rules(collected, [])
    row = out[0]
    assert row["logical_match_key"] == "b" * 40
    assert row["page_canonical_key"] == "a" * 40
    assert row["path_signature"] == "main>p"
    assert row["container_signature"] == "main"
    assert row["normalized_ordinal"] == 1
