"""Phase 2 — Annotation logic for Polyglot Watchdog.

Contract: contract/watchdog_contract_v1.0.md §6 Phase 2
Schema: contract/schemas/template_rules.schema.json

Key contract rules:
  - Rules are per element per URL (no GLOBAL/DOMAIN/PATH scopes in v1.0).
  - Rule semantics are deterministic and reproducible.
  - Allowed rule_types: IGNORE_ENTIRE_ELEMENT, MASK_VARIABLE, ALWAYS_COLLECT.
"""

from __future__ import annotations

import datetime
import hashlib
from typing import Literal

RuleType = Literal["IGNORE_ENTIRE_ELEMENT", "MASK_VARIABLE", "ALWAYS_COLLECT"]
ALLOWED_RULE_TYPES: set[str] = {"IGNORE_ENTIRE_ELEMENT", "MASK_VARIABLE", "ALWAYS_COLLECT"}


def compute_rule_id(item_id: str, url: str, rule_type: str) -> str:
    """Return stable rule_id = sha1(item_id + url + rule_type)."""
    payload = item_id + url + rule_type
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def make_rule(
    item_id: str,
    url: str,
    rule_type: str,
    note: str | None = None,
    created_at: str | None = None,
) -> dict:
    """Build a single template_rules record.

    Contract §6 Phase 2: per element per URL, deterministic rule_id.
    """
    if rule_type not in ALLOWED_RULE_TYPES:
        raise ValueError(f"Invalid rule_type: {rule_type!r}. Must be one of {ALLOWED_RULE_TYPES}")
    ts = created_at or datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    rule_id = compute_rule_id(item_id, url, rule_type)
    return {
        "rule_id": rule_id,
        "item_id": item_id,
        "url": url,
        "rule_type": rule_type,
        "created_at": ts,
        "note": note,
    }


def apply_rules_to_items(
    collected_items: list[dict],
    template_rules: list[dict],
) -> dict[str, dict]:
    """Return a mapping of item_id -> effective rule (last wins per item_id+url).

    Per Contract §6 Phase 2: rules are per element per URL.
    """
    rules_map: dict[str, dict] = {}
    # Sort by created_at for deterministic precedence
    for rule in sorted(template_rules, key=lambda r: (r["created_at"], r["rule_id"])):
        key = rule["item_id"] + "::" + rule["url"]
        rules_map[key] = rule
    return rules_map


def filter_items_by_rules(
    collected_items: list[dict],
    template_rules: list[dict],
) -> list[dict]:
    """Return items eligible for Phase 3 after applying template_rules.

    - IGNORE_ENTIRE_ELEMENT: exclude from eligible_dataset.
    - MASK_VARIABLE: include but set mask_applied=True.
    - ALWAYS_COLLECT: include unconditionally (mask_applied=False).
    - No rule: include as-is (mask_applied=False).
    """
    rules_map = apply_rules_to_items(collected_items, template_rules)
    result: list[dict] = []
    for item in collected_items:
        key = item["item_id"] + "::" + item["url"]
        rule = rules_map.get(key)
        if rule and rule["rule_type"] == "IGNORE_ENTIRE_ELEMENT":
            continue
        mask_applied = rule is not None and rule["rule_type"] == "MASK_VARIABLE"
        result.append({
            "item_id": item["item_id"],
            "page_id": item.get("page_id"),
            "url": item["url"],
            "language": item["language"],
            "element_type": item.get("element_type"),
            "text": item["text"],
            "mask_applied": mask_applied,
            "page_canonical_key": item.get("page_canonical_key"),
            "logical_match_key": item.get("logical_match_key"),
            "role_hint": item.get("role_hint"),
            "semantic_attrs": item.get("semantic_attrs"),
            "local_path_signature": item.get("local_path_signature"),
            "container_signature": item.get("container_signature"),
            "stable_ordinal": item.get("stable_ordinal"),
        })
    # Sort for determinism — Contract §1
    result.sort(key=lambda i: (i["item_id"], i["url"]))
    return result
