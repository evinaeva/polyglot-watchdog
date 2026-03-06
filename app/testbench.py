"""Internal module testbench registry, suite discovery, and runners."""

from __future__ import annotations

import json
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from pipeline.schema_validator import SchemaValidationError, validate

BASE_DIR = Path(__file__).resolve().parents[1]

ModuleRunner = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class ModuleConfig:
    module_id: str
    title: str
    phase: str
    status: str
    description: str
    input_artifacts: list[str]
    output_artifacts: list[str]
    schema_refs: list[str]
    test_data_path: str
    runner: ModuleRunner | None
    validator: Callable[[dict[str, Any], dict[str, Any]], list[str]] | None = None


def _phase5_runner(payload: dict[str, Any]) -> dict[str, Any]:
    from pipeline.phase5_normalizer import normalize_text

    text = str(payload.get("text", ""))
    return {"normalized_text": normalize_text(text)}


def _phase5_validator(payload: dict[str, Any], output: dict[str, Any]) -> list[str]:
    expected = payload.get("expected_normalized_text")
    if expected is not None and output.get("normalized_text") != expected:
        return ["normalized_text does not match expected_normalized_text"]
    return []


def _schema_only_validator(payload: dict[str, Any], output: dict[str, Any]) -> list[str]:
    artifact_name = payload.get("validate_artifact")
    artifact_data = payload.get("artifact_data", output)
    if not artifact_name:
        return ["TODO: no validate_artifact specified in test input"]
    try:
        validate(str(artifact_name), artifact_data)
        return [f"Schema validation passed for artifact '{artifact_name}'"]
    except SchemaValidationError as exc:
        return [str(exc)]


MODULE_REGISTRY: list[ModuleConfig] = [
    ModuleConfig(
        module_id="phase0_url_discovery",
        title="Phase 0: URL Discovery",
        phase="0",
        status="partial",
        description="Discovers canonical URLs and emits url_inventory.json.",
        input_artifacts=["domain", "optional:url_rules.json"],
        output_artifacts=["url_inventory.json"],
        schema_refs=["contract/schemas/url_inventory.schema.json", "contract/schemas/url_rules.schema.json"],
        test_data_path="tests/modules/phase0",
        runner=None,
        validator=_schema_only_validator,
    ),
    ModuleConfig(
        module_id="phase1_data_collection",
        title="Phase 1: Data Collection",
        phase="1",
        status="partial",
        description="Collects page screenshots and extracted items.",
        input_artifacts=["url_inventory.json"],
        output_artifacts=["page_screenshots.json", "collected_items.json", "universal_sections.json"],
        schema_refs=[
            "contract/schemas/page_screenshots.schema.json",
            "contract/schemas/collected_items.schema.json",
            "contract/schemas/universal_sections.schema.json",
        ],
        test_data_path="tests/modules/phase1",
        runner=None,
        validator=_schema_only_validator,
    ),
    ModuleConfig(
        module_id="phase2_annotation_rules",
        title="Phase 2: Annotation / Template Rules",
        phase="2",
        status="partial",
        description="Stores template_rules decisions for item-level handling.",
        input_artifacts=["item_id", "url", "rule_type", "optional:note"],
        output_artifacts=["template_rules.json"],
        schema_refs=["contract/schemas/template_rules.schema.json"],
        test_data_path="tests/modules/phase2",
        runner=None,
        validator=_schema_only_validator,
    ),
    ModuleConfig(
        module_id="phase3_reference_build",
        title="Phase 3: Eligible Dataset / Reference Build",
        phase="3",
        status="partial",
        description="Builds eligible_dataset.json from pulled artifacts and rules.",
        input_artifacts=["collected_items.json", "template_rules.json"],
        output_artifacts=["eligible_dataset.json"],
        schema_refs=["contract/schemas/eligible_dataset.schema.json"],
        test_data_path="tests/modules/phase3",
        runner=None,
        validator=_schema_only_validator,
    ),
    ModuleConfig(
        module_id="phase5_normalization",
        title="Phase 5: Normalization",
        phase="5",
        status="implemented",
        description="Deterministic text normalization preserving significant spacing.",
        input_artifacts=["text"],
        output_artifacts=["normalized_text"],
        schema_refs=[],
        test_data_path="tests/modules/phase5",
        runner=_phase5_runner,
        validator=_phase5_validator,
    ),
    ModuleConfig(
        module_id="phase6_localization_qa",
        title="Phase 6: Localization QA / Issues Detection",
        phase="6",
        status="partial",
        description="Compares EN and target artifacts and emits issues.json.",
        input_artifacts=["eligible_dataset.json", "collected_items.json", "page_screenshots.json"],
        output_artifacts=["issues.json"],
        schema_refs=["contract/schemas/issues.schema.json"],
        test_data_path="tests/modules/phase6",
        runner=None,
        validator=_schema_only_validator,
    ),
    ModuleConfig(
        module_id="phase_future_placeholder",
        title="Future Module Placeholder",
        phase="future",
        status="not_implemented",
        description="Reserved placeholder for upcoming modules.",
        input_artifacts=["TBD"],
        output_artifacts=["TBD"],
        schema_refs=[],
        test_data_path="tests/modules/future",
        runner=None,
        validator=None,
    ),
]


