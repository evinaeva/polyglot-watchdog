#!/usr/bin/env python3
"""Shared config loader for docs auto-update scripts."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

CONFIG_ENV_VAR = "DOCS_AUTOUPDATE_CONFIG"
DEFAULT_CONFIG_RELATIVE = Path(".github/scripts/config.json")


def config_root() -> Path:
    try:
        root = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip()
        if root:
            return Path(root)
    except Exception:
        pass
    return Path.cwd()


def runtime_repo_root() -> Path:
    try:
        top = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip()
        if top:
            return Path(top)
    except Exception:
        pass
    return Path.cwd()


def default_config_path() -> Path:
    return config_root() / DEFAULT_CONFIG_RELATIVE


def load_config() -> dict[str, Any]:
    override = os.environ.get(CONFIG_ENV_VAR, "").strip()
    path = Path(override).resolve() if override else default_config_path()
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_repo_path(path_value: str) -> Path:
    return runtime_repo_root() / path_value
