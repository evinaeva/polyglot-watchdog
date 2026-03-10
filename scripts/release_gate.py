#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRUTH_SURFACES = [
    ROOT / "README.md",
    ROOT / "docs/ABOUT_PAGE_COPY.md",
    ROOT / "docs/PRODUCT_TRUTHSET.md",
]
AUDIT_PATH = ROOT / "docs/RELEASE_READINESS.md"
EVIDENCE_PATH = ROOT / "docs/RELEASE_EVIDENCE.md"

PRE_PROD_PHRASE = "late prototype / pre-production / operator-console-in-progress"
PROD_PHRASE = "production-ready for the documented v1.0 scope"


def extract_gate_state(text: str) -> str:
    if "Messaging state: **pre_production**" in text:
        return "pre_production"
    if "Messaging state: **production_ready_v1_scope**" in text:
        return "production_ready_v1_scope"
    return "unknown"


def audit_has_non_pass_status(text: str) -> bool:
    return "| **fail** |" in text or "| unknown |" in text or "| **fail**" in text


def main() -> int:
    errors: list[str] = []

    if not AUDIT_PATH.exists():
        errors.append("missing docs/RELEASE_READINESS.md")
        gate_state = "unknown"
        audit_text = ""
    else:
        audit_text = AUDIT_PATH.read_text(encoding="utf-8")
        gate_state = extract_gate_state(audit_text)
        if gate_state == "unknown":
            errors.append("unable to parse messaging state from docs/RELEASE_READINESS.md")

    if not EVIDENCE_PATH.exists():
        errors.append("missing docs/RELEASE_EVIDENCE.md")

    truth_texts = []
    for path in TRUTH_SURFACES:
        if not path.exists():
            errors.append(f"missing truth surface: {path.relative_to(ROOT)}")
            continue
        truth_texts.append((path, path.read_text(encoding="utf-8")))

    preprod_missing = [
        str(path.relative_to(ROOT))
        for path, text in truth_texts
        if PRE_PROD_PHRASE not in text
    ]
    if preprod_missing:
        errors.append(f"pre-production phrase missing in: {', '.join(preprod_missing)}")

    prod_present = [
        str(path.relative_to(ROOT))
        for path, text in truth_texts
        if PROD_PHRASE in text
    ]

    if prod_present and gate_state != "production_ready_v1_scope":
        errors.append(
            "production-ready wording found while gate state is not production_ready_v1_scope: "
            + ", ".join(prod_present)
        )

    if gate_state == "production_ready_v1_scope" and audit_has_non_pass_status(audit_text):
        errors.append("gate marked passed but audit table still contains fail/unknown statuses")

    for path, text in truth_texts:
        if "OCR / Phase 4" not in text:
            errors.append(f"deferred scope mention missing OCR / Phase 4 in {path.relative_to(ROOT)}")
        if "manual seed URL workflow" not in text:
            errors.append(
                f"deferred scope mention missing manual seed URL workflow in {path.relative_to(ROOT)}"
            )

    forbidden = [
        "mostly production-ready",
        "basically production-ready",
        "production-ready except",
        "all mock",
        "no phases implemented",
    ]
    for path, text in truth_texts:
        lower = text.lower()
        for phrase in forbidden:
            if phrase in lower:
                errors.append(f"forbidden phrase '{phrase}' found in {path.relative_to(ROOT)}")

    if errors:
        for err in errors:
            print(f"[release-gate] ERROR: {err}")
        return 1

    print("[release-gate] PASS: messaging and release-doc gate checks succeeded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
