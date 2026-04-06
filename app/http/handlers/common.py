from __future__ import annotations

from http import HTTPStatus

from app.seed_urls import validate_domain
from app.server_utils import _missing_required_query_params, _require_query_params, _validate_run_id
from app.check_languages_service import _normalize_testsite_domain_key


def require_query_params_or_400(handler: object, query: dict[str, list[str]], *names: str) -> dict[str, str] | None:
    required, missing = _require_query_params(query, *names)
    if missing:
        handler._json_response(_missing_required_query_params(*missing), status=HTTPStatus.BAD_REQUEST)
        return None
    return required


def require_domain_and_run_id_or_400(handler: object, query: dict[str, list[str]], *, normalize_domain: bool = False) -> tuple[str, str] | None:
    required = require_query_params_or_400(handler, query, "domain", "run_id")
    if required is None:
        return None
    try:
        domain = required["domain"]
        if normalize_domain:
            domain = validate_domain(_normalize_testsite_domain_key(domain))
        run_id = _validate_run_id(required["run_id"])
    except ValueError as exc:
        handler._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        return None
    return domain, run_id


def handle_artifact_error(handler: object, exc: Exception) -> bool:
    if isinstance(exc, FileNotFoundError):
        handler._json_response({"status": "not_ready", "error": str(exc)}, status=HTTPStatus.NOT_FOUND)
        return True
    if isinstance(exc, ValueError):
        handler._json_response({"error": str(exc), "status": "artifact_invalid"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
        return True
    return False
