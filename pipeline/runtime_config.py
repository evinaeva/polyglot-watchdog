"""Unified runtime config loaders for pipeline execution entrypoints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from pipeline.schema_validator import validate

_ALLOWED_VIEWPORTS = {"desktop", "mobile", "responsive"}
_ALLOWED_STATES = {"guest", "user"}


@dataclass(frozen=True)
class Phase1RuntimeConfig:
    domain: str
    run_id: str
    language: str
    viewport_kind: str
    state: str
    user_tier: str | None


def validate_seed_urls_payload(payload: Mapping[str, Any]) -> None:
    """Validate canonical seed_urls payload shape used by runtime planning."""
    validate("seed_urls", {"domain": payload.get("domain"), "urls": payload.get("urls")})


def load_phase1_runtime_config(source: Mapping[str, Any]) -> Phase1RuntimeConfig:
    """Load one normalized Phase 1 runtime config from UI/programmatic input."""
    domain = str(source.get("domain", "")).strip()
    run_id = str(source.get("run_id", "")).strip()
    language = str(source.get("language", "en")).strip() or "en"
    viewport_kind = str(source.get("viewport_kind", source.get("viewport", "desktop"))).strip() or "desktop"
    state = str(source.get("state", "guest")).strip() or "guest"
    raw_user_tier = source.get("user_tier")
    user_tier = str(raw_user_tier).strip() if raw_user_tier not in (None, "") else None

    if not domain:
        raise ValueError("domain is required")
    if not run_id:
        raise ValueError("run_id is required")
    if viewport_kind not in _ALLOWED_VIEWPORTS:
        raise ValueError(f"viewport_kind must be one of {sorted(_ALLOWED_VIEWPORTS)}")
    if state not in _ALLOWED_STATES:
        raise ValueError(f"state must be one of {sorted(_ALLOWED_STATES)}")

    return Phase1RuntimeConfig(
        domain=domain,
        run_id=run_id,
        language=language,
        viewport_kind=viewport_kind,
        state=state,
        user_tier=user_tier,
    )
