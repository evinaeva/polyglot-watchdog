# Local Demo Runbook (UI-only v1.0 Operator Flow)

## 1) Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2) Start app

```bash
AUTH_MODE=OFF PYTHONPATH=. python app/skeleton_server.py
```

## 3) Execute full operator workflow (UI only)

1. Open **Workflow Hub**: `http://127.0.0.1:8000/workflow`.
2. Select/create domain by first visiting **URLs** (`/urls`) and adding seed URL(s).
3. Return to **Workflow Hub** (`/workflow`), pick domain, enter run id, click **Load Status**.
4. Click **Start Capture**.
5. Click **Refresh** until `capture.status = ready` and `review.status` moves to `not_ready/in_progress/ready`.
6. Click **Open Contexts** and save review decisions from the table (`valid`, `blocked_by_overlay`, or `not_found`).
7. Return to **Workflow Hub** and refresh until review is `ready`.
8. Click **Open Pulls** and save annotation decisions per row (`eligible`, `exclude`, `needs-fix`).
9. Return to **Workflow Hub**, click **Generate Eligible Dataset**, then refresh until `eligible_dataset.status = ready`.
10. Click **Generate Issues**, then refresh until `issues.status = ready` (or `empty` if no issues).
11. Click **Open Issues** and verify issues explorer is populated from run-scoped backend data.
12. Click **Open First Issue Detail** (or open issue detail from explorer) and confirm evidence is visible (screenshot link and related refs).

If capture fails on Workflow Hub (status `failed`), stop the v1.0 flow and resolve capture runner prerequisites first. Do not proceed with synthetic/manual artifact generation.

## Optional developer verification (not part of v1.0 operator flow)

```bash
PYTHONPATH=. pytest -q tests/test_workflow_status_and_acceptance.py
```


> Workstream A cannot be marked PASS in environments where real capture runner prerequisites are missing, because capture artifacts are not produced and downstream steps stay blocked by design.
