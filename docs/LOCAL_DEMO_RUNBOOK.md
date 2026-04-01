# Local Demo Runbook (UI-only v1.0 Operator Flow)

This runbook reflects the canonical v1.0 operator workflow as a multi-page UI flow. The workflow is intentionally distributed across official product pages and does not require consolidation into a single screen to count as integrated.

## 1) Setup

Use the existing local/dev setup for the repository.

Common local entry points may include:
- the standard app startup flow for local development;
- `run_e2e_happy_path.sh` for end-to-end validation support;
- `Dockerfile.e2e` for containerized validation scenarios.

Open the local app in your browser after startup.

## 2) Workflow Hub

Start from the main workflow hub or entry route exposed by the app.

From there, navigate through the official product pages for the operator flow.

## 3) Seed URL management

Go to the URL management surface.

Use the UI to:
- add seed URLs,
- review saved URLs,
- confirm that the URL list is persisted.

This step is UI-only and does not require curl or CLI interaction.

## 4) Context and capture flow

Navigate to the contexts / runs / pulls pages through the visible UI.

Use the product UI to:
- inspect created runs or contexts,
- review captured artifacts,
- move between the available operator pages.

This flow may span multiple pages, which is acceptable for the v1.0 operator model.

## 5) Review / annotation flow

Use the visible review-related surfaces to inspect reviewable items and persisted state where available.

The goal of the demo is to confirm that the operator can move through the intended workflow using official UI routes rather than hidden or developer-only paths.

## 6) Issues exploration

Open the issues explorer and issue detail pages.

Confirm that:
- issues are readable from the operator UI,
- filters (including domain selection and multi-selects) can be used to find specific issues,
- issue detail pages expose persisted evidence,
- the operator can move from summary views to detail views through the UI.

## 7) Expected interpretation

A successful local demo does **not** require every operator step to live on a single page.

The intended v1.0 flow is considered coherent if:
- the operator can complete required steps through official UI surfaces,
- navigation between pages is understandable,
- persisted state supports the workflow,
- the flow does not depend on hidden routes or manual developer-only intervention.

## 8) Notes

All steps in this runbook are intended to be UI-only.

No curl or CLI commands are required for the core operator walkthrough beyond initial local setup.