#!/usr/bin/env python3
"""Pre-sync guard: detect whether there is a new merged PR that the docs
AI sync has not yet processed.

Outputs (written to $GITHUB_OUTPUT):
  should_run=true|false
  latest_pr_number=<int or empty>
  latest_pr_merged_at=<ISO string or empty>

Exit codes:
  0  always (failures are soft; should_run defaults to false on error)

Called by docs-ai-sync.yml before the AI sync step.  Schedule runs gate
on should_run==true; workflow_dispatch runs ignore this output entirely.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request
from typing import Any


STATE_REF = "origin/DOCS_AUTOUPDATE"
STATE_PATH = "docs/auto/docs_sync_state.json"


def git_show(ref_path: str) -> str:
    res = subprocess.run(["git", "show", ref_path], capture_output=True, text=True)
    if res.returncode != 0:
        return ""
    return res.stdout


def gh_api_get(url: str, token: str) -> Any:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "check-new-merged-prs",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def write_output(path: str, key: str, value: str) -> None:
    if not path:
        print(f"[guard] {key}={value}")  # log even when no GITHUB_OUTPUT
        return
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"{key}={value}\n")
    print(f"[guard] {key}={value}")


def load_state() -> dict[str, Any]:
    raw = git_show(f"{STATE_REF}:{STATE_PATH}")
    if not raw.strip():
        print("[guard] No prior state found; treating as first run.", file=sys.stderr)
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"[guard] State JSON parse error: {exc}; treating as first run.", file=sys.stderr)
        return {}


def fetch_latest_merged_pr(token: str, repo: str) -> dict[str, Any] | None:
    """Return the most recently merged PR into main, or None on error."""
    url = (
        f"https://api.github.com/repos/{repo}/pulls"
        "?state=closed&base=main&sort=updated&direction=desc&per_page=20"
    )
    try:
        pulls = gh_api_get(url, token)
    except Exception as exc:  # noqa: BLE001
        print(f"[guard] GitHub API error fetching PRs: {exc}", file=sys.stderr)
        return None

    if not isinstance(pulls, list):
        print("[guard] Unexpected GitHub API response shape.", file=sys.stderr)
        return None

    for pr in pulls:
        if pr.get("merged_at") and pr.get("base", {}).get("ref") == "main":
            return pr

    return None


def main() -> int:
    github_output = os.environ.get("GITHUB_OUTPUT", "")

    token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")

    if not token or not repo:
        print(
            "[guard] GITHUB_TOKEN or GITHUB_REPOSITORY not set; defaulting should_run=false.",
            file=sys.stderr,
        )
        write_output(github_output, "should_run", "false")
        write_output(github_output, "latest_pr_number", "")
        write_output(github_output, "latest_pr_merged_at", "")
        return 0

    state = load_state()
    # Accept both the legacy key and the new canonical key
    last_processed_pr = int(
        state.get("last_processed_pr_number")
        or state.get("last_processed_merged_pr_number")
        or 0
    )
    print(f"[guard] Last processed PR number from state: {last_processed_pr or '(none)'}")

    latest_pr = fetch_latest_merged_pr(token, repo)
    if latest_pr is None:
        # API failure — be conservative: skip to avoid spurious runs
        print(
            "[guard] Could not determine latest merged PR; defaulting should_run=false.",
            file=sys.stderr,
        )
        write_output(github_output, "should_run", "false")
        write_output(github_output, "latest_pr_number", "")
        write_output(github_output, "latest_pr_merged_at", "")
        return 0

    latest_pr_number = int(latest_pr.get("number") or 0)
    latest_pr_merged_at = str(latest_pr.get("merged_at") or "")

    print(f"[guard] Latest merged PR: #{latest_pr_number} merged_at={latest_pr_merged_at}")

    if latest_pr_number <= last_processed_pr:
        print(
            f"[guard] No new merged PRs (latest=#{latest_pr_number}, "
            f"last_processed=#{last_processed_pr}). Skipping AI sync."
        )
        write_output(github_output, "should_run", "false")
    else:
        print(
            f"[guard] New merged PR detected: #{latest_pr_number} > "
            f"last_processed #{last_processed_pr}. AI sync will run."
        )
        write_output(github_output, "should_run", "true")

    write_output(github_output, "latest_pr_number", str(latest_pr_number))
    write_output(github_output, "latest_pr_merged_at", latest_pr_merged_at)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
