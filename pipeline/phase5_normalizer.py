"""Phase 5 — deterministic text normalization.

Contract: contract/watchdog_contract_v1.0.md §6 Phase 5
Rule: normalization MUST be deterministic and MUST NOT normalize away double spaces.
"""

from __future__ import annotations

import re
import unicodedata

_BIDI_RE = re.compile(r"[\u200E\u200F\u202A\u202B\u202C\u202D\u202E]")
_ZERO_WIDTH_RE = re.compile(r"[\u200b\u200c\u200d\ufeff]")


def normalize_text(text: str) -> str:
    """Normalize text deterministically while preserving user-visible spacing.

    This function intentionally does not collapse or strip repeated internal spaces.
    """
    if text is None:
        return ""
    out = unicodedata.normalize("NFC", text)
    out = out.replace("\r\n", "\n").replace("\r", "\n")
    out = _BIDI_RE.sub("", out)
    out = _ZERO_WIDTH_RE.sub("", out)
    return out
