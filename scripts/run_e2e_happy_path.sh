#!/usr/bin/env bash
# run_e2e_happy_path.sh — deterministic clean-env happy-path E2E runner.
#
# Builds the Playwright-ready Docker image and runs the e2e_happy_path test suite.
# No host-level Playwright installation is required.
#
# Usage:
#   bash scripts/run_e2e_happy_path.sh
#
# Prerequisites: Docker (any recent version)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)"

echo "==> Building watchdog-e2e image ..."
docker build -f "${REPO_ROOT}/Dockerfile.e2e" -t watchdog-e2e "${REPO_ROOT}"

echo "==> Running happy-path E2E acceptance test ..."
docker run --rm \
  -e PYTHONPATH=/app \
  -e AUTH_MODE=OFF \
  watchdog-e2e

echo "==> Done."
