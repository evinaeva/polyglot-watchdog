#!/usr/bin/env python3
"""Append deterministic merged PR entries to docs/auto/merged_pr_feed.md.

Designed for pull_request.closed events where merged=true and base=main.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from pathlib import Path
from typing import List


def gh_api_get(url: str, token: str) -> dict | list:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "docs-pr-feed",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_changed_files(event: dict) -> List[str]:
    files = event.get("pull_request", {}).get("files")
    if isinstance(files, list):
        return sorted({f.get("filename", "") for f in files if f.get("filename")})

    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    pr_number = event.get("pull_request", {}).get("number")
    if not token or not repo or not pr_number:
        return []

    out: list[str] = []
    page = 1
    while True:
        api_url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/files?per_page=100&page={page}"
        payload = gh_api_get(api_url, token)
        if not payload:
            break
        for entry in payload:
            name = entry.get("filename")
            if name:
                out.append(name)
        if len(payload) < 100:
            break
        page += 1
    return sorted(set(out))


def build_entry(event: dict, files: List[str]) -> str:
    pr = event["pull_request"]
    pr_body = (pr.get("body") or "").rstrip()
    lines = [
        f"## PR #{pr['number']} — {pr.get('merged_at', '')}",
        "",
        f"- Title: {pr.get('title', '').strip()}",
        f"- PR URL: {pr.get('html_url', '')}",
        f"- Author: {pr.get('user', {}).get('login', '')}",
        f"- Base branch: {pr.get('base', {}).get('ref', '')}",
        f"- Head branch: {pr.get('head', {}).get('ref', '')}",
        f"- Merge commit: {pr.get('merge_commit_sha', '')}",
        "- Changed files:",
    ]
    if files:
        lines.extend([f"  - {path}" for path in files])
    else:
        lines.append("  - (none reported)")
    lines.append("- Description:")
    if pr_body:
        lines.extend([f"  {line}" for line in pr_body.splitlines()])
    else:
        lines.append("  ")
    lines.append("- Notes: Auto-generated from merged PR metadata.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        print("GITHUB_EVENT_PATH is required", file=sys.stderr)
        return 1

    event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    pr = event.get("pull_request", {})
    if not pr.get("merged") or pr.get("base", {}).get("ref") != "main":
        print("Not a merged PR into main; nothing to do.")
        return 0

    pr_number = pr.get("number")
    merge_sha = pr.get("merge_commit_sha", "")

    feed_path = Path("docs/auto/merged_pr_feed.md")
    feed_path.parent.mkdir(parents=True, exist_ok=True)
    if not feed_path.exists():
        feed_path.write_text("# Merged PR Feed\n\n", encoding="utf-8")

    existing = feed_path.read_text(encoding="utf-8")
    duplicate_pattern = re.compile(
        rf"^## PR #{re.escape(str(pr_number))} — .*?^- Merge commit: {re.escape(merge_sha)}$",
        flags=re.MULTILINE | re.DOTALL,
    )
    if duplicate_pattern.search(existing):
        print("Duplicate detected; feed entry already exists.")
        return 0

    files = get_changed_files(event)
    entry = build_entry(event, files)
    updated = existing.rstrip() + "\n\n" + entry
    feed_path.write_text(updated, encoding="utf-8")
    print(f"Appended feed entry for PR #{pr_number}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
