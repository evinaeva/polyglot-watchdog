#!/usr/bin/env python3
"""Ensure cron schedule is synchronized between config and workflow."""

from __future__ import annotations

import json
import re
from pathlib import Path

CONFIG_PATH = Path('.github/docs_autoupdate/config.json')
WORKFLOW_PATH = Path('.github/workflows/docs-ai-sync.yml')


def read_config_cron() -> str:
    config = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
    return str(config['workflows']['docs_ai_sync']['schedule_cron']).strip()


def read_workflow_cron() -> str:
    text = WORKFLOW_PATH.read_text(encoding='utf-8')
    match = re.search(r"(?m)^\s*-\s*cron:\s*['\"]([^'\"]+)['\"]\s*$", text)
    if not match:
        raise RuntimeError('Unable to locate workflow schedule cron value')
    return match.group(1).strip()


def main() -> int:
    config_cron = read_config_cron()
    workflow_cron = read_workflow_cron()
    if config_cron != workflow_cron:
        raise RuntimeError('Cron schedule mismatch between workflow and config')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
