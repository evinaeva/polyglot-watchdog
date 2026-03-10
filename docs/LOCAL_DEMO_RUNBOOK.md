# Local Demo Runbook (UI-only v1.0 Operator Flow)

## 1) Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium   # required for capture
```

## 2) Start app

```bash
AUTH_MODE=OFF PYTHONPATH=. python app/skeleton_server.py
```

---

## Happy-path demo (Playwright-ready environment)

The following steps exercise the full v1.0 operator journey through the UI.
All steps are UI-only — no curl or CLI commands are required.

1. Open **Workflow Hub**: `http://127.0.0.1:8080/workflow`
2. Visit **URLs** (`/urls`), add one or more seed URL(s) for your domain.
3. Return to **Workflow Hub** (`/workflow`), enter your domain and a run ID, click **Load Status**.
4. Click **Start Capture** and wait for `capture.status = ready`.
   - Requires Playwright + Chromium to be installed.
   - If capture fails, see **Prerequisites missing** section below.
5. Click **Refresh** until `capture.status = ready` and `review.status` becomes active.
6. Click **Open Contexts** (`/contexts`) and save review decisions per row  
   (`valid`, `blocked_by_overlay`, or `not_found`).
7. Return to **Workflow Hub**, refresh until `review.status = ready`.
8. Click **Open Pulls** (`/pulls`) and save annotation decisions per row  
   (`eligible`, `exclude`, or `needs-fix`).
9. Return to **Workflow Hub**, click **Generate Eligible Dataset**,  
   then refresh until `eligible_dataset.status = ready`.
10. Click **Generate Issues**, then refresh until `issues.status = ready` (or `empty`).
11. Click **Open Issues** (`/`) and verify the issues explorer is populated.
12. Click into any issue (or visit `/issues/detail`) and confirm evidence is visible  
    (screenshot link and artifact refs).

> **If capture.status = failed**: stop and resolve Playwright prerequisites before  
> continuing. Do not generate synthetic artifacts or bypass the capture step.

---

## Happy-path acceptance test (Playwright-ready runner — clean environment)

This section documents the **deterministic, reproducible** way to execute the full
happy-path E2E acceptance test (`tests/test_workflow_happy_path_e2e.py`) from a
clean environment. No host-level Playwright installation is required.

**Prerequisites:** Docker (any recent version).

**Single command:**

```bash
bash scripts/run_e2e_happy_path.sh
```

This command:
1. Builds `Dockerfile.e2e` — a Python + Playwright/Chromium image where the browser
   is installed at **image build time** (not at runtime).
2. Runs `pytest -m e2e_happy_path -v` inside the container.

Expected output on success:
```
==> Building watchdog-e2e image ...
...
==> Running happy-path E2E acceptance test ...
tests/test_workflow_happy_path_e2e.py::test_full_v1_operator_journey_happy_path PASSED
1 passed in Xs
==> Done.
```

Inside the container, `PLAYWRIGHT_BROWSERS_PATH=/ms-playwright` is set at build time,
so `tests/playwright_probe.py` always returns `(True, 'ok')` and the test is never skipped.

Outside the container (plain CI without Playwright), the test is automatically **SKIPPED**,
not FAILED. The default suite still passes.

---

## CI / Prerequisites missing (expected truthful failure)

When Playwright is not installed, the system behaves as follows:

- `POST /api/workflow/start-capture` returns `{"status": "started"}` and launches the runner.
- The runner fails immediately (missing browser binary).
- `GET /api/workflow/status` reports `capture.status = failed` with an error message.
- `GET /api/capture/contexts` returns `404 not_ready`.
- `POST /api/workflow/generate-eligible-dataset` returns `409 not_ready`.
- `POST /api/workflow/generate-issues` returns `409 not_ready`.

This is the correct, truthful behaviour. No synthetic artifacts are generated.

The CI test suite (`tests/test_workflow_status_and_acceptance.py`) asserts all of  
the above and **passes** in a no-Playwright environment.

The happy-path E2E test (`tests/test_workflow_happy_path_e2e.py`) is automatically  
**SKIPPED** (not failed) in environments without Playwright.

---

## Optional developer verification (not part of v1.0 operator flow)

Run CI-safe truthful-failure suite (always passes, Playwright not required):

```bash
PYTHONPATH=. pytest -q tests/test_workflow_status_and_acceptance.py
```

Run happy-path E2E via Docker (requires Docker; no host Playwright needed):

```bash
bash scripts/run_e2e_happy_path.sh
```

Run happy-path E2E directly (requires `playwright install chromium` on host):

```bash
playwright install chromium
PYTHONPATH=. pytest -m e2e_happy_path -v
```

Run full default suite (both; skips what cannot run):

```bash
PYTHONPATH=. pytest -q
```

> Workstream A PASS requires `test_workflow_happy_path_e2e.py` to PASS (not merely skip)  
> in a Playwright-capable environment. The Docker command above satisfies this requirement  
> from a clean environment without any manual prerequisites.
