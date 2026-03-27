from __future__ import annotations

import html

from app.server_utils import _as_bool, _as_float, _as_int, _coalesce, _first_present


def _h(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def _llm_review_display(latest_job: dict | None, telemetry_payload: object, telemetry_exists: bool, workflow_state: str) -> dict[str, str]:
    in_progress = str((latest_job or {}).get("status", "")).strip().lower() in {"running", "queued"} or str((latest_job or {}).get("stage", "")).strip().lower() in {
        "queued",
        "preparing_target_run",
        "running_target_capture",
        "running_comparison",
    }
    completed = str((latest_job or {}).get("status", "")).strip().lower() in {"succeeded", "failed", "error"} or str((latest_job or {}).get("stage", "")).strip().lower() in {
        "completed",
        "running_comparison_failed",
        "running_target_capture_failed",
    }

    state = "Telemetry not evaluated yet."
    warning = ""
    payload = telemetry_payload if isinstance(telemetry_payload, dict) else None
    malformed = telemetry_exists and payload is None
    if not telemetry_exists:
        if workflow_state in {"preparing_payload", "failed_before_llm", "prepared_for_llm"}:
            state = "LLM stage not started"
        elif in_progress:
            state = "LLM review not reached yet"
        elif completed:
            state = "LLM telemetry missing"
        else:
            state = "LLM telemetry unavailable"
    elif malformed:
        state = "LLM telemetry malformed"
        warning = "Telemetry file exists but is malformed; showing unavailable placeholders."
        payload = {}

    payload = payload or {}
    estimated_tokens = payload.get("estimated_tokens") if isinstance(payload.get("estimated_tokens"), dict) else {}
    actual_tokens = payload.get("actual_tokens") if isinstance(payload.get("actual_tokens"), dict) else {}
    costs = payload.get("cost_usd") if isinstance(payload.get("cost_usd"), dict) else {}

    llm_requested = _as_bool(_first_present(payload, "llm_requested", "request_sent"))
    requested_text = (
        "no real LLM request was sent"
        if llm_requested is False
        else "yes"
        if llm_requested is True
        else "unknown"
    )

    batches_attempted = _as_int(_first_present(payload, "llm_batches_attempted", "batches_attempted", "attempted_batches"))
    batches_succeeded = _as_int(_first_present(payload, "llm_batches_succeeded", "batches_succeeded", "successful_batches"))
    batches_failed = _as_int(_first_present(payload, "llm_batches_failed", "batches_failed", "failed_batches"))
    responses_received = _as_int(_first_present(payload, "responses_received", "response_count"))
    fallback_batches = _as_int(_first_present(payload, "fallback_batches", "batches_fallback"))
    fallback_items = _as_int(_first_present(payload, "fallback_items", "items_fallback"))
    used_fallback = _as_bool(_first_present(payload, "used_fallback"))

    fallback_state = "N/A"
    if batches_attempted > 0:
        if batches_succeeded == 0 and (fallback_batches > 0 or batches_failed >= batches_attempted):
            fallback_state = "Full fallback"
        elif fallback_batches > 0 or fallback_items > 0 or (batches_succeeded > 0 and batches_failed > 0):
            fallback_state = "Partial fallback"
        elif batches_succeeded > 0 and batches_failed == 0 and fallback_batches == 0 and fallback_items == 0:
            fallback_state = "Fully LLM-backed"
        else:
            fallback_state = "Mixed/unknown"

    est_prompt = _as_int(_first_present(estimated_tokens, "prompt", "input", "prompt_tokens"), _as_int(_first_present(payload, "estimated_prompt_tokens")))
    est_completion = _as_int(_first_present(estimated_tokens, "completion", "output", "completion_tokens"), _as_int(_first_present(payload, "estimated_completion_tokens")))
    est_total = _as_int(_first_present(estimated_tokens, "total", "total_tokens"), est_prompt + est_completion)

    act_prompt = _as_int(_first_present(actual_tokens, "prompt", "input", "prompt_tokens"), _as_int(_first_present(payload, "actual_prompt_tokens")))
    act_completion = _as_int(_first_present(actual_tokens, "completion", "output", "completion_tokens"), _as_int(_first_present(payload, "actual_completion_tokens")))
    act_total = _as_int(_first_present(actual_tokens, "total", "total_tokens"), act_prompt + act_completion)

    configured_provider = str(_first_present(payload, "configured_provider", "provider_configured", "provider") or "—")
    effective_provider = str(
        _first_present(payload, "effective_provider", "provider_effective", "provider")
        or (configured_provider if configured_provider != "—" else None)
        or "—"
    )
    configured_model = str(_first_present(payload, "configured_model", "model_configured", "model") or "—")
    effective_model = str(_first_present(payload, "effective_model", "model_effective", "model") or "—")
    review_mode = str(_first_present(payload, "review_mode", "mode") or "—")
    provider_type = str(_first_present(payload, "provider_type", "provider_kind") or "—")

    if provider_type == "—":
        if llm_requested is False:
            provider_type = "no real LLM request was sent"
        elif fallback_state == "Fully LLM-backed":
            provider_type = "llm"
        elif fallback_state in {"Partial fallback", "Full fallback"}:
            provider_type = "llm+fallback"

    actual_cost = _as_float(_coalesce(_first_present(payload, "actual_cost_usd", "cost_actual_usd"), costs.get("actual")))
    estimated_cost = _as_float(_coalesce(_first_present(payload, "estimated_cost_usd", "cost_estimated_usd"), costs.get("estimated")))
    if actual_cost is not None:
        cost_display = f"${actual_cost:.6f} (actual)"
    elif estimated_cost is not None:
        cost_display = f"${estimated_cost:.6f} (estimated)"
    else:
        cost_display = "unavailable"

    operator_notes: list[str] = []
    if review_mode == "llm" and llm_requested is False:
        operator_notes.append("LLM not executed: provider misconfigured (missing API key or provider)")
    if used_fallback is True or fallback_batches > 0 or fallback_items > 0:
        operator_notes.append(f"Fallback used: {fallback_state}")
    if batches_attempted > 0 and batches_succeeded == 0:
        operator_notes.append("No successful LLM responses")

    summary = f"{state}. Fallback status: {fallback_state}. Cost: {cost_display}."
    if operator_notes:
        summary += " " + "; ".join(operator_notes) + "."

    return {
        "state": state,
        "warning": warning,
        "review_mode": review_mode,
        "provider_type": provider_type,
        "configured_provider": configured_provider,
        "effective_provider": effective_provider,
        "configured_model": configured_model,
        "effective_model": effective_model,
        "llm_requested": requested_text,
        "batches_attempted": str(batches_attempted),
        "batches_succeeded": str(batches_succeeded),
        "batches_failed": str(batches_failed),
        "responses_received": str(responses_received),
        "fallback_batches": str(fallback_batches),
        "fallback_items": str(fallback_items),
        "fallback_state": fallback_state,
        "estimated_tokens": f"prompt={est_prompt}, completion={est_completion}, total={est_total}",
        "actual_tokens": f"prompt={act_prompt}, completion={act_completion}, total={act_total}",
        "cost_display": cost_display,
        "operator_notes": " | ".join(operator_notes) if operator_notes else "none",
        "process_summary": summary,
    }
