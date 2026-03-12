import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path


def run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)


def init_git_repo(tmp_path: Path) -> None:
    run(["git", "init"], tmp_path)
    run(["git", "config", "user.name", "test"], tmp_path)
    run(["git", "config", "user.email", "test@example.com"], tmp_path)
    (tmp_path / "README.md").write_text("hello\n", encoding="utf-8")
    run(["git", "add", "README.md"], tmp_path)
    run(["git", "commit", "-m", "init"], tmp_path)


def load_docs_ai_module():
    script_path = Path(__file__).resolve().parents[1] / ".github" / "scripts" / "docs_ai_sync.py"
    spec = importlib.util.spec_from_file_location("docs_ai_sync_test", script_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_validate_docs_diff_allows_allowlist(tmp_path):
    init_git_repo(tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "x.md").write_text("x\n", encoding="utf-8")
    script = Path(__file__).resolve().parents[1] / ".github" / "scripts" / "validate_docs_diff.py"
    res = run([sys.executable, str(script), "--ref", "HEAD"], tmp_path)
    assert res.returncode == 0, res.stderr


def test_validate_docs_diff_rejects_blacklist(tmp_path):
    init_git_repo(tmp_path)
    (tmp_path / "Dockerfile").write_text("FROM alpine\n", encoding="utf-8")
    script = Path(__file__).resolve().parents[1] / ".github" / "scripts" / "validate_docs_diff.py"
    res = run([sys.executable, str(script), "--ref", "HEAD"], tmp_path)
    assert res.returncode == 1
    assert "Blacklisted files" in res.stderr


def test_merged_feed_duplicate_guard(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    feed_dir = tmp_path / "docs" / "auto"
    feed_dir.mkdir(parents=True)
    (feed_dir / "merged_pr_feed.md").write_text("# Merged PR Feed\n", encoding="utf-8")

    event = {
        "pull_request": {
            "merged": True,
            "base": {"ref": "main"},
            "number": 42,
            "merged_at": "2026-01-01T00:00:00Z",
            "title": "Update docs",
            "html_url": "https://example/pr/42",
            "user": {"login": "octocat"},
            "head": {"ref": "feature"},
            "merge_commit_sha": "abc123",
        }
    }
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(event), encoding="utf-8")

    script = repo / ".github" / "scripts" / "update_merged_pr_feed.py"
    env = os.environ.copy()
    env["GITHUB_EVENT_PATH"] = str(event_path)

    first = subprocess.run([sys.executable, str(script)], cwd=tmp_path, env=env, text=True, capture_output=True)
    assert first.returncode == 0, first.stderr
    second = subprocess.run([sys.executable, str(script)], cwd=tmp_path, env=env, text=True, capture_output=True)
    assert second.returncode == 0, second.stderr

    content = (feed_dir / "merged_pr_feed.md").read_text(encoding="utf-8")
    assert content.count("## PR #42") == 1


def test_docs_ai_noop_and_state_advancement_and_blank_model_fallback(monkeypatch, tmp_path):
    mod = load_docs_ai_module()
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.md").write_text("A\n", encoding="utf-8")

    feed_text = "# Merged PR Feed\n\n## PR #1 — 2026-01-01T00:00:00Z\n- Merge commit: sha1\n- Changed files:\n  - docs/a.md\n"

    def fake_show(ref_path: str) -> str:
        if ref_path.endswith("merged_pr_feed.md"):
            return feed_text
        if ref_path.endswith("docs_sync_state.json"):
            return '{"last_processed_merge_commit":"","last_processed_pr_number":0,"last_sync_at_utc":""}'
        return ""

    captured = {}

    def fake_call(_prompt, model, _api_key):
        captured["model"] = model
        return '{"updates": []}'

    monkeypatch.setattr(mod, "git_show", fake_show)
    monkeypatch.setattr(mod, "call_claude", fake_call)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    monkeypatch.setenv("ANTHROPIC_MODEL", "")

    prompt = tmp_path / "prompt.txt"
    prompt.write_text("template", encoding="utf-8")
    out_state = tmp_path / "state.json"
    out_env = tmp_path / "out.env"

    old_argv = sys.argv
    sys.argv = [
        "docs_ai_sync.py",
        "--prompt-template",
        str(prompt),
        "--state-output",
        str(out_state),
        "--github-output",
        str(out_env),
    ]
    try:
        rc = mod.main()
    finally:
        sys.argv = old_argv

    assert rc == 0
    assert captured["model"] == mod.DEFAULT_MODEL
    out = out_env.read_text(encoding="utf-8")
    assert "docs_changed=false" in out
    assert "state_changed=true" in out
    state = json.loads(out_state.read_text(encoding="utf-8"))
    assert state["last_processed_merge_commit"] == "sha1"


def test_docs_ai_state_marker_missing_recovers_by_pr_number(monkeypatch, tmp_path):
    mod = load_docs_ai_module()
    recovered = mod.compute_new_entries(
        entries=[
            {"pr_number": 7, "merge_commit": "sha7"},
            {"pr_number": 8, "merge_commit": "sha8"},
        ],
        state={"last_processed_merge_commit": "missing", "last_processed_pr_number": 7},
    )
    assert len(recovered) == 1
    assert recovered[0]["pr_number"] == 8


def test_docs_ai_state_marker_missing_without_pr_fails():
    mod = load_docs_ai_module()
    try:
        mod.compute_new_entries(
            entries=[{"pr_number": 7, "merge_commit": "sha7"}],
            state={"last_processed_merge_commit": "missing", "last_processed_pr_number": 0},
        )
    except RuntimeError:
        assert True
        return
    assert False, "Expected unsafe replay guard runtime error"


def test_docs_ai_rejects_invalid_claude_output(monkeypatch, tmp_path):
    mod = load_docs_ai_module()
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.md").write_text("A\n", encoding="utf-8")

    monkeypatch.setattr(
        mod,
        "git_show",
        lambda ref_path: "# Merged PR Feed\n\n## PR #1 — 2026-01-01T00:00:00Z\n- Merge commit: sha1\n"
        if ref_path.endswith("merged_pr_feed.md")
        else '{"last_processed_merge_commit":"","last_processed_pr_number":0,"last_sync_at_utc":""}',
    )
    monkeypatch.setattr(mod, "call_claude", lambda *args, **kwargs: '{"foo": 1}')
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")

    prompt = tmp_path / "prompt.txt"
    prompt.write_text("template", encoding="utf-8")
    out_state = tmp_path / "state.json"

    old_argv = sys.argv
    sys.argv = ["docs_ai_sync.py", "--prompt-template", str(prompt), "--state-output", str(out_state)]
    try:
        rc = mod.main()
    finally:
        sys.argv = old_argv

    assert rc == 1


def test_docs_ai_rejects_malformed_anthropic_model_before_api_call(monkeypatch, tmp_path):
    mod = load_docs_ai_module()
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.md").write_text("A\n", encoding="utf-8")

    monkeypatch.setattr(
        mod,
        "git_show",
        lambda ref_path: "# Merged PR Feed\n\n## PR #1 — 2026-01-01T00:00:00Z\n- Merge commit: sha1\n"
        if ref_path.endswith("merged_pr_feed.md")
        else '{"last_processed_merge_commit":"","last_processed_pr_number":0,"last_sync_at_utc":""}',
    )

    called = {"value": False}

    def fail_if_called(*_args, **_kwargs):
        called["value"] = True
        raise AssertionError("call_claude should not be called for malformed ANTHROPIC_MODEL")

    monkeypatch.setattr(mod, "call_claude", fail_if_called)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    monkeypatch.setenv("ANTHROPIC_MODEL", "ANTHROPIC_MODEL = claude-3-haiku-20240307")

    prompt = tmp_path / "prompt.txt"
    prompt.write_text("template", encoding="utf-8")
    out_state = tmp_path / "state.json"

    old_argv = sys.argv
    sys.argv = ["docs_ai_sync.py", "--prompt-template", str(prompt), "--state-output", str(out_state)]
    try:
        rc = mod.main()
    finally:
        sys.argv = old_argv

    assert rc == 1
    assert called["value"] is False
    assert not out_state.exists()
