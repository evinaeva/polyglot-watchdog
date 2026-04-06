from __future__ import annotations


def handle_post(handler: object, parsed) -> bool:
    handler._legacy_api_post(parsed)
    return True


def handle_put(handler: object, parsed) -> bool:
    handler._legacy_api_put(parsed)
    return True
