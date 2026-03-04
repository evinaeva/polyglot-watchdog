import json
from datetime import datetime, timezone


def log_event(event: str, **fields) -> None:
    """
    Emit a structured log event as JSON.

    Each log contains the event name and an ISO8601 UTC timestamp. Additional
    keyword arguments are included as extra fields in the payload. Logs are
    printed to stdout, which makes them available in Cloud Run logs.
    """
    payload = {
        "event": event,
        "timestamp_utc": datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
        **fields,
    }
    print(json.dumps(payload, ensure_ascii=False))
