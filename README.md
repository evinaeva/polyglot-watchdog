# Polyglot Watchdog — Skeleton UI

Minimal skeleton web UI service for Polyglot Watchdog.

This is an early-stage scaffold. No pipeline phases (0–6) are implemented yet.
All data returned by the API endpoints is mock/static.

## Available routes

| Route | Description |
|---|---|
| `/` | Issues explorer (returns results only when filters are applied) |
| `/crawler` | URL crawler page |
| `/pulling` | Content pulling and annotation page |
| `/about` | Glossary (placeholder) |
| `/healthz` | Health check — returns `{"status": "ok"}` |

## What is NOT implemented yet

- Phase 0–6 pipeline logic (crawling, pulling, annotation persistence, OCR, normalization, QA)
- Real GCP storage integration
- Authentication / user tiers
- Any production-ready data

## Run locally

```bash
PORT=8080 python app/skeleton_server.py
```

Verify:
```bash
curl http://localhost:8080/healthz
# {"status": "ok"}
```

## Build and deploy to Cloud Run

```bash
gcloud builds submit \
  --config=cloudbuild.yaml \
  --substitutions=_SERVICE_NAME=polyglot-watchdog,_REGION=europe-west1
```

After deployment, verify:
```bash
curl https://<SERVICE_URL>/healthz
# {"status": "ok"}
```

The service URL is printed at the end of `gcloud builds submit` output,
or retrieve it with:
```bash
gcloud run services describe polyglot-watchdog --region=europe-west1 --format='value(status.url)'
```
