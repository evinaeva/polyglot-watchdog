from app.seed_urls import _seed_payload, normalize_seed_url, parse_seed_urls, parse_seed_urls_with_errors


def test_normalize_seed_url_rules() -> None:
    assert normalize_seed_url("  ") is None
    assert normalize_seed_url("Example.COM/path?a=1#Frag") == "https://example.com/path?a=1#Frag"
    assert normalize_seed_url("HTTP://MiXeD.Example.com/Path?Q=Yes") == "http://mixed.example.com/Path?Q=Yes"
    assert normalize_seed_url("https://UPPER.example.com/Path/Keep/") == "https://upper.example.com/Path/Keep"


def test_parse_seed_urls_dedup_and_sort() -> None:
    input_data = """
example.com/z
https://Example.com/a
example.com/z
http://Example.com/B/

"""
    assert parse_seed_urls(input_data) == [
        "http://example.com/B",
        "https://example.com/a",
        "https://example.com/z",
    ]


def test_parse_seed_urls_with_errors_collects_bad_lines() -> None:
    parsed = parse_seed_urls_with_errors("good.example.com\nftp://bad.example.com\n")
    assert parsed["urls"] == ["https://good.example.com/"]
    assert len(parsed["errors"]) == 1
    assert parsed["errors"][0]["line"] == 2


def test_seed_payload_uses_schema_rows() -> None:
    payload = _seed_payload("example.com", ["https://example.com/a"])
    assert payload["domain"] == "example.com"
    assert payload["urls"] == [{"url": "https://example.com/a", "description": None, "recipe_ids": [], "active": True}]


def test_seed_payload_rejects_legacy_string_rows_on_read() -> None:
    from unittest.mock import patch
    from app.seed_urls import read_seed_urls

    legacy_payload = {"domain": "example.com", "updated_at": "2026-01-01T00:00:00Z", "urls": ["https://example.com/a"]}
    with patch("app.seed_urls.storage.read_json_artifact", return_value=legacy_payload):
        payload = read_seed_urls("example.com")

    assert payload["domain"] == "example.com"
    assert payload["urls"] == []


def test_seed_payload_recovers_from_non_string_updated_at() -> None:
    from unittest.mock import patch
    from app.seed_urls import read_seed_urls

    bad_payload = {"domain": "example.com", "updated_at": 123, "urls": [{"url": "https://example.com/a", "recipe_ids": []}]}
    with patch("app.seed_urls.storage.read_json_artifact", return_value=bad_payload):
        payload = read_seed_urls("example.com")

    assert isinstance(payload["updated_at"], str)


def test_write_seed_rows_preserves_active_roundtrip(monkeypatch):
    from app.seed_urls import read_seed_urls, write_seed_rows

    db = {}

    def fake_write(domain, run_id, filename, data):
        db[(domain, run_id, filename)] = data
        return "ok"

    def fake_read(domain, run_id, filename):
        return db[(domain, run_id, filename)]

    monkeypatch.setattr("app.seed_urls.storage.write_json_artifact", fake_write)
    monkeypatch.setattr("app.seed_urls.storage.read_json_artifact", fake_read)

    write_seed_rows("example.com", [{"url": "https://example.com/a", "recipe_ids": [], "active": False}])
    loaded = read_seed_urls("example.com")
    assert loaded["urls"][0]["active"] is False


def test_load_active_map_ignores_invalid_state_urls(monkeypatch):
    from app.seed_urls import _load_active_map

    monkeypatch.setattr(
        "app.seed_urls.storage.read_json_artifact",
        lambda domain, run_id, filename: {
            "states": [
                {"url": "ftp://bad.example.com", "active": False},
                {"url": "good.example.com", "active": False},
            ]
        },
    )

    mapping = _load_active_map("example.com")
    assert mapping == {"https://good.example.com/": False}
