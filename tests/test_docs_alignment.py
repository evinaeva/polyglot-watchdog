from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
ABOUT = ROOT / "docs/ABOUT_PAGE_COPY.md"
TRUTHSET = ROOT / "docs/PRODUCT_TRUTHSET.md"
AUDIT = ROOT / "docs/RELEASE_READINESS.md"
EVIDENCE = ROOT / "docs/RELEASE_EVIDENCE.md"
MESSAGING = ROOT / "docs/MESSAGING_STATE.md"
RUNBOOK = ROOT / "docs/LOCAL_DEMO_RUNBOOK.md"
DOCKERFILE_E2E = ROOT / "Dockerfile.e2e"
E2E_SCRIPT = ROOT / "scripts/run_e2e_happy_path.sh"

PRE_PROD_PHRASE = "late prototype / pre-production / operator-console-in-progress"
PROD_PHRASE = "production-ready for the documented v1.0 scope"


TRUTH_SURFACES = [README, ABOUT, TRUTHSET]


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_truth_surfaces_share_pre_production_stage_phrase() -> None:
    for path in TRUTH_SURFACES:
        assert PRE_PROD_PHRASE in _text(path), f"missing pre-production phrase in {path}"


def test_production_wording_requires_gate_pass() -> None:
    audit_text = _text(AUDIT)
    gate_is_passed = "Messaging state: **production_ready_v1_scope**" in audit_text

    found_prod_wording = [path for path in TRUTH_SURFACES if PROD_PHRASE in _text(path)]
    if found_prod_wording:
        assert gate_is_passed, "production wording present but gate decision is not passed"


def test_deferred_scope_is_explicit_on_truth_surfaces() -> None:
    for path in TRUTH_SURFACES:
        text = _text(path)
        assert "OCR / Phase 4" in text, f"missing OCR deferred-scope statement in {path}"
        assert "manual seed URL workflow" in text, (
            f"missing manual-seed deferred-scope statement in {path}"
        )


def test_forbidden_phrases_not_present() -> None:
    forbidden_phrases = [
        "mostly production-ready",
        "basically production-ready",
        "production-ready except",
        "all mock",
        "no phases implemented",
    ]
    for path in TRUTH_SURFACES:
        lower = _text(path).lower()
        for phrase in forbidden_phrases:
            assert phrase not in lower, f"forbidden phrase '{phrase}' found in {path}"


def test_evidence_and_messaging_docs_exist_with_required_sections() -> None:
    assert EVIDENCE.exists(), "docs/RELEASE_EVIDENCE.md must exist"
    assert MESSAGING.exists(), "docs/MESSAGING_STATE.md must exist"

    evidence_text = _text(EVIDENCE)
    required_evidence_markers = [
        "/urls persistence evidence",
        "Reproducible capture flow evidence",
        "Review/annotation persistence evidence",
        "Deterministic eligible dataset generation evidence",
        "Issue artifact generation + explorer visibility evidence",
        "Documentation synchronization evidence",
    ]
    for marker in required_evidence_markers:
        assert marker in evidence_text, f"missing evidence section: {marker}"


def test_workstream_a_happy_path_runnable_command_exists() -> None:
    """Gate: Workstream A PASS requires a deterministic, clean-env runnable command.

    This test fails if:
    - Dockerfile.e2e does not exist
    - scripts/run_e2e_happy_path.sh does not exist
    - docs/LOCAL_DEMO_RUNBOOK.md does not document the docker command

    Passing this test confirms the clean-env happy-path claim is auditable.
    """
    assert DOCKERFILE_E2E.exists(), (
        "Dockerfile.e2e must exist to provide a deterministic Playwright-ready test environment. "
        "Workstream A cannot be marked PASS without it."
    )
    assert E2E_SCRIPT.exists(), (
        "scripts/run_e2e_happy_path.sh must exist to provide the single runnable command. "
        "Workstream A cannot be marked PASS without it."
    )

    runbook_text = _text(RUNBOOK)
    assert "run_e2e_happy_path.sh" in runbook_text, (
        "docs/LOCAL_DEMO_RUNBOOK.md must document the Docker-based happy-path command. "
        "Workstream A cannot be marked PASS without it."
    )
    assert "Dockerfile.e2e" in runbook_text, (
        "docs/LOCAL_DEMO_RUNBOOK.md must reference Dockerfile.e2e. "
        "Workstream A cannot be marked PASS without it."
    )
