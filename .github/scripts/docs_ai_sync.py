#!/usr/bin/env python3
"""Run incremental AI docs sync based on merged PR feed in DOCS_AUTOUPDATE.

This script reads feed/state from a source ref (typically origin/DOCS_AUTOUPDATE),
applies validated documentation updates in the current checkout (expected main), and
emits outputs for workflow control.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ALLOWED_PREFIXES = ("docs/", "spec/", "contract/schemas/")
ALLOWED_ROOT_FILES = {"RELEASE_CRITERIA.md", "README.md", "APPLYING_STREAM1.md"}
BLACKLIST = {
    "contract/watchdog_contract_v1.0.md",
    "Dockerfile",
    "Dockerfile.e2e",
    "cloudbuild.yaml",
    "requirements.txt",
}
DEFAULT_MODEL = "claude-3-5-sonnet-20241022"
MAX_DOC_FILES = 80
MAX_DOC_CHARS = 300_000
MAX_FILE_CHARS = 20_000


def git_show(ref_path: str) -> str:
    res = subprocess.run(["git", "show", ref_path], capture_output=True, text=True)
    if res.returncode != 0:
        return ""
    return res.stdout


def parse_feed(feed_text: str) -> list[dict[str, Any]]:
    chunks = re.split(r"(?m)^## PR #", feed_text)
    entries: list[dict[str, Any]] = []
    for chunk in chunks[1:]:
        head, *rest = chunk.splitlines()
        m = re.match(r"(\d+)\s+—\s+(.+)", head.strip())
        if not m:
            continue
        pr_number = int(m.group(1))
        merged_at = m.group(2).strip()
        body = "\n".join(rest)
        merge_match = re.search(r"(?m)^- Merge commit:\s*(\S+)\s*$", body)
        merge_commit = merge_match.group(1) if merge_match else ""

        changed_files: list[str] = []
        in_changed_section = False
        for line in rest:
            if line.startswith("- Changed files:"):
                in_changed_section = True
                continue
            if in_changed_section:
                if line.startswith("- ") and not line.startswith("  - "):
                    break
                if line.startswith("  - "):
                    path = line[4:].strip()
                    if path and path != "(none reported)":
                        changed_files.append(path)

        entries.append(
            {
                "pr_number": pr_number,
                "merged_at": merged_at,
                "merge_commit": merge_commit,
                "changed_files": changed_files,
                "raw": f"## PR #{chunk}",
            }
        )
    return entries


def is_allowed(path: str) -> bool:
    if path in BLACKLIST:
        return False
    if path in ALLOWED_ROOT_FILES:
        return True
    return path.startswith(ALLOWED_PREFIXES)


def _all_allowlisted_files() -> list[str]:
    files: list[Path] = []
    for prefix in ["docs", "spec", "contract/schemas"]:
        root = Path(prefix)
        if root.exists():
            files.extend([p for p in root.rglob("*") if p.is_file()])

    for root_file in ALLOWED_ROOT_FILES:
        p = Path(root_file)
        if p.exists():
            files.append(p)

    return sorted({f.as_posix() for f in files})


def gather_allowlisted_files(candidate_paths: list[str]) -> tuple[dict[str, str], dict[str, Any]]:
    all_paths = _all_allowlisted_files()
    if not all_paths:
        return {}, {"selected_files": 0, "total_chars": 0, "truncated_files": []}

    prioritized: list[str] = []
    for path in candidate_paths:
        if path in all_paths and path not in prioritized:
            prioritized.append(path)

    for root_file in sorted(ALLOWED_ROOT_FILES):
        if root_file in all_paths and root_file not in prioritized:
            prioritized.append(root_file)

    for path in all_paths:
        if path not in prioritized:
            prioritized.append(path)

    selected: dict[str, str] = {}
    total_chars = 0
    truncated_files: list[str] = []

    for path in prioritized:
        if len(selected) >= MAX_DOC_FILES:
            break
        content = Path(path).read_text(encoding="utf-8")
        if len(content) > MAX_FILE_CHARS:
            content = content[:MAX_FILE_CHARS] + "\n\n[TRUNCATED_FOR_PROMPT]\n"
            truncated_files.append(path)
        if total_chars + len(content) > MAX_DOC_CHARS:
            break
        selected[path] = content
        total_chars += len(content)

    return selected, {
        "selected_files": len(selected),
        "total_chars": total_chars,
        "truncated_files": truncated_files,
        "max_files": MAX_DOC_FILES,
        "max_chars": MAX_DOC_CHARS,
        "max_file_chars": MAX_FILE_CHARS,
    }


def extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def call_claude(prompt: str, model: str, api_key: str) -> str:
    payload = {
        "model": model,
        "max_tokens": 4000,
        "temperature": 0,
        "messages": [{"role": "user", "content": prompt}],
    }
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    parts = body.get("content", [])
    text_parts = [p.get("text", "") for p in parts if p.get("type") == "text"]
    return "\n".join(text_parts).strip()


def resolve_model(raw_model: str | None) -> str:
    if raw_model is None:
        return DEFAULT_MODEL

    model = raw_model.strip()
    if not model:
        return DEFAULT_MODEL

    if "=" in model:
        raise ValueError(
            "Invalid ANTHROPIC_MODEL: expected a model id (for example 'claude-3-5-sonnet-20241022'), "
            "but got an assignment-like value containing '='."
        )

    if any(ch.isspace() for ch in model):
        raise ValueError("Invalid ANTHROPIC_MODEL: model id must not contain whitespace.")

    return model


def write_output(path: str | None, key: str, value: str) -> None:
    if not path:
        return
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"{key}={value}\n")


def compute_new_entries(entries: list[dict[str, Any]], state: dict[str, Any]) -> list[dict[str, Any]]:
    last_commit = (state.get("last_processed_merge_commit") or "").strip()
    last_pr = int(state.get("last_processed_pr_number") or 0)

    if not last_commit and last_pr <= 0:
        return entries

    if last_commit:
        for idx, entry in enumerate(entries):
            if entry.get("merge_commit") == last_commit:
                return entries[idx + 1 :]

        print(
            "State marker merge commit was not found in feed; attempting PR-number recovery.",
            file=sys.stderr,
        )

    if last_pr > 0:
        recovered = [entry for entry in entries if int(entry.get("pr_number", 0)) > last_pr]
        print(f"Recovered incrementality using last_processed_pr_number={last_pr}.", file=sys.stderr)
        return recovered

    raise RuntimeError(
        "State marker not found in feed and no PR-number recovery marker exists; refusing unsafe full replay."
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--feed-ref", default="origin/DOCS_AUTOUPDATE")
    parser.add_argument("--state-ref", default="origin/DOCS_AUTOUPDATE")
    parser.add_argument("--state-output", default=".github/tmp/docs_sync_state.json")
    parser.add_argument("--prompt-template", default=".github/prompts/docs_sync_prompt.txt")
    parser.add_argument("--github-output", default=os.environ.get("GITHUB_OUTPUT", ""))
    args = parser.parse_args()

    write_output(args.github_output, "docs_changed", "false")
    write_output(args.github_output, "state_changed", "false")

    feed_text = git_show(f"{args.feed_ref}:docs/auto/merged_pr_feed.md")
    if not feed_text:
        print("No feed content found; exiting no-op.")
        return 0

    state_text = git_show(f"{args.state_ref}:docs/auto/docs_sync_state.json")
    state = {"last_processed_merge_commit": "", "last_processed_pr_number": 0, "last_sync_at_utc": ""}
    if state_text.strip():
        try:
            state.update(json.loads(state_text))
        except json.JSONDecodeError:
            print("State file is invalid JSON.", file=sys.stderr)
            return 1

    entries = parse_feed(feed_text)
    if not entries:
        print("No feed entries found.")
        return 0

    try:
        new_entries = compute_new_entries(entries, state)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if not new_entries:
        print("No new feed entries to process.")
        return 0

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ANTHROPIC_API_KEY is required.", file=sys.stderr)
        return 1

    try:
        model = resolve_model(os.environ.get("ANTHROPIC_MODEL"))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    changed_candidates = [p for entry in new_entries for p in entry.get("changed_files", []) if is_allowed(p)]
    docs_snapshot, snapshot_meta = gather_allowlisted_files(changed_candidates)
    prompt_template = Path(args.prompt_template).read_text(encoding="utf-8")
    payload = {
        "feed_delta": [
            {
                "pr_number": e["pr_number"],
                "merged_at": e["merged_at"],
                "merge_commit": e["merge_commit"],
                "changed_files": e["changed_files"],
                "entry": e["raw"],
            }
            for e in new_entries
        ],
        "docs_snapshot": docs_snapshot,
        "docs_snapshot_meta": snapshot_meta,
    }
    prompt = f"{prompt_template}\n\nINPUT_JSON:\n{json.dumps(payload, ensure_ascii=False)}"

    response_text = call_claude(prompt, model, api_key)
    try:
        response_json = extract_json(response_text)
    except Exception as exc:
        print(f"Failed to parse Claude JSON response: {exc}", file=sys.stderr)
        return 1

    updates = response_json.get("updates")
    if not isinstance(updates, list):
        print("Claude response missing 'updates' list.", file=sys.stderr)
        return 1

    docs_changed = False
    for update in updates:
        if not isinstance(update, dict):
            print("Invalid update entry type.", file=sys.stderr)
            return 1
        path = str(update.get("path", "")).strip()
        action = update.get("action")
        content = update.get("content")
        if action != "replace_file":
            print(f"Unsupported action: {action}", file=sys.stderr)
            return 1
        if not path or not is_allowed(path):
            print(f"Disallowed target path: {path}", file=sys.stderr)
            return 1
        if not isinstance(content, str) or not content.strip():
            print(f"Invalid content for {path}", file=sys.stderr)
            return 1

        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        existing = target.read_text(encoding="utf-8") if target.exists() else ""
        if existing != content:
            target.write_text(content, encoding="utf-8")
            docs_changed = True

    newest = new_entries[-1]
    new_state = {
        "last_processed_merge_commit": newest.get("merge_commit", ""),
        "last_processed_pr_number": newest.get("pr_number", 0),
        "last_sync_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    out_path = Path(args.state_output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(new_state, indent=2) + "\n", encoding="utf-8")

    write_output(args.github_output, "docs_changed", "true" if docs_changed else "false")
    write_output(args.github_output, "state_changed", "true")
    write_output(args.github_output, "state_output_path", out_path.as_posix())

    print("No documentation changes proposed by AI." if not docs_changed else "Documentation updates applied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
