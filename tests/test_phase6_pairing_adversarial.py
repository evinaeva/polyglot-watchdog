from pipeline.run_phase6 import _pair_target_items


def _en_item(**overrides):
    base = {
        "item_id": "en-1",
        "url": "https://example.com/p",
        "element_type": "p",
        "css_selector": "main > p",
        "local_path_signature": "p#1>main#1",
        "container_signature": "main",
        "role_hint": "",
        "stable_ordinal": 1,
        "semantic_attrs": {},
        "text": "Buy now",
    }
    base.update(overrides)
    return base


def _target_item(**overrides):
    base = {
        "item_id": "fr-1",
        "url": "https://example.com/fr/p",
        "element_type": "p",
        "css_selector": "main > p",
        "local_path_signature": "p#1>main#1",
        "container_signature": "main",
        "role_hint": "",
        "stable_ordinal": 1,
        "semantic_attrs": {},
        "text": "Acheter",
    }
    base.update(overrides)
    return base


def test_single_candidate_true_drift_pairs():
    matched, meta = _pair_target_items(_en_item(), [_target_item(item_id="drifted")], used_target_ids=set())
    assert matched is not None
    assert meta["pairing_basis"] in {"fallback_weighted", "logical_match_key_exact"}


def test_single_candidate_unrelated_remains_unresolved():
    en = _en_item(css_selector="main > h1", local_path_signature="h1#1>header#1", container_signature="header", stable_ordinal=1)
    unrelated = _target_item(
        item_id="fr-unrelated",
        css_selector="footer > a",
        element_type="a",
        local_path_signature="a#4>footer#1",
        container_signature="footer",
        stable_ordinal=4,
        text="Contact",
    )
    matched, meta = _pair_target_items(en, [unrelated], used_target_ids=set())
    assert matched is None
    assert meta["pairing_basis"] == "fallback_no_viable_candidate"


def test_ambiguous_candidates_remain_unresolved_with_provenance():
    en = _en_item()
    t1 = _target_item(item_id="fr-1")
    t2 = _target_item(item_id="fr-2")
    matched, meta = _pair_target_items(en, [t1, t2], used_target_ids=set())
    assert matched is None
    assert meta["pairing_basis"] in {"ambiguous_logical_match_key", "fallback_ambiguous"}
    assert "pairing_score_breakdown" in meta


def test_logical_key_exact_beats_weighted_fallback():
    en = _en_item(logical_match_key="lk-1", css_selector="main > h2")
    exact = _target_item(item_id="fr-exact", logical_match_key="lk-1", css_selector="other")
    weighted = _target_item(item_id="fr-weighted", logical_match_key="lk-2", css_selector="main > h2")
    matched, meta = _pair_target_items(en, [weighted, exact], used_target_ids=set())
    assert matched["item_id"] == "fr-exact"
    assert meta["pairing_basis"] == "logical_match_key_exact"


def test_pairing_is_deterministic_for_same_inputs():
    en = _en_item()
    candidates = [_target_item(item_id="fr-a"), _target_item(item_id="fr-b", css_selector="main > span", element_type="span")]
    first = _pair_target_items(en, candidates, used_target_ids=set())
    second = _pair_target_items(en, candidates, used_target_ids=set())
    assert first == second
