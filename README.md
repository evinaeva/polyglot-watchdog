# Polyglot Watchdog — Skeleton UI

Minimal skeleton web UI service for Polyglot Watchdog.

Operator UI is now connected to runtime/storage artifacts for core flows:

- `/urls`: persisted seed URL source-of-truth (`manual/seed_urls.json`) with normalization/dedup and row upsert.
- `/pulling`: reads real `collected_items.json` by `domain + run_id` and writes phase2 decisions via `/api/phase2/rule`.
- `/`: issues explorer reads real `issues.json` by `domain + run_id`.
- Capture review/rerun endpoints are wired to Phase 1 exact-context rerun APIs.
- `/api/domains` dropdown source is temporarily a fixed list (`MOCK_DOMAINS`) until storage-backed domain indexing is introduced.
- `/api/rules` remains a local/in-memory helper endpoint; durable annotation persistence should use `POST /api/phase2/rule`.

## Available routes

| Route | Description |
|---|---|
| `/login` | Login screen (used only when auth mode is ON) |
| `/` | Issues explorer (table fills after Apply Query; `q` may be empty, but `domain` + `run_id` are required) |
| `/crawler` | URL crawler page |
| `/pulling` | Content pulling and annotation page |
| `/about` | Glossary (placeholder) |
| `/testbench` | Internal testbench |

## Authentication and CSRF

## Auth mode switch (one line)

In `app/skeleton_server.py` there is a single toggle:

```python
AUTH_MODE = "ON"
```

Set it to `"OFF"` to disable login/session/CSRF checks and make all UI/API routes publicly accessible (no redirects to `/login`).

⚠️ `AUTH_MODE = "OFF"` means public access for anyone with the URL.

The web app now uses the same model as PutThatBase:

- Password login form on `/login`.
- Signed session cookie (`pw_session`) after successful login.
- CSRF cookie/token (`pw_csrf`) validation for all mutating requests (`POST`/`PUT`).
- Protected pages and API endpoints redirect/deny access when unauthenticated (only when auth mode is ON).
- Logout via `POST /logout`, which clears both session and CSRF cookies.

Cookie policy:

- `HttpOnly=true` for `pw_session`.
- `SameSite=Lax` for session and CSRF cookies.
- `Secure=true` automatically when running in Cloud Run (`K_SERVICE` present) or `ENV=production`.
- Default max age: 8 hours (`SESSION_MAX_AGE_SECONDS`, minimum 5 minutes).

## Required environment variables

Do not hardcode secrets in code. Inject from Cloud Run + Secret Manager:

- `WATCHDOG_PASSWORD`: login password for the web UI.
- `SESSION_SIGNING_SECRET`: secret key used to sign session cookies.
- `SESSION_MAX_AGE_SECONDS` (optional): session/csrf max age.

## Run locally

```bash
export WATCHDOG_PASSWORD='your-local-password'
export SESSION_SIGNING_SECRET='long-random-local-secret'
PORT=8080 python app/skeleton_server.py
```

Verify:
```bash
curl -i http://localhost:8080/
```
(with `AUTH_MODE="ON"`, should redirect to `/login` until authenticated).

## Build and deploy to Cloud Run

```bash
gcloud builds submit \
  --config=cloudbuild.yaml \
  --substitutions=_SERVICE_NAME=polyglot-watchdog,_REGION=europe-west1
```

`cloudbuild.yaml` now deploys with Secret Manager bindings:

- `WATCHDOG_PASSWORD=WATCHDOG_PASSWORD:latest`
- `SESSION_SIGNING_SECRET=SESSION_SIGNING_SECRET:latest`

Create/update those secrets first:

```bash
printf '%s' 'your-strong-password' | gcloud secrets versions add WATCHDOG_PASSWORD --data-file=-
printf '%s' 'your-long-random-signing-secret' | gcloud secrets versions add SESSION_SIGNING_SECRET --data-file=-
```

After deployment, verify:

```bash
curl -i https://<SERVICE_URL>/login
```

The service URL is printed at the end of `gcloud builds submit` output,
or retrieve it with:

```bash
gcloud run services describe polyglot-watchdog --region=europe-west1 --format='value(status.url)'
```

## Internal testbench

- Manual module playground: `/testbench`
- Preferred test data format: universal suite files (`*.suite.json`, `*.tests.json`, `suite.json`)
- Setup and extension guide: `docs/testbench.md`


## Operator flow (local)

1. Configure URLs in `/urls`.
2. Trigger capture with `POST /api/phase1/run` (or plan via `POST /api/runs/plan`).
3. Review contexts via `POST /api/capture/review` and rerun exact context via `POST /api/capture/rerun`.
4. Annotate items in `/pulling` and save Phase 2 rules.
5. Run Phase 3 / Phase 6 and inspect real issues on `/`.
