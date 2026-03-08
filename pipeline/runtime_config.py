"""Unified runtime config loaders for pipeline execution entrypoints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from pipeline.interactive_capture import validate_state_name
from pipeline.schema_validator import validate

_ALLOWED_VIEWPORTS = {"desktop", "mobile", "responsive"}


@dataclass(frozen=True)
class Phase1RuntimeConfig:
    domain: str
    run_id: str
    language: str
    viewport_kind: str
    state: str
    user_tier: str | None


def validate_seed_urls_payload(payload: Mapping[str, Any]) -> None:
    """Validate canonical seed_urls payload shape used by runtime planning.

    The canonical payload may include `updated_at`; schema validation is enforced
    against the authoritative contract fields (`domain`, `urls`).
    """
    if not isinstance(payload, Mapping):
        raise ValueError("seed_urls payload must be an object")

    if "updated_at" in payload and payload["updated_at"] is not None and not isinstance(payload["updated_at"], str):
        raise ValueError("seed_urls.updated_at must be a string when present")

    canonical_payload = {
        "domain": payload.get("domain"),
        "urls": payload.get("urls"),
    }
    validate("seed_urls", canonical_payload)


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
    try:
        validate_state_name(state)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc

    return Phase1RuntimeConfig(
        domain=domain,
        run_id=run_id,
        language=language,
        viewport_kind=viewport_kind,
        state=state,
        user_tier=user_tier,
    )
