# Operator Read Routes (Stage A, release-grade artifact-backed API)

These operator read routes are backed strictly by canonical persisted artifacts. No UI fixtures or synthetic fallback business data are used.

## Canonical artifact mapping

- Phase 1: `page_screenshots.json`, `collected_items.json`, `universal_sections.json`
- Phase 2: `template_rules.json` (loaded via `_load_phase2_decisions`)
- Phase 6: `issues.json`

## Error model

- Missing required query params: `400` with `{"error":"missing_required_query_params","missing":[...]} ` (ordered by route-required param list).
- Required artifact not present yet: `404` with `{"error":"<artifact> artifact missing","status":"not_ready"}`
- Artifact read/type failure (read error or wrong JSON type): `500` with `{"status":"artifact_invalid","error":"<artifact>.json artifact_invalid|artifact_read_failed"}`
- `status` is always `artifact_invalid` for both read failures and type-validation failures; clients should inspect `error` for detail.

## Routes

### `GET /api/pulls`

Query: `domain`, `run_id`, optional `url`, `state`, `language`, `viewport_kind`, `user_tier`.

Notes:
- This is the **pull/annotation read model**, not git pulls.
- Requires `collected_items.json`; otherwise `404 not_ready` with `collected_items artifact missing`.
- Adds synthetic universal rows only from persisted `universal_sections.json`.
- `user_tier` normalization: null/empty/`"none"`/`"null"` (case-insensitive) => `null`, otherwise trimmed string.
- Returns:

```json
{
  "rows": [
    {
      "item_id": "...",
      "url": "...",
      "state": "...",
      "language": "...",
      "viewport_kind": "...",
      "user_tier": null,
      "element_type": "...",
      "text": "...",
      "not_found": false,
      "decision": "..."
    }
  ],
  "missing_universal_sections": false
}
```

Decision mapping is by `(item_id, url)` from Phase 2 persisted decisions.

### `GET /api/rules`

Query: `domain`, `run_id`.

Returns `{"rules": [...]}` from `template_rules.json` via `_load_phase2_decisions`.

Corrupted Phase 2 artifact shape fails closed with `500 artifact_invalid`.

### `GET /api/issues`

Query: `domain`, `run_id`, optional filters: `q`, `type`, `language`, `severity`, `state`, `url`, `domain_filter`.

Filter semantics:
- exact match: `type` (matches `category`), `language`, `severity`, `state`
- substring match: `q` (matches category/message/url), `url` (matches evidence.url), `domain_filter` (matches evidence.url)

Returns deterministic sorted issues by `id` using numeric-first ordering (`"2"` before `"10"`; non-numeric ids sort lexicographically after numeric ids).

`404 not_ready` if `issues.json` is missing (`issues artifact missing`).

```json
{"issues":[...],"count":N}
```

### `GET /api/issues/export?format=csv`

Uses the same filtered subset as `/api/issues` and exports stable CSV columns:

`id,category,severity,language,state,url,message`

Content type: `text/csv; charset=utf-8`.

CSV is single-line per record: message values have CR/LF normalized to spaces before writing.

### `GET /api/issues/detail`

Query: `domain`, `run_id`, `id`.

- `404 not_ready` if `issues.json` is missing (`issues artifact missing`).
- `404` if the issue id is unknown.
- `200` with partial drilldown when item/page resolution is unavailable.

Minimum response shape:

```json
{
  "issue": {},
  "drilldown": {
    "screenshot_uri": "...",
    "page": null,
    "element": null,
    "artifact_refs": {
      "issues": "domain/run_id/issues.json",
      "page_screenshots": "domain/run_id/page_screenshots.json",
      "collected_items": "domain/run_id/collected_items.json"
    }
  }
}
```

### `GET /api/capture-contexts` (alias: `/api/capture/contexts`)

Query: `domain`, `run_id`.

Requires `page_screenshots.json` (`404 not_ready` if missing, `page_screenshots artifact missing`) and returns contexts with `elements_count` derived from `collected_items.json` when present.

Contexts are returned in deterministic order by `(capture_context_id, page_id, url)`.