def _safe_json_load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {}
    return data


def _normalize_suite_case(module: ModuleConfig, suite_file: Path, suite_data: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    case_id = str(case.get("id", "")).strip() or f"{suite_file.stem}-case"
    return {
        "source_type": "suite",
        "source_file": str(suite_file.relative_to(BASE_DIR)),
        "suite_version": str(suite_data.get("suite_version", "1.0")),
        "phase": str(suite_data.get("phase", f"phase{module.phase}")),
        "module_id": str(suite_data.get("module_id", module.module_id)),
        "module_title": str(suite_data.get("module_title", module.title)),
        "case_id": case_id,
        "case_key": f"suite::{suite_file.name}::{case_id}",
        "title": str(case.get("title", case_id)),
        "priority": str(case.get("priority", "normal")),
        "tags": case.get("tags", []) if isinstance(case.get("tags"), list) else [],
        "input": case.get("input", {}),
        "expected": case.get("expected", {}),
        "assertions": case.get("assertions", []) if isinstance(case.get("assertions"), list) else [],
        "notes": str(case.get("notes", "")),
    }


def _load_suite_cases(module: ModuleConfig) -> list[dict[str, Any]]:
    folder = BASE_DIR / module.test_data_path
    patterns = ["*.suite.json", "*.tests.json", "suite.json"]
    files: list[Path] = []
    for pattern in patterns:
        files.extend(sorted(folder.glob(pattern)))

    cases: list[dict[str, Any]] = []
    for suite_file in files:
        suite_data = _safe_json_load(suite_file)
        raw_cases = suite_data.get("test_cases", [])
        if not isinstance(raw_cases, list):
            continue
        for raw_case in raw_cases:
            if isinstance(raw_case, dict):
                cases.append(_normalize_suite_case(module, suite_file, suite_data, raw_case))
    return cases


def _discover_cases(module: ModuleConfig) -> tuple[list[dict[str, Any]], str]:
    suite_cases = _load_suite_cases(module)
    if suite_cases:
        return suite_cases, ""
    return [], "NO TEST FILES FOUND. Add suite files (*.suite.json / *.tests.json / suite.json)."


def _path_get(data: Any, path: str | None) -> tuple[bool, Any]:
    if not path:
        return True, data
    parts = [p for p in path.split(".") if p]
    cur = data
    for part in parts:
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
            continue
        if isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
            continue
        return False, None
    return True, cur


def _deep_contains(actual: Any, expected: Any) -> bool:
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return False
        return all(k in actual and _deep_contains(actual[k], v) for k, v in expected.items())
    if isinstance(expected, list):
        if not isinstance(actual, list):
            return False
        for item in expected:
            if not any(_deep_contains(candidate, item) for candidate in actual):
                return False
        return True
    return actual == expected


def _run_assertions(case: dict[str, Any], output: dict[str, Any]) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    assertions = case.get("assertions", [])
    expected = case.get("expected", {})
    if not isinstance(assertions, list):
        return results

    for idx, assertion in enumerate(assertions):
        if not isinstance(assertion, dict):
            continue
        kind = str(assertion.get("kind", "")).strip()
        path = assertion.get("path")
        message = assertion.get("message", "")
        exists, actual_value = _path_get(output, str(path) if path else None)
        _, expected_value = _path_get(expected, str(path) if path else None)
        ok = True
        detail = ""

        if kind == "equals":
            ok = exists and actual_value == expected_value
            detail = f"expected={expected_value!r} actual={actual_value!r}"
        elif kind == "deep_contains":
            ok = exists and _deep_contains(actual_value, expected_value)
            detail = "actual contains expected subset"
        elif kind == "schema_match":
            artifact_name = assertion.get("artifact") or expected.get("validate_artifact")
            value_for_schema = actual_value if path else output
            if artifact_name:
                try:
                    validate(str(artifact_name), value_for_schema)
                    ok = True
                    detail = f"schema '{artifact_name}' passed"
                except SchemaValidationError as exc:
                    ok = False
                    detail = str(exc)
            else:
                ok = False
                detail = "missing 'artifact' for schema_match assertion"
        elif kind == "field_absent":
            ok = not exists
            detail = f"field '{path}' should be absent"
        elif kind == "field_present":
            ok = exists
            detail = f"field '{path}' should be present"
        elif kind == "custom_message_only":
            ok = True
            detail = str(message or "custom message")
        else:
            ok = False
            detail = f"unsupported assertion kind: {kind}"

        results.append(
            {
                "index": str(idx),
                "kind": kind,
                "path": str(path or ""),
                "status": "PASS" if ok else "FAIL",
                "message": str(message or detail),
                "detail": detail,
            }
        )
    return results


def get_modules() -> list[dict[str, Any]]:
    modules: list[dict[str, Any]] = []
    for module in MODULE_REGISTRY:
        test_cases, cases_message = _discover_cases(module)
        modules.append(
            {
                "module_id": module.module_id,
                "title": module.title,
                "phase": module.phase,
                "status": module.status,
                "description": module.description,
                "input_artifacts": module.input_artifacts,
                "output_artifacts": module.output_artifacts,
                "schema_refs": module.schema_refs,
                "test_data_path": module.test_data_path,
                "cases_message": cases_message,
                "test_cases": test_cases,
            }
        )
    return modules


def run_module_test(module_id: str, case_key: str | None, inline_payload: dict[str, Any] | None) -> dict[str, Any]:
    module = next((m for m in MODULE_REGISTRY if m.module_id == module_id), None)
    if module is None:
        return {"status": "ERROR", "error": f"Unknown module_id: {module_id}"}

    started = time.perf_counter()
    discovered_cases, _ = _discover_cases(module)
    selected_case = next((c for c in discovered_cases if c.get("case_key") == case_key or c.get("case_id") == case_key), None)

    if selected_case is None:
        selected_case = {
            "source_type": "suite",
            "source_file": "inline",
            "suite_version": "inline",
            "phase": f"phase{module.phase}",
            "module_id": module.module_id,
            "module_title": module.title,
            "case_id": "INLINE",
            "case_key": "INLINE",
            "title": "Inline payload",
            "priority": "normal",
            "tags": ["inline"],
            "input": inline_payload or {},
            "expected": {},
            "assertions": [],
            "notes": "",
        }

    payload = selected_case.get("input") if isinstance(selected_case.get("input"), dict) else {}

    if module.runner is None:
        return {
            "status": "NOT_IMPLEMENTED",
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            "case": selected_case,
            "input": payload,
            "expected": selected_case.get("expected", {}),
            "output": None,
            "assertion_results": [],
            "validation_messages": ["Runner TODO: connect real execution adapter for this module."],
            "error": "",
        }

    try:
        output = module.runner(payload)
        assertion_results = _run_assertions(selected_case, output)
        validation_messages: list[str] = []
        if assertion_results:
            validation_messages = [f"{item['status']} {item['kind']} {item['path']} {item['message']}" for item in assertion_results]
        elif module.validator:
            validation_messages = module.validator(payload, output)

        status = "PASS"
        if any(item.get("status") == "FAIL" for item in assertion_results):
            status = "FAIL"
        elif any(message.startswith("STOP:") or "does not match" in message for message in validation_messages):
            status = "FAIL"

        return {
            "status": status,
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            "case": selected_case,
            "input": payload,
            "expected": selected_case.get("expected", {}),
            "output": output,
            "assertion_results": assertion_results,
            "validation_messages": validation_messages,
            "error": "",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "ERROR",
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            "case": selected_case,
            "input": payload,
            "expected": selected_case.get("expected", {}),
            "output": None,
            "assertion_results": [],
            "validation_messages": [],
            "error": f"{exc}\n{traceback.format_exc()}",
        }
