from app.seed_urls import _seed_payload, normalize_seed_url, parse_seed_urls


def test_normalize_seed_url_rules() -> None:
    assert normalize_seed_url("  ") is None
    assert normalize_seed_url("Example.COM/path?a=1#Frag") == "https://example.com/path?a=1#Frag"
    assert normalize_seed_url("HTTP://MiXeD.Example.com/Path?Q=Yes") == "https://http://MiXeD.Example.com/Path?Q=Yes"
    assert normalize_seed_url("https://UPPER.example.com/Path/Keep") == "https://upper.example.com/Path/Keep"


def test_parse_seed_urls_dedup_and_sort() -> None:
    input_data = """
example.com/z
https://Example.com/a
example.com/z
http://Example.com/B

"""
    assert parse_seed_urls(input_data) == [
        "http://example.com/B",
        "https://example.com/a",
        "https://example.com/z",
    ]


def test_seed_payload_uses_schema_rows() -> None:
    payload = _seed_payload("example.com", ["https://example.com/a"])
    assert payload["domain"] == "example.com"
    assert payload["urls"] == [{"url": "https://example.com/a", "description": None, "recipe_ids": []}]


def test_seed_payload_rejects_legacy_string_rows_on_read() -> None:
    from unittest.mock import patch
    from app.seed_urls import read_seed_urls

    legacy_payload = {"domain": "example.com", "updated_at": "2026-01-01T00:00:00Z", "urls": ["https://example.com/a"]}
    with patch("app.seed_urls.storage.read_json_artifact", return_value=legacy_payload):
        payload = read_seed_urls("example.com")

    assert payload["domain"] == "example.com"
    assert payload["urls"] == []
