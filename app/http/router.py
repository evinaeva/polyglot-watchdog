from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
from urllib.parse import ParseResult

RouteHandler = Callable[[object, ParseResult], bool]


@dataclass(frozen=True)
class Route:
    method: str
    path: str
    handler: RouteHandler


class MethodPathRouter:
    """Simple method+path dispatcher with optional prefix routes."""

    def __init__(self) -> None:
        self._exact: dict[tuple[str, str], RouteHandler] = {}
        self._prefix: dict[str, list[tuple[str, RouteHandler]]] = {}

    def add(self, method: str, path: str, handler: RouteHandler) -> None:
        self._exact[(method.upper(), path)] = handler

    def add_prefix(self, method: str, path_prefix: str, handler: RouteHandler) -> None:
        self._prefix.setdefault(method.upper(), []).append((path_prefix, handler))

    def dispatch(self, request_handler: object, *, method: str, parsed: ParseResult) -> bool:
        method_u = method.upper()
        exact = self._exact.get((method_u, parsed.path))
        if exact is not None:
            return exact(request_handler, parsed)
        for prefix, handler in self._prefix.get(method_u, []):
            if parsed.path.startswith(prefix):
                if handler(request_handler, parsed):
                    return True
        return False
