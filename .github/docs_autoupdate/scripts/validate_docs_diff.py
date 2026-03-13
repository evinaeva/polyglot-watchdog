#!/usr/bin/env python3
"""Validate changed files against docs auto-sync allowlist/blacklist."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_loader import load_config

CONFIG = load_config()
ALLOWED_PREFIXES = tuple(CONFIG["docs_rules"]["allowed_prefixes"])
ALLOWED_ROOT_FILES = set(CONFIG["docs_rules"]["allowed_root_files"])
BLACKLIST = set(CONFIG["docs_rules"]["blacklist"])
IGNORED_RUNTIME_PREFIXES = tuple(CONFIG["paths"]["runtime_temp_prefixes"])

if not ALLOWED_PREFIXES:
    raise RuntimeError("Config error: allowed_prefixes cannot be empty")

if not BLACKLIST:
    raise RuntimeError("Config error: blacklist cannot be empty")


def is_ignored_runtime_path(path: str) -> bool:
    return path.startswith(IGNORED_RUNTIME_PREFIXES)


def is_allowed(path: str) -> bool:
    if path in ALLOWED_ROOT_FILES:
        return True
    return path.startswith(ALLOWED_PREFIXES)


def get_changed_name_status(ref: str) -> list[tuple[str, str]]:
    result = subprocess.run(["git", "diff", "--name-status", ref], check=True, capture_output=True, text=True)
    entries: list[tuple[str, str]] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        status, file_path = line.split("\t", 1)
        entries.append((status.strip(), file_path.strip()))

    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        check=True,
        capture_output=True,
        text=True,
    )
    for line in untracked.stdout.splitlines():
        if line.strip():
            entries.append(("A", line.strip()))
    return entries


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ref", default="HEAD", help="Diff against git ref (default: HEAD)")
    args = parser.parse_args()

    entries = get_changed_name_status(args.ref)
    disallowed = []
    blacklisted = []
    deleted = []

    for status, path in entries:
        if is_ignored_runtime_path(path):
            continue
        if path in BLACKLIST:
            blacklisted.append(path)
        if not is_allowed(path):
            disallowed.append(path)
        if status.startswith("D"):
            deleted.append(path)

    if blacklisted:
        print("Blacklisted files were modified:", file=sys.stderr)
        for path in sorted(set(blacklisted)):
            print(f" - {path}", file=sys.stderr)
        return 1

    if disallowed:
        print("Files outside allowlist were modified:", file=sys.stderr)
        for path in sorted(set(disallowed)):
            print(f" - {path}", file=sys.stderr)
        return 1

    if deleted:
        print("File deletions are not allowed:", file=sys.stderr)
        for path in sorted(set(deleted)):
            print(f" - {path}", file=sys.stderr)
        return 1

    print("Diff validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
