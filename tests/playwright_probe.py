"""Playwright readiness probe — no downloads, no installs.

Used by the happy-path E2E acceptance test to decide whether to run or skip.
Never calls playwright install; only detects binary presence.

Inside the Docker image (Dockerfile.e2e), PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
is set at build time and the binaries are pre-installed, so the probe always
returns (True, 'ok') there.

Outside Docker (e.g. plain CI or a developer machine without Playwright installed),
the probe returns (False, reason) and the test is SKIPPED, not FAILED.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _chromium_candidates() -> list[Path]:
    """Return candidate paths where Playwright stores Chromium binaries."""
    candidates: list[Path] = []

    # 1. Explicit override via env — checked first and treated as authoritative.
    #    Inside Dockerfile.e2e: PLAYWRIGHT_BROWSERS_PATH=/ms-playwright (pre-installed).
    #    Inside CI safety test: set to a tmp dir that has no binaries.
    env_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "").strip()
    if env_path:
        root = Path(env_path)
        candidates.extend(root.rglob("chrome"))
        candidates.extend(root.rglob("chromium"))
        candidates.extend(root.rglob("chrome.exe"))
        return candidates  # env override is authoritative — only look here

    # 2. Default Playwright cache locations per OS (developer machines).
    home = Path.home()
    if sys.platform == "darwin":
        default_roots = [
            home / "Library" / "Caches" / "ms-playwright",
            home / ".cache" / "ms-playwright",
        ]
    elif sys.platform == "win32":
        appdata = os.environ.get("LOCALAPPDATA", str(home / "AppData" / "Local"))
        default_roots = [Path(appdata) / "ms-playwright"]
    else:  # Linux / generic CI
        default_roots = [
            home / ".cache" / "ms-playwright",
            Path("/ms-playwright"),  # Docker image path
        ]

    for root in default_roots:
        if root.exists():
            candidates.extend(root.rglob("chrome"))
            candidates.extend(root.rglob("chromium"))
            candidates.extend(root.rglob("chrome.exe"))
    return candidates


def playwright_ready() -> tuple[bool, str]:
    """Return (True, 'ok') if Playwright can launch Chromium; (False, reason) otherwise.

    Does NOT call playwright install or download anything.
    Inside Dockerfile.e2e the result is deterministically (True, 'ok').
    """
    found = [p for p in _chromium_candidates() if p.is_file()]
    if not found:
        return False, (
            "Playwright Chromium binary not found. "
            "Run the Docker-based test runner: bash scripts/run_e2e_happy_path.sh"
        )

    # Verify launch actually works (catches permission/corruption issues).
    try:
        import asyncio

        from playwright.async_api import async_playwright

        async def _probe() -> None:
            async with async_playwright() as p:
                browser = await p.chromium.launch(timeout=10_000)
                await browser.close()

        asyncio.run(_probe())
        return True, "ok"
    except ImportError:
        return False, "playwright package not installed (pip install playwright)"
    except Exception as exc:
        msg = str(exc).splitlines()[0][:200]
        return False, f"Playwright Chromium launch failed: {msg}"
