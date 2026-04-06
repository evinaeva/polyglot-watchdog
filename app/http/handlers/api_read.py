from __future__ import annotations


def handle_get(handler: object, parsed) -> bool:
    """Read-only API GET routes. Kept as a dedicated module for future endpoint-level split."""
    handler._legacy_api_get(parsed)
    return True
