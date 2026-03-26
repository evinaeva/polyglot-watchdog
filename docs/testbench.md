# Internal Module Testbench

The `/testbench` page is an **INTERNAL TEST PAGE / NON-PRODUCTION** manual harness for pipeline modules.

It is intended for currently registered modules in `app/testbench.py`; it is not a placeholder page for unreleased future phases.

## Route

- Path: `/testbench`
- Server APIs:
  - `GET /api/testbench/modules`
  - `POST /api/testbench/run`

## Test data model (suite-only)

Only universal suite files are supported in each module phase folder:

- `*.suite.json`
- `*.tests.json`
- `suite.json`

Example:

```txt
tests/modules/phase5/phase5-normalization.suite.json
```

## Universal suite format

```json
{
  "suite_version": "1.0",
  "phase": "phase5",
  "module_id": "phase5_normalization",
  "module_title": "Phase 5 — Normalization",
  "description": "Deterministic normalization checks.",
  "source": "generated",
  "test_cases": [
    {
      "id": "TC-001",
      "title": "Remove zero-width and normalize line endings",
      "priority": "high",
      "tags": ["normalization", "unicode"],
      "input": {"text": "Hello\u200B\r\nWorld"},
      "expected": {"normalized_text": "Hello\nWorld"},
      "assertions": [
        {"kind": "equals", "path": "normalized_text"}
      ],
      "notes": "Sample deterministic normalization check."
    }
  ]
}
```

Required top-level fields for discoverability:

- `suite_version`
- `phase`
- `module_id`
- `module_title`
- `test_cases` (array)

Recommended per-case fields:

- `id`
- `title`
- `input`
- `expected`
- `assertions`

Optional per-case fields:

- `priority`
- `tags`
- `notes`

## Normalized internal case model

Each discovered suite case is normalized to:

- `source_type` (`suite`)
- `source_file`
- `suite_version`
- `phase`
- `module_id`
- `module_title`
- `case_id`
- `case_key`
- `title`
- `priority`
- `tags`
- `input`
- `expected`
- `assertions`
- `notes`

## Discovery behavior

For each module folder `tests/modules/<phase>/`:

1. Load matching `*.suite.json` files.
2. Load matching `*.tests.json` files.
3. Load `suite.json` if present.

If no matching suite files exist, testbench returns:

- `NO TEST FILES FOUND. Add suite files (*.suite.json / *.tests.json / suite.json).`

## Assertion support

Supported assertion kinds:

- `equals`
- `deep_contains`
- `schema_match`
- `field_absent`
- `field_present`
- `custom_message_only`

If assertions are present, assertion results determine PASS/FAIL.
If assertions are absent, the module default validator is used.

## UI behavior

Case selection and metadata display:

- case id
- title
- source type
- source file
- priority
- tags

Run panel shows:

- normalized input
- expected payload
- actual output
- assertion results
- validation messages
- status
- duration
- errors

## Generator workflow

For generator-produced test packs (including GPT-generated output):

1. Write one suite file per module or test pack.
2. Put all cases under top-level `test_cases`.
3. Put execution data in `input`.
4. Put expected comparison data in `expected`.
5. Add optional assertion metadata in `assertions`.

## Adding a new module

1. Add a `ModuleConfig` entry in `app/testbench.py`.
2. Add suite files under `tests/modules/<phase>/`.
3. Wire `runner(payload)` when ready.
4. Optional: add module-specific default validator.
