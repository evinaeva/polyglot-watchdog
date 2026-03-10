"""Playwright readiness probe — no downloads, no installs.

Used by the happy-path E2E acceptance test to decide whether to run or skip.
Never calls playwright install; only detects binary presence.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _chromium_candidates() -> list[Path]:
    """Return candidate paths where Playwright stores Chromium binaries."""
    candidates: list[Path] = []

    # 1. Explicit override via env (matches test fixture that forces missing browsers)
    env_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "").strip()
    if env_path:
        root = Path(env_path)
        candidates.extend(root.rglob("chrome"))
        candidates.extend(root.rglob("chromium"))
        candidates.extend(root.rglob("chrome.exe"))
        return candidates  # env override is authoritative — if set, only look there

    # 2. Default Playwright cache locations per OS
    home = Path.home()
    if sys.platform == "darwin":
        default_roots = [
            home / "Library" / "Caches" / "ms-playwright",
            home / ".cache" / "ms-playwright",
        ]
    elif sys.platform == "win32":
        appdata = os.environ.get("LOCALAPPDATA", str(home / "AppData" / "Local"))
        default_roots = [Path(appdata) / "ms-playwright"]
    else:  # Linux / CI
        default_roots = [
            home / ".cache" / "ms-playwright",
            Path("/ms-playwright"),
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
    """
    # Quick binary-presence check first (fast path)
    found = [p for p in _chromium_candidates() if p.is_file()]
    if not found:
        return False, (
            "Playwright Chromium binary not found in cache. "
            "Run: playwright install chromium"
        )

    # Verify launch actually works (catches permission/corruption issues)
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
