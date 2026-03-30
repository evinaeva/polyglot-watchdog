import sys
import types

from app import artifact_helpers


def test_artifact_exists_logs_and_returns_false_on_storage_error(capsys):
    original_storage = sys.modules.get("pipeline.storage")
    fake_storage = types.ModuleType("pipeline.storage")
    fake_storage.artifact_path = lambda domain, run_id, filename: f"{domain}/{run_id}/{filename}"

    def _boom(*args, **kwargs):
        raise RuntimeError("transient gcs outage")

    fake_storage.list_run_artifacts = _boom
    sys.modules["pipeline.storage"] = fake_storage
    try:
        exists = artifact_helpers._artifact_exists("example.com", "run-1", "issues.json")
    finally:
        if original_storage is None:
            sys.modules.pop("pipeline.storage", None)
        else:
            sys.modules["pipeline.storage"] = original_storage

    assert exists is False
    captured = capsys.readouterr()
    assert (
        "[storage] exists_check fallback domain=example.com run_id=run-1 file=issues.json: transient gcs outage"
        in captured.err
    )
