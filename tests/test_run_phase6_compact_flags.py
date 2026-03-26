from pipeline.run_phase6 import _kind_code, _resolve_masked_flag


def test_resolve_masked_flag_prefers_explicit_upstream_signal_over_regex():
    target_item = {"mask_applied": False}
    evidence_base = {"masked_flag": 0}
    assert _resolve_masked_flag(target_item, evidence_base, "***") == 0

    target_item_true = {"mask_applied": True}
    assert _resolve_masked_flag(target_item_true, {}, "normal text") == 1


def test_resolve_masked_flag_uses_regex_fallback_when_explicit_signal_absent():
    assert _resolve_masked_flag({}, {}, "***") == 1
    assert _resolve_masked_flag({}, {}, "normal text") == 0


def test_kind_code_4_represents_short_text_inference():
    assert _kind_code({"tag": "span"}, {"tag": "span"}, "Short label") == 4
