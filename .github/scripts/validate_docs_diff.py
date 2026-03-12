#!/usr/bin/env python3
"""Validate changed files against docs auto-sync allowlist/blacklist."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ALLOWED_PREFIXES = ("docs/", "spec/", "contract/schemas/")
ALLOWED_ROOT_FILES = {"RELEASE_CRITERIA.md", "README.md", "APPLYING_STREAM1.md"}
BLACKLIST = {
    "contract/watchdog_contract_v1.0.md",
    "Dockerfile",
    "Dockerfile.e2e",
    "cloudbuild.yaml",
    "requirements.txt",
}


def is_allowed(path: str) -> bool:
    if path in ALLOWED_ROOT_FILES:
        return True
    return path.startswith(ALLOWED_PREFIXES)


def get_changed_name_status(ref: str) -> list[tuple[str, str]]:
    result = subprocess.run(
        ["git", "diff", "--name-status", ref],
        check=True,
        capture_output=True,
        text=True,
    )
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
