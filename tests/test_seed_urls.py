from app.seed_urls import normalize_seed_url, parse_seed_urls


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
